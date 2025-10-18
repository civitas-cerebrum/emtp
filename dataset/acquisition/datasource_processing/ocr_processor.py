import pytesseract
from PIL import Image
import os
import time
from pathlib import Path
from .text_cleaner import clean_text

try:
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: pypdf not installed. PDF processing will not be available.")


import logging

logger = logging.getLogger(__name__)

def process_file(file_path, output_dir=None, use_language_tool=False):
    start_time = time.time()

    file_path = Path(file_path)
    logger.info(f"Processing {file_path}...")

    try:
        logger.info("Starting OCR processing...")
        if file_path.suffix.lower() == '.pdf':
            # Process PDF file
            if not PDF_SUPPORT:
                logger.error(f"PDF processing not available. pypdf library not installed.")
                return str(file_path), None, 0.0

            text = extract_text_from_pdf(file_path)
        else:
            # Process image file (PNG, TIFF, etc.)
            text = extract_text_from_image(file_path)
        logger.info("OCR processing completed.")
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


def extract_text_from_image(image_path):
    """Extract text from an image file using OCR."""
    try:
        logger.debug(f"Opening image: {image_path}")
        image = Image.open(image_path)
        
        logger.debug(f"Image opened. Size: {image.size}, Mode: {image.mode}")
        logger.debug(f"Running Tesseract OCR...")
        
        text = pytesseract.image_to_string(
            image,
            config=r'--oem 3 --psm 3',
            timeout=30
        )
        
        logger.debug(f"OCR completed. Extracted {len(text)} characters")
        return text
    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract-OCR is not installed or not in your PATH. Please install it.")
        raise
    except RuntimeError as timeout_error:
        logger.error(f"Tesseract timeout processing {image_path}: {timeout_error}")
        return ""
    except pytesseract.TesseractError as e:
        if "Estimating resolution as" in str(e):
            logger.warning(f"Tesseract resolution estimation failed for {image_path}: {e}. Skipping text extraction for this file.")
            return ""
        else:
            logger.error(f"Tesseract error: {e}")
            raise


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
        raise