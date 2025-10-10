"""
Module for processing and saving images.
"""

import os
from io import BytesIO
from PIL import Image
from typing import Optional

# Set a higher limit for Pillow's decompression bomb protection
Image.MAX_IMAGE_PIXELS = None


def save_screenshot_as_png(
    screenshot_bytes: bytes,
    output_path: str,
    quality: int = 95
) -> None:
    """
    Save screenshot bytes as a PNG file.

    Args:
        screenshot_bytes (bytes): The screenshot data as bytes.
        output_path (str): The path where to save the PNG file.
        quality (int): The quality of the PNG image (0-100). Defaults to 95.

    Raises:
        OSError: If there's an error saving the file.
    """
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    try:
        # Open the screenshot image from bytes
        image = Image.open(BytesIO(screenshot_bytes))

        # Convert to RGB if necessary (PNG supports alpha, but sometimes conversion helps)
        if image.mode in ("RGBA", "LA", "P"):
            # Create a white background
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1])  # Use alpha as mask
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        # Save as PNG
        image.save(output_path, format="PNG", quality=quality)

    except Exception as e:
        raise OSError(f"Error saving PNG file '{output_path}': {e}")


def process_screenshot_for_png(
    screenshot_bytes: bytes,
    output_path: str,
    quality: Optional[int] = 95
) -> None:
    """
    Process screenshot bytes and save as PNG with optimal settings.

    Args:
        screenshot_bytes (bytes): The screenshot data as bytes.
        output_path (str): The path where to save the PNG file.
        quality (Optional[int]): Quality setting for PNG.
    """
    save_screenshot_as_png(screenshot_bytes, output_path, quality)


def validate_png_file(file_path: str) -> bool:
    """
    Validate that a file is a valid PNG file.

    Args:
        file_path (str): Path to the file to validate.

    Returns:
        bool: True if valid PNG, False otherwise.
    """
    if not os.path.exists(file_path):
        return False

    try:
        with Image.open(file_path) as img:
            return img.format == "PNG"
    except:
        return False