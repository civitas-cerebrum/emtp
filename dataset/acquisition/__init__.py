"""
Data Acquisition Module

This module provides access to the different stages of data acquisition:
- retrieve_url: Retrieves URLs based on questions from qa_questions.json
- save_screenshot: Captures screenshots from retrieved URLs
"""

from .retrieve_url.main import main as retrieve_url_stage
from .save_datasource.main import main_async as save_datasource_stage
from .datasource_processing.main import main as datasource_processing_stage

__all__ = ["retrieve_url_stage", "save_datasource_stage", "datasource_processing_stage"]