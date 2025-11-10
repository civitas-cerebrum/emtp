"""
Data Acquisition Module

This module provides access to the different stages of data acquisition:
- retrieve_url: Retrieves URLs based on questions from qa_questions.json
- save_datasource: Scrapes web content using Firecrawl API
"""

from .retrieve_url.main import main as retrieve_url_stage
from .save_datasource.main import main_async as save_datasource_stage

__all__ = ["retrieve_url_stage", "save_datasource_stage"]