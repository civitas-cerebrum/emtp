import pytesseract
from PIL import Image
import os
import time
from pathlib import Path
from .spinner import Spinner
from .text_cleaner import clean_text


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