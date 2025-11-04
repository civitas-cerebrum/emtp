import time
from pathlib import Path
from .text_cleaner import clean_text


import logging

logger = logging.getLogger(__name__)

def process_file(file_path, output_dir=None, use_language_tool=False):
    start_time = time.time()

    file_path = Path(file_path)
    logger.info(f"Processing {file_path}...")

    try:
        if file_path.suffix.lower() == '.md':
            # Process markdown file
            text = extract_text_from_markdown(file_path)
            logger.debug(f"Extracted text from {file_path}")
        else:
            logger.error(f"Unsupported file type: {file_path.suffix}")
            return str(file_path), None, 0.0
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return str(file_path), None, 0.0

    # Clean text
    text = clean_text(text, use_language_tool)

    # Create output path
    if output_dir:
        output_file = Path(output_dir) / (file_path.stem + '.txt')
    else:
        output_file = file_path.with_suffix('.txt')

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Save text
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text)

    process_time = time.time() - start_time
    return str(file_path), str(output_file), process_time




def extract_text_from_markdown(md_path):
    """Extract text from a markdown file."""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return text
    except Exception as e:
        logger.error(f"Error reading markdown file {md_path}: {e}")
        raise