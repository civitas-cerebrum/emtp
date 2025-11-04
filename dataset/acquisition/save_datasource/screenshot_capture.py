import os
import asyncio # Keep for async compatibility
import requests
import logging
from selenium.common.exceptions import WebDriverException # Keep for compatibility

# Configure logging for the module
logger = logging.getLogger(__name__)


class ScreenshotCapture:
    """Class for capturing web page content using Firecrawl API."""

    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Initialize the ScreenshotCapture instance.

        Args:
            headless (bool): Ignored, kept for compatibility.
            timeout (int): Timeout for API requests in seconds.
        """
        self.timeout = timeout
        self.base_url = "http://localhost:3002"

    async def capture_full_page_screenshot(self, url: str) -> bytes:
        """
        Scrape the given URL using Firecrawl API and return markdown content.

        Args:
            url (str): The URL to scrape.

        Returns:
            bytes: The markdown content as bytes.

        Raises:
            WebDriverException: For compatibility with existing error handling patterns.
        """
        try:
            response = requests.post(
                f"{self.base_url}/v2/scrape",
                json={"url": url, "formats": ["markdown"]},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("success"):
                raise WebDriverException(f"Firecrawl API returned success=false for URL {url}")
            markdown = data["data"]["markdown"]
            return markdown.encode('utf-8')
        except requests.exceptions.Timeout:
            raise WebDriverException(f"Request timed out for URL {url}")
        except requests.exceptions.RequestException as e:
            raise WebDriverException(f"Request failed for URL {url}: {e}")
        except KeyError as e:
            raise WebDriverException(f"Unexpected response format for URL {url}: {e}")

    async def download_pdf(self, url: str) -> bytes:
        """
        Download a PDF file from the given URL.

        Args:
            url (str): The URL of the PDF to download.

        Returns:
            bytes: The PDF data as bytes.

        Raises:
            Exception: If the download fails or the response is not a PDF.
        """
        try:
            # Set a user agent to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            # Check if the response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'application/pdf' not in content_type and not url.lower().endswith('.pdf'):
                raise Exception(f"URL does not appear to be a PDF. Content-Type: {content_type}")

            return response.content

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to download PDF from {url}: {e}")
        except Exception as e:
            raise Exception(f"An error occurred while downloading PDF from {url}: {e}")

    async def close(self):
        """No-op for compatibility."""
        pass

    async def __aenter__(self):
        """Asynchronous context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Asynchronous context manager exit."""
        await self.close()


async def capture_screenshot(url: str, headless: bool = True, timeout: int = 30) -> bytes:
    """
    Convenience asynchronous function to scrape a URL using Firecrawl.

    Args:
        url (str): The URL to scrape.
        headless (bool): Ignored, kept for compatibility.
        timeout (int): Timeout for API request.

    Returns:
        bytes: The markdown content.
    """
    async with ScreenshotCapture(headless=headless, timeout=timeout) as capturer:
        return await capturer.capture_full_page_screenshot(url)