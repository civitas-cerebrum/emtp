# Dataset

This directory contains all data related to the Expert Model Training Pipeline (EMTP). It is structured to manage the acquisition, storage, and processing of data necessary for training and evaluating expert models.

## Subdirectories:

*   **[`acquisition/`](dataset/acquisition)**: Handles all processes related to acquiring raw data, primarily through web scraping via Firecrawl API (supports local and external instances), which outputs content directly as markdown files. It also includes URL retrieval and an optional datasource processing step for non-Firecrawl acquired data.
*   **[`enrichment/`](dataset/enrichment)**: Focuses on transforming, cleaning, and enhancing raw data into a format suitable for model training. This includes feature engineering, data normalization, and annotation.
*   **[`questions/`](dataset/questions)**: Stores structured questions or prompts used for data acquisition or model evaluation. This might include QA datasets, interview questions, or specific queries used to extract information.