import pytesseract
from PIL import Image
import glob
import os
import time
import re
import sys
import threading
import itertools
import language_tool_python
import argparse
from multiprocessing import Pool, cpu_count
from functools import partial
from pathlib import Path

class Spinner:
    def __init__(self):
        self.spinner_chars = ["⠋", "⠙", "⠚", "⠞", "⠖", "⠦", "⠧", "⠇", "⠏", "⠍"]
        self.spinner = itertools.cycle(self.spinner_chars)
        self.busy = False
        self.delay = 0.1
        self.spinner_visible = False
        self.thread = None

    def write_next(self):
        with self._screen_lock:
            if not self.spinner_visible:
                sys.stdout.write(next(self.spinner))
                self.spinner_visible = True
                sys.stdout.flush()

    def remove_spinner(self, cleanup=False):
        with self._screen_lock:
            if self.spinner_visible:
                sys.stdout.write('\b')
                self.spinner_visible = False
                if cleanup:
                    sys.stdout.write(' ')
                    sys.stdout.write('\b')
                sys.stdout.flush()

    def spinner_task(self):
        while self.busy:
            self.write_next()
            time.sleep(self.delay)
            self.remove_spinner()

    def __enter__(self):
        if sys.stdout.isatty():
            self._screen_lock = threading.Lock()
            self.busy = True
            self.thread = threading.Thread(target=self.spinner_task)
            self.thread.daemon = True
            self.thread.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if sys.stdout.isatty():
            self.busy = False
            time.sleep(self.delay)
            self.remove_spinner(cleanup=True)
            if self.thread:
                self.thread.join()

# Initialize the language tool as global instance
tool = None
FAST_MODE = True  # Set to False for more accurate but slower processing

def init_language_tool():
    global tool
    if not FAST_MODE and tool is None:
        tool = language_tool_python.LanguageTool('en-US')

def clean_text(text, use_language_tool=False):
    # Compile regex patterns for better performance
    CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]')
    STUCK_WORDS = re.compile(r'(?<=[a-z])(?=[A-Z])')
    
    # Fast initial cleanup
    text = CONTROL_CHARS.sub('', text)
    text = STUCK_WORDS.sub(' ', text)
    text = text.replace('|', 'I')
    
    # Split and clean lines
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            cleaned_lines.append(line)
            continue
        
        # Apply language tool only if requested and not in fast mode
        if use_language_tool and not FAST_MODE and tool is not None:
            try:
                matches = tool.check(line)
                if matches:
                    for match in matches:
                        if match.replacements:
                            line = line[:match.offset] + match.replacements[0] + line[match.offset + match.errorLength:]
            except:
                pass  # Skip language checking if any error occurs
        
        cleaned_lines.append(line)
    
    # Join lines back together
    return '\n'.join(cleaned_lines)

def process_file(png_file, output_dir=None, use_language_tool=False):
    start_time = time.time()
    
    print(f"\nProcessing {png_file}... ", end='', flush=True)
    with Spinner():
        # Load image and extract text
        image = Image.open(png_file)
        text = pytesseract.image_to_string(
            image,
            config=r'--oem 3 --psm 3'
        )
    
    # Clean text
    text = clean_text(text, use_language_tool)
    
    # Create output path
    if output_dir:
        output_file = Path(output_dir) / (Path(png_file).stem + '.txt')
    else:
        output_file = os.path.splitext(png_file)[0] + '.txt'
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save text
    with open(output_file, 'w') as f:
        f.write(text)
    
    process_time = time.time() - start_time
    return str(png_file), str(output_file), process_time

def main():
    parser = argparse.ArgumentParser(description='OCR tool to extract text from images')
    parser.add_argument('input', help='Input image file or directory containing PNG files')
    parser.add_argument('-o', '--output', help='Output directory for text files (default: same as input)')
    parser.add_argument('--accurate', action='store_true', help='Use more accurate but slower processing')
    args = parser.parse_args()

    # Set processing mode
    global FAST_MODE
    FAST_MODE = not args.accurate

    # Initialize language tool if needed
    if not FAST_MODE:
        init_language_tool()
    
    # Handle input path
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input path '{input_path}' does not exist")
        return

    # Set output directory
    output_dir = Path(args.output) if args.output else input_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of PNG files
    if input_path.is_file():
        if input_path.suffix.lower() != '.png':
            print("Error: Input file must be a PNG image")
            return
        png_files = [input_path]
    else:
        png_files = list(input_path.glob('*.png'))

    if not png_files:
        print("No PNG files found in the specified path.")
        return

    total_start_time = time.time()
    
    # Process files in parallel
    with Pool(processes=min(cpu_count(), len(png_files))) as pool:
        process_func = partial(process_file, output_dir=output_dir, use_language_tool=not FAST_MODE)
        results = pool.map(process_func, [str(f) for f in png_files])
    
    # Print results
    for png_file, output_file, process_time in results:
        print(f"\rProcessed {png_file} -> {output_file} (took {process_time:.2f} seconds)")
    
    total_time = time.time() - total_start_time
    print(f"\nTotal processing time: {total_time:.2f} seconds for {len(png_files)} file(s)")

if __name__ == '__main__':
    main()
