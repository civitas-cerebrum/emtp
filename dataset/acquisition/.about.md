# Data Acquisition

This directory contains modules responsible for acquiring raw data from various sources. Each subdirectory represents a distinct stage in the data acquisition process.

## Subdirectories:

*   **[`retrieve_url/`](dataset/acquisition/retrieve_url)**: Responsible for searching and retrieving relevant URLs based on predefined questions or queries, with support for DuckDuckGo search operators (dorks).
*   **[`save_datasource/`](dataset/acquisition/save_datasource)**: Handles capturing screenshots of web pages and downloading PDF files from the retrieved URLs, converting web content into visual and document data.
*   **[`datasource_processing/`](dataset/acquisition/datasource_processing)**: Processes captured screenshots and downloaded PDFs to extract text content using OCR and PDF parsing.