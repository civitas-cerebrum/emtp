import os
import asyncio # New import for asynchronous operations
import random # Keep this import for random delays
import requests
import logging
from selenium.common.exceptions import WebDriverException # Keep for now for return type inference and existing error handling patterns.
from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions # New import
from pydoll.exceptions import PydollException, TimeoutException

# Configure logging for the module
logger = logging.getLogger(__name__)


class ScreenshotCapture:
    """Class for capturing screenshots of web pages using pydoll."""

    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Initialize the ScreenshotCapture instance.

        Args:
            headless (bool): Whether to run browser in headless mode.
            timeout (int): Timeout for page load operations in seconds.
        """
        self.headless = headless
        self.timeout = timeout
        self.browser = None # Renamed from driver to browser for pydoll

    async def _setup_driver(self):
        """Set up the pydoll browser with appropriate options."""
        options = ChromiumOptions()
        options.headless = self.headless # Set headless via options object
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-cookies')
        options.add_argument('--disable-notifications')
        options.add_argument('--test-third-party-cookie-phaseout')
        options.add_argument('--deny-permission-prompts')
        # options.add_argument('--host-resolver-rules="MAP *cookielaw.org 0.0.0.0"') # This might block legitimate content.
        options.add_argument('--disable-blink-features=AutomationControlled') # Evade detection
        options.add_argument(f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(80, 100)}.0.0.0 Safari/537.36') # Randomize user agent

        self.browser = Chrome(options=options) # Pass options object
        await self.browser.start()

    async def capture_full_page_screenshot(self, url: str) -> bytes:
        """
        Capture a full-page screenshot of the given URL using pydoll.

        Args:
            url (str): The URL to capture.

        Returns:
            bytes: The screenshot data as bytes.

        Raises:
            TimeoutException: If the page load or an operation times out.
            PydollException: For other pydoll-related errors.
            WebDriverException: For compatibility with existing error handling patterns.
        """
        if self.browser is None:
            await self._setup_driver()

        try:
            tab = await self.browser.new_tab() # pydoll uses tabs for navigation

            # Enable automatic Cloudflare captcha solving before navigating
            await tab.enable_auto_solve_cloudflare_captcha()

            await tab.go_to(url, timeout=self.timeout * 1000)  # pydoll timeout is in milliseconds

            # Add randomized delays and scrolling to mimic human behavior
            await asyncio.sleep(random.uniform(1, 3)) # Longer, randomized initial sleep

            # Add a randomized delay before interactions
            await asyncio.sleep(random.uniform(1, 3)) # Longer, randomized initial sleep

            # Execute the original cookie removal script
            try:
                script = 'const elementsToRemove = document.querySelectorAll(\'[id*="cookie"], [class*="fc-consent-root"], [class*="overlay"], [class*="ot-fade-in"],[id*="consent"], [class*="consent"]\'); elementsToRemove.forEach(element => {element.remove();});'
                await tab.execute_script(script) # Use execute_script for script execution
                logger.debug("Attempted to remove cookie popups with script.")
            except Exception as e:
                logger.debug(f"Error executing cookie removal script: {e}")

            # pydoll captures full-page screenshot by default. Can specify type and quality.
            screenshot_b64 = await tab.take_screenshot(beyond_viewport=True, as_base64=True)
            import base64
            screenshot = base64.b64decode(screenshot_b64)
            await tab.close() # Close the tab after screenshot
            return screenshot

        except TimeoutException as e:
            raise TimeoutException(f"Page load or operation timed out for URL: {url} - {e}")
        except PydollException as e:
            raise PydollException(f"Pydoll error for URL {url}: {e}")
        except Exception as e: # Catch any other unexpected exceptions
            # For compatibility, re-raise as WebDriverException if appropriate, or a custom exception
            raise WebDriverException(f"An unexpected error occurred for URL {url}: {e}") from e

    async def print_to_pdf(self, url: str) -> bytes:
        """
        Print the given URL to a PDF file using pydoll.

        Args:
            url (str): The URL to print to PDF.

        Returns:
            bytes: The PDF data as bytes.

        Raises:
            TimeoutException: If the page load or an operation times out.
            PydollException: For other pydoll-related errors.
            WebDriverException: For compatibility with existing error handling patterns.
        """
        if self.browser is None:
            await self._setup_driver()

        try:
            tab = await self.browser.new_tab()
            await tab.go_to(url, timeout=self.timeout * 1000)
            
            # Create a temporary file to save the PDF
            temp_pdf_path = f"/tmp/pydoll_print_{os.urandom(8).hex()}.pdf"
            await tab.print_to_pdf(path=temp_pdf_path)
            
            with open(temp_pdf_path, "rb") as f:
                pdf_bytes = f.read()
            os.remove(temp_pdf_path) # Clean up the temporary file

            await tab.close()
            return pdf_bytes
        except TimeoutException as e:
            raise TimeoutException(f"Page print to PDF timed out for URL: {url} - {e}")
        except PydollException as e:
            raise PydollException(f"Pydoll error printing to PDF for URL {url}: {e}")
        except Exception as e:
            raise WebDriverException(f"An unexpected error occurred while printing PDF for URL {url}: {e}") from e

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
        """Close the pydoll browser instance."""
        if self.browser:
            await self.browser.stop()
            self.browser = None

    async def __aenter__(self):
        """Asynchronous context manager entry."""
        if self.browser is None:
            await self._setup_driver()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Asynchronous context manager exit."""
        await self.close()


async def capture_screenshot(url: str, headless: bool = True, timeout: int = 30) -> bytes:
    """
    Convenience asynchronous function to capture a screenshot of a URL using pydoll.

    Args:
        url (str): The URL to capture.
        headless (bool): Whether to run in headless mode.
        timeout (int): Timeout for page loading.

    Returns:
        bytes: The screenshot data.
    """
    async with ScreenshotCapture(headless=headless, timeout=timeout) as capturer:
        return await capturer.capture_full_page_screenshot(url)