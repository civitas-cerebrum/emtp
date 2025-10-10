# URL Retrieval Module

Retrieves relevant URLs for questions using DuckDuckGo search.

## Features

- **DuckDuckGo Search**: Privacy-focused URL retrieval
- **DuckDuckGo Dorks Support**: Optional search operators (filetype:, site:, intitle:, inurl:, etc.)
- **Unicode Handling**: Normalizes special characters in questions
- **Categorized Processing**: Processes questions by category
- **JSON Output**: Structured results per category
- **Backward Compatibility**: Supports both legacy and new JSON formats

## Input Format

JSON file with categorized questions:
```json
{
  "Category Name": [
    "Question 1?",
    "Question 2?"
  ]
}
```

## Command Line Options

- `--dorks`: Apply DuckDuckGo search operators to all searches (optional)
  - Examples: `filetype:pdf`, `site:example.com`, `intitle:keyword`
  - Multiple operators can be combined: `filetype:pdf site:example.com`
  - Supported operators:
    - `filetype:pdf` - Search for PDF files
    - `site:example.com` - Search within a specific site
    - `intitle:keyword` - Search in page titles
    - `inurl:keyword` - Search in URLs
    - `-exclude` - Exclude terms
    - `"exact phrase"` - Search for exact phrases

## Output

Creates JSON files with search results containing URLs and metadata.

## Usage

```python
from dataset.acquisition.retrieve_url.main import main

# Run with default questions file
main()

# Run with custom questions file
main(questions_file="path/to/questions.json")

# Run with dorks applied to all searches
main(dorks="filetype:pdf site:example.com")
```

### Command Line

```bash
# Basic usage
python main.py

# With dorks
python main.py --dorks "filetype:pdf"

# With custom questions file and dorks
python main.py --questions-file custom_questions.json --dorks "site:stackoverflow.com"
```

## Dependencies

- ddgs (DuckDuckGo search API)
- Standard Python libraries