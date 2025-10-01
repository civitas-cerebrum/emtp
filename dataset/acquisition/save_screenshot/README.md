# Screenshot Capture Module

Captures full-page screenshots of URLs from JSON files using Selenium WebDriver.

## Features

- **Full-Page Screenshots**: Captures complete webpage content
- **Headless Chrome**: Fast, automated screenshot capture
- **PNG Format**: High-quality image output
- **Recursive Processing**: Finds JSON files in subdirectories
- **URL Extraction**: Automatically extracts URLs from JSON structures
- **Error Handling**: Robust processing with detailed logging

## Usage

```bash
python main.py <input_dir> <output_dir> [options]
```

### Arguments

- `input_dir`: Directory containing JSON files with URLs
- `output_dir`: Directory where screenshots will be saved

### Options

- `--timeout SECONDS`: Page load timeout (default: 30)
- `--verbose, -v`: Enable verbose logging
- `--headless`: Run browser in headless mode (default: True)
- `--no-headless`: Run browser in non-headless mode

## Input Format

JSON files containing URLs in any structure:

```json
{
  "urls": ["https://example.com"],
  "metadata": {"source": "https://another.com"}
}
```

## Output

Screenshots saved as PNG files in a mirrored directory structure.

## Dependencies

- selenium
- Pillow
- webdriver-manager

## Requirements

- Python 3.7+
- Google Chrome browser