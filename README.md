# EMTP - Expert Model Training Pipeline

EMTP is a comprehensive pipeline for acquiring, processing, and preparing data for training expert AI models. The pipeline focuses on quality assurance (QA) related content, systematically collecting questions, retrieving relevant URLs using DuckDuckGo search, and capturing webpage screenshots.

## Key Features

- **Interactive Pipeline**: Choose individual stages or run the full pipeline with custom paths
- **DuckDuckGo Search**: Uses DuckDuckGo for URL retrieval (privacy-focused, no Google)
- **Unicode Handling**: Automatically processes and normalizes Unicode characters in questions
- **Temp Directory Management**: Uses organized temp directories for intermediate data storage
- **Modular Architecture**: Clean separation of acquisition, enrichment, and training stages

## Project Structure

```
emtp/
├── main.py                 # Main interactive pipeline orchestrator
├── requirements.txt        # Lists all Python package dependencies for the project
├── qa_questions.json       # Centralized JSON file containing questions for data acquisition
├── .gitignore              # Specifies intentionally untracked files and directories to ignore by Git
├── dataset/                # Top-level directory for all data, organized into acquisition, enrichment, and questions
│   ├── README.md           # Provides an overview of the dataset directory's purpose and contents
│   ├── acquisition/        # Contains all modules and scripts responsible for data acquisition stages
│   │   ├── __init__.py     # Marks `acquisition` as a Python package and handles module connections
│   │   ├── README.md       # Detailed documentation for the data acquisition process
│   │   ├── temp/           # Temporary storage for intermediate data generated during acquisition
│   │   │   ├── urls/       # Stores JSON files containing URLs retrieved from search engines
│   │   │   ├── screenshots/ # Stores captured web page screenshots in PNG format
│   │   │   └── text_data/    # Stores extracted text data from screenshots
│   │   ├── retrieve_url/   # Python module dedicated to retrieving URLs based on QA questions
│   │   ├── save_screenshot/ # Python module dedicated to capturing screenshots from URLs
│   │   └── screenshot_processing/ # Python module for OCR and text cleaning from screenshots
│   │   └── screenshot_processing/ # Python module for OCR and text cleaning from screenshots
│   ├── enrichment/         # Placeholder for future data enrichment and processing modules
│   └── questions/          # Stores question datasets, including `qa_questions.json`
└── training/               # Placeholder for future model training components and scripts
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the interactive pipeline:**
   ```bash
   python main.py
   ```

   This launches an interactive menu where you can:
   - Choose individual stages with custom input/output paths
   - Run the full pipeline (asks only for questions file and final screenshot output)
   - Exit the session

## Non-Interactive Execution

You can also run the pipeline directly using command-line arguments, which is useful for automation or scripting. Use the `--stage` argument to specify which part of the pipeline to run.

```bash
python main.py --stage full_pipeline --questions-file dataset/acquisition/retrieve_url/sample.json --text-data-output-dir dataset/acquisition/temp/text_data --accurate --verbose
```

## Pipeline Stages

### 1. URL Retrieval (`dataset/acquisition/retrieve_url/`)
- Reads questions from `dataset/acquisition/retrieve_url/sample.json` (or specified via `--questions-file`)
- Searches DuckDuckGo for relevant URLs
- Saves categorized results to `dataset/acquisition/temp/urls/`

### 2. Screenshot Capture (`dataset/acquisition/save_screenshot/`)
- Reads URLs from `dataset/acquisition/temp/urls/`
- Captures full-page screenshots using Selenium
- Saves PNG images to `dataset/acquisition/temp/screenshots/`

### 3. Screenshot Processing (`dataset/acquisition/screenshot_processing/`)
- Reads PNG images from `dataset/acquisition/temp/screenshots/` (recursively through subdirectories)
- Performs OCR to extract text from images
- Cleans and processes the extracted text. Can use `--accurate` flag for more robust cleaning.
- Saves text data to `dataset/acquisition/temp/text_data/`

## Data Flow

```mermaid
graph TD
    A[qa_questions.json] --> B(URL Retrieval);
    B --> C{dataset/acquisition/temp/urls/};
    C --> D(Screenshot Capture);
    D --> F{dataset/acquisition/temp/screenshots/};
    F --> G(Screenshot Processing);
    G --> H{dataset/acquisition/temp/text_data/};
```

## Requirements

- Python 3.8+
- Chrome/Chromium browser (for Selenium WebDriver)
- Internet connection for web scraping and searches

## Individual Stage Execution

You can run individual stages through the interactive menu in `main.py`, or directly from their respective directories, or via the non-interactive `main.py` entry point:

```bash
# Non-interactive URL retrieval only
python main.py --stage url_retrieval --questions-file dataset/acquisition/retrieve_url/sample.json --urls-output-dir custom/output

# Non-interactive Screenshot capture only
python main.py --stage screenshot_capture --urls-output-dir custom/input --screenshots-output-dir custom/output

# Non-interactive Screenshot processing only (with accurate mode)
python main.py --stage screenshot_processing --screenshots-output-dir custom/input --text-data-output-dir custom/output --accurate
```

## Configuration

- Modify `dataset/acquisition/retrieve_url/sample.json` or create a new JSON file to change the source questions.
- Configure screenshot settings in `save_screenshot/main.py`

## Dependencies

- `ddgs`: DuckDuckGo search API
- `selenium`: Web browser automation
- `webdriver-manager`: Automatic ChromeDriver management
- `Pillow`: Image processing for screenshots

## Notes

- All paths are resolved relative to project root
- Unicode characters in questions are automatically normalized
- Temporary directories are created automatically
- Screenshots are saved as PNG files with timestamps