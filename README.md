# EMTP - Expert Model Training Pipeline

EMTP is a pipeline for acquiring, processing, and preparing domain-specific data to fine-tune expert AI models. It systematically generates questions, searches the web, scrapes content, generates Q&A pairs, and converts them into multi-turn conversations for training.

## Pipeline Overview

```
Input Questions
     |
1. URL Retrieval ------> Search DuckDuckGo (with optional dorks)
     |
2. Datasource Capture -> Scrape URLs to markdown via Firecrawl
     |
3. Deep-Dive (optional)  Analyze content, generate follow-up questions,
     |                    search & scrape round 2
     |
4. Q&A Generation -----> LLM generates Q&A pairs from all markdown
     |                    (includes deduplication + validation)
     |
5. Conversation --------> LLM converts Q&A into multi-turn dialogues
     |
   Output: conversation_dataset.json
```

## Key Features

- **5-stage pipeline** with interactive menu and full CLI support
- **Deep-dive generation** — second round of search/scrape for deeper content
- **Multi-turn conversations** — transforms flat Q&A into natural dialogues for training
- **LLM provider abstraction** — pluggable providers (Ollama built-in), retry with exponential backoff, connection pooling
- **Pipeline resumability** — tracks completed stages, resume with `--resume` flag
- **Data quality** — Q&A deduplication (exact + near-duplicate), schema validation, minimum/maximum content length filters
- **Dataset versioning** — timestamped snapshots in `datasets/`
- **Export formats** — JSON, CSV, Parquet (`--export csv|parquet`)
- **Data provenance** — each Q&A pair tracks `source_file`, `category`, and `source` (round1/round2)
- **Atomic file writes** — crash-safe JSON output
- **Progress tracking** — `[34/127]` counters in all processing loops
- **Config validation** — required keys checked at startup, optional keys warn with defaults
- **159 tests** passing

## Project Structure

```
emtp/
├── main.py                          # Pipeline orchestrator (interactive + CLI)
├── config.ini                       # Configuration (API endpoints, prompts, model settings)
├── requirements.txt                 # Python dependencies
│
├── dataset/
│   ├── acquisition/
│   │   ├── retrieve_url/            # DuckDuckGo URL search
│   │   │   ├── main.py              # Search orchestration
│   │   │   ├── search_engine.py     # DDGS search with dorks support
│   │   │   └── data_loader.py       # Question JSON normalization (2 formats)
│   │   ├── save_datasource/         # Firecrawl web scraping
│   │   │   ├── main.py              # Batch scrape with retry logic
│   │   │   ├── file_finder.py       # JSON file discovery
│   │   │   └── json_parser.py       # URL extraction from JSON
│   │   └── temp/                    # Intermediate data
│   │       ├── urls/                # Search result URLs (per-category JSON)
│   │       ├── datasources/         # Scraped markdown (round 1)
│   │       ├── datasources_deep/    # Scraped markdown (round 2, deep-dive)
│   │       └── urls_deep/           # Deep-dive search URLs
│   │
│   ├── enrichment/
│   │   ├── deep_dive_generation.py  # Generate follow-up questions from content
│   │   ├── dataset_generation.py    # Q&A pair generation from markdown
│   │   └── conversation_conversion.py # Convert Q&A to multi-turn dialogues
│   │
│   └── questions/
│       ├── question_generation.py   # AI-powered topic-to-questions
│       └── question_categorisation.py # Question categorization
│
├── training/
│   └── train.py                     # SFT training with LoRA (HuggingFace/TRL)
│
├── util/
│   ├── utilities.py                 # Config, logging, config validation
│   ├── llm_client.py                # LLMClient factory
│   ├── llm_providers/
│   │   ├── base.py                  # LLMProvider Protocol + LLMError
│   │   └── ollama.py                # Ollama provider (retry, session pooling)
│   ├── file_utils.py                # Atomic JSON writes
│   ├── pipeline_state.py            # Pipeline resumability tracking
│   ├── schema_validation.py         # Dataset schema validation
│   ├── deduplication.py             # Q&A near-duplicate removal
│   ├── dataset_versioning.py        # Timestamped dataset snapshots
│   └── export.py                    # CSV/Parquet export
│
├── tests/                           # 159 tests (pytest)
└── datasets/                        # Versioned dataset snapshots
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure** `config.ini` with your API endpoints, model name, and authorization token.

3. **Run the interactive pipeline:**
   ```bash
   python main.py
   ```

4. **Or run the full pipeline via CLI:**
   ```bash
   python main.py --stage full_pipeline \
     --questions-file questions.json \
     --verbose
   ```

## CLI Usage

```bash
# Full pipeline
python main.py --stage full_pipeline --questions-file questions.json

# Full pipeline, skip deep-dive for speed
python main.py --stage full_pipeline --questions-file questions.json --skip-deep-dive

# Full pipeline, skip conversation conversion (flat Q&A output only)
python main.py --stage full_pipeline --questions-file questions.json --skip-conversation

# Resume a previously interrupted run
python main.py --stage full_pipeline --questions-file questions.json --resume

# Export to CSV after completion
python main.py --stage full_pipeline --questions-file questions.json --export csv

# Individual stages
python main.py --stage url_retrieval --questions-file questions.json
python main.py --stage datasource_capture
python main.py --stage deep_dive
python main.py --stage qa_generation
python main.py --stage conversation_conversion

# With search operators
python main.py --stage full_pipeline --questions-file questions.json --dorks "filetype:pdf site:stackoverflow.com"
```

## Input Format

Questions JSON (two formats supported):

```json
[
  {
    "category": "Test Automation",
    "questions": [
      "What are best practices for test automation frameworks?",
      "How does Selenium compare to Playwright?"
    ]
  }
]
```

Or legacy format:
```json
{
  "Test Automation": ["What are best practices for test automation frameworks?"]
}
```

## Output Formats

**Q&A Dataset** (`qna_dataset.json`):
```json
[
  {
    "q": "What is shift-left testing?",
    "a": "Shift-left testing is a practice where testing activities are performed earlier...",
    "category": "Testing",
    "source": "round1",
    "source_file": "testing/www_example_com_article.md"
  }
]
```

**Conversation Dataset** (`conversation_dataset.json`):
```json
[
  {
    "messages": [
      {"role": "user", "content": "Can you explain shift-left testing?"},
      {"role": "assistant", "content": "Shift-left testing is a practice where..."},
      {"role": "user", "content": "How does that differ from traditional QA?"},
      {"role": "assistant", "content": "In traditional workflows..."}
    ]
  }
]
```

## Configuration

Key settings in `config.ini`:

| Key | Description | Default |
|-----|-------------|---------|
| `model_name` | Ollama model for LLM calls | `gemma3:27b` |
| `model_expertise` | Domain expertise for prompts | `Quality Assurance` |
| `owui_base_url` | Base URL for Ollama API | Required |
| `ollama_uri` | Ollama generate endpoint path | Required |
| `authorization_token` | Bearer token for API auth | Optional |
| `firecrawl_url` | Firecrawl instance URL | `http://localhost:3002` |
| `search_result_count` | URLs per question | `10` |
| `request_timeout` | LLM request timeout (seconds) | `60` |
| `min_content_length` | Skip markdown files below this (chars) | `200` |
| `max_content_length` | Truncate documents above this (chars, 0=off) | `0` |
| `conversation_batch_size` | Q&A pairs per conversation batch | `8` |

## Training

The training script fine-tunes models using SFT (Supervised Fine-Tuning) with LoRA:

```bash
python training/train.py
```

Supports both conversation format (multi-turn) and legacy Q&A format. Uses HuggingFace Transformers + TRL + PEFT with BitsAndBytes quantization.

## Testing

```bash
# Run all 159 tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_llm_client.py -v
```

## Architecture

### LLM Provider Abstraction

All LLM calls go through a shared `LLMClient` with pluggable providers:

```
LLMClient (factory: create_llm_client())
  └── OllamaProvider
        ├── requests.Session (connection pooling)
        ├── Retry with exponential backoff (3 retries on 429/5xx/connection errors)
        └── Response parsing (handles string/dict/list responses)
```

To add a new provider, implement the `LLMProvider` protocol in `util/llm_providers/` and add it to the factory.

### Pipeline State

The `--resume` flag uses `.pipeline_state.json` to track completed stages. If a run is interrupted, resuming skips already-completed stages.

### Data Quality

- **Deduplication**: Normalizes question text (lowercase, strip punctuation) and hashes to detect near-duplicates
- **Schema validation**: Validates Q&A and conversation datasets at stage boundaries
- **Content filtering**: Skips files below `min_content_length`, truncates above `max_content_length`

## Requirements

- Python 3.10+
- Internet connection for web searches and scraping
- Ollama-compatible LLM API endpoint
- Firecrawl instance (local or external)
- For training: CUDA-capable GPU with PyTorch
