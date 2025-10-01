# URL Retrieval Module

Retrieves relevant URLs for questions using DuckDuckGo search.

## Features

- **DuckDuckGo Search**: Privacy-focused URL retrieval
- **Unicode Handling**: Normalizes special characters in questions
- **Categorized Processing**: Processes questions by category
- **JSON Output**: Structured results per category

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

## Output

Creates JSON files with search results containing URLs and metadata.

## Usage

```python
from dataset.acquisition.retrieve_url.main import main

# Run with default questions file
main()

# Run with custom questions file
main(questions_file="path/to/questions.json")
```

## Dependencies

- ddgs (DuckDuckGo search API)
- Standard Python libraries