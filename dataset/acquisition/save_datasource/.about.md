# Web Content Scraper Module

Scrapes web content from URLs using a self-hosted Firecrawl API and saves it as markdown files.

## Features

- **Firecrawl Integration**: Leverages a self-hosted Firecrawl instance for efficient web content scraping.
- **Markdown Output**: Converts web pages into clean, readable markdown format.
- **Batch Processing**: Processes multiple URLs concurrently for improved performance.
- **Recursive Processing**: Finds JSON files containing URLs in subdirectories.
- **URL Extraction**: Automatically extracts URLs from diverse JSON structures.
- **Robust Error Handling**: Provides detailed logging for successful and failed scrapes.

## Usage

```bash
python main.py <input_dir> <output_dir> [options]
```

### Arguments

- `input_dir`: Directory containing JSON files with URLs.
- `output_dir`: Directory where scraped markdown content will be saved.

### Options

- `--verbose, -v`: Enable verbose logging.

## Input Format

JSON files containing URLs in any structure (e.g., from the URL Retrieval stage):

```json
{
  "urls": ["https://example.com", "https://another.com/page.html"],
  "metadata": {"source": "some_source"}
}
```

## Output

Markdown files (`.md`) saved in the specified output directory, mirroring the input JSON file structure.

## Dependencies

- `requests`: For making HTTP requests to the Firecrawl API.
- `json_parser`: Custom module for extracting URLs from JSON.
- `file_finder`: Custom module for finding JSON files.

## Requirements

- Python 3.7+
- A running instance of the self-hosted Firecrawl API (e.g., on `localhost:3002`).