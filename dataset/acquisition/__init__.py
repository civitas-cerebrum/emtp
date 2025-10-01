"""
Data Acquisition Module

This module provides access to the different stages of data acquisition:
- retrieve_url: Retrieves URLs based on questions from qa_questions.json
- save_screenshot: Captures screenshots from retrieved URLs
"""

from .retrieve_url.main import main as retrieve_url_stage
from .save_screenshot.main import main as save_screenshot_stage
from .screenshot_processing.main import main as screenshot_processing_stage
 
__all__ = ["retrieve_url_stage", "save_screenshot_stage", "screenshot_processing_stage"]