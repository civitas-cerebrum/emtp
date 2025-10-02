"""
Module for capturing screenshots of web pages using Selenium.
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ScreenshotCapture:
    """Class for capturing screenshots of web pages."""

    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Initialize the ScreenshotCapture instance.

        Args:
            headless (bool): Whether to run browser in headless mode.
            timeout (int): Timeout for page loading in seconds.
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None

    def _setup_driver(self):
        """Set up the Chrome WebDriver with appropriate options."""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        # Removed --disable-images and --disable-javascript for better screenshot quality
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-cookies")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--test-third-party-cookie-phaseout")
        chrome_options.add_argument("--deny-permission-prompts")
        chrome_options.add_argument("--host-resolver-rules='MAP *cookielaw.org 0.0.0.0'")
        chrome_options.add_experimental_option("prefs", {"profile.cookie_controls_mode": 1})
        chrome_options.add_experimental_option("prefs", {"profile.default_content_setting_values.cookies": 2})
        
        # Install and use ChromeDriver
        self.driver = webdriver.Chrome(options=chrome_options)

        # Set page load timeout
        self.driver.set_page_load_timeout(self.timeout)

    def capture_full_page_screenshot(self, url: str) -> bytes:
        """
        Capture a full-page screenshot of the given URL.

        Args:
            url (str): The URL to capture.

        Returns:
            bytes: The screenshot data as bytes.

        Raises:
            WebDriverException: If there's an error with the WebDriver.
            TimeoutException: If the page takes too long to load.
        """
        if self.driver is None:
            self._setup_driver()

        try:
            self.driver.get(url)

            # Wait for the document to be in a 'complete' state
            WebDriverWait(self.driver, self.timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            # Optional: Add a short, minimal sleep for dynamic content to settle
            time.sleep(0.5)

            # Get the full page height
            total_height = self.driver.execute_script(
                "return Math.max(document.body.scrollHeight, document.body.offsetHeight, "
                "document.documentElement.clientHeight, document.documentElement.scrollHeight, "
                "document.documentElement.offsetHeight);"
            )

            try:
                script = 'const elementsToRemove = document.querySelectorAll(\'[id*="cookie"], [class*="fc-consent-root"], [class*="overlay"], [class*="ot-fade-in"],[id*="consent"], [class*="consent"]\'); elementsToRemove.forEach(element => {element.remove();});'

                self.driver.execute_script(script)
                print("Google cookie popup removed!")

            except Exception as ignored:
                print("No google cookie popup!")

            # Set window size to capture full page
            self.driver.set_window_size(1920, total_height)

            # Take screenshot
            screenshot = self.driver.get_screenshot_as_png()

            return screenshot

        except TimeoutException:
            raise TimeoutException(f"Page load timeout for URL: {url}")
        except WebDriverException as e:
            raise WebDriverException(f"WebDriver error for URL {url}: {e}")


    def close(self):
        """Close the WebDriver instance."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def capture_screenshot(url: str, headless: bool = True, timeout: int = 30) -> bytes:
    """
    Convenience function to capture a screenshot of a URL.

    Args:
        url (str): The URL to capture.
        headless (bool): Whether to run in headless mode.
        timeout (int): Timeout for page loading.

    Returns:
        bytes: The screenshot data.
    """
    with ScreenshotCapture(headless=headless, timeout=timeout) as capturer:
        return capturer.capture_full_page_screenshot(url)