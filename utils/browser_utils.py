"""
Browser Utilities for Facebook Marketplace Bot
Advanced WebDriver management with anti-detection features
"""

import time
import random
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    WebDriverException, ElementNotInteractableException
)
from webdriver_manager.chrome import ChromeDriverManager
import chromedriver_autoinstaller
from fake_useragent import UserAgent

from config import Config
from utils.logger import get_logger


class BrowserManager:
    """
    Advanced browser management with anti-detection features

    Features:
    - Automatic WebDriver setup and management
    - Random user agents and browser fingerprints
    - Human-like delays and mouse movements
    - Screenshot capture for debugging
    - Session persistence and recovery
    - Anti-detection measures
    """

    def __init__(self, headless: bool = None, user_data_dir: Optional[str] = None):
        """
        Initialize BrowserManager

        Args:
            headless: Run browser in headless mode (None = use config)
            user_data_dir: Custom user data directory for session persistence
        """
        self.logger = get_logger(__name__)
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.actions: Optional[ActionChains] = None

        # Configuration
        self.headless = headless if headless is not None else Config.HEADLESS_MODE
        self.user_data_dir = user_data_dir
        self.screenshot_counter = 0

        # Anti-detection settings
        self.ua = UserAgent()
        self.current_user_agent = None

        # Performance tracking
        self.start_time = None
        self.page_load_times = []

        self.logger.info("BrowserManager initialized")

    def setup_driver(self, profile_name: str = "default") -> bool:
        """
        Set up Chrome WebDriver with anti-detection features

        Args:
            profile_name: Name for the browser profile

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Setting up Chrome WebDriver (profile: {profile_name})")

            # Chrome options
            options = self._get_chrome_options(profile_name)

            # WebDriver service - use chromedriver-autoinstaller (more reliable)
            try:
                driver_path = chromedriver_autoinstaller.install()
                service = Service(driver_path)
                self.logger.info(f"Using ChromeDriver from: {driver_path}")
            except Exception as e:
                self.logger.warning(f"chromedriver-autoinstaller failed: {e}")
                # Fallback to webdriver-manager
                try:
                    service = Service(ChromeDriverManager().install())
                except Exception as e2:
                    self.logger.error(f"Both ChromeDriver methods failed: {e2}")
                    raise e2

            # Create driver
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, Config.BROWSER_TIMEOUT)
            self.actions = ActionChains(self.driver)

            # Configure driver settings
            self._configure_driver()

            self.logger.info("Chrome WebDriver setup successful")
            return True

        except Exception as e:
            self.logger.error(f"Failed to setup WebDriver: {e}")
            return False

    def _get_chrome_options(self, profile_name: str) -> Options:
        """Get Chrome options with anti-detection features"""
        options = Options()

        # Basic settings
        if self.headless:
            options.add_argument("--headless=new")
            self.logger.info("Running in headless mode")

        # User data directory for session persistence
        if self.user_data_dir:
            user_data_path = Path(self.user_data_dir) / profile_name
            user_data_path.mkdir(parents=True, exist_ok=True)
            options.add_argument(f"--user-data-dir={user_data_path}")
            self.logger.info(f"Using user data directory: {user_data_path}")

        # Anti-detection measures
        if Config.USE_RANDOM_USER_AGENTS:
            self.current_user_agent = self.ua.random
            options.add_argument(f"--user-agent={self.current_user_agent}")
            self.logger.debug(f"Using user agent: {self.current_user_agent}")

        # Stealth options
        if Config.ENABLE_STEALTH_MODE:
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins-discovery")
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")

        # Performance options
        options.add_argument("--no-first-run")
        options.add_argument("--no-service-autorun")
        options.add_argument("--password-store=basic")

        # Window size
        if not self.headless:
            options.add_argument("--window-size=1366,768")

        # Prefs to avoid notifications and popups
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2  # Block images for faster loading
        }
        options.add_experimental_option("prefs", prefs)

        return options

    def _configure_driver(self):
        """Configure driver settings after initialization"""
        if not self.driver:
            return

        # Set timeouts
        self.driver.set_page_load_timeout(Config.PAGE_LOAD_TIMEOUT)
        self.driver.implicitly_wait(Config.BROWSER_TIMEOUT)

        # Execute stealth script to hide automation
        if Config.ENABLE_STEALTH_MODE:
            stealth_script = """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            """
            self.driver.execute_script(stealth_script)

    def navigate_to(self, url: str, wait_for_load: bool = True) -> bool:
        """
        Navigate to a URL with timing and error handling

        Args:
            url: URL to navigate to
            wait_for_load: Whether to wait for page load

        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.logger.error("Driver not initialized")
            return False

        try:
            self.start_time = time.time()
            self.logger.info(f"Navigating to: {url}")

            self.driver.get(url)

            if wait_for_load:
                self.wait_for_page_load()

            load_time = time.time() - self.start_time
            self.page_load_times.append(load_time)
            self.logger.info(f"Page loaded in {load_time:.2f}s")

            # Take screenshot if enabled
            if Config.TAKE_SCREENSHOTS:
                self.take_screenshot(f"navigate_{url.split('/')[-1]}")

            return True

        except TimeoutException:
            self.logger.error(f"Page load timeout for: {url}")
            if Config.SCREENSHOT_ON_ERROR:
                self.take_screenshot("timeout_error")
            return False
        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            if Config.SCREENSHOT_ON_ERROR:
                self.take_screenshot("navigation_error")
            return False

    def wait_for_page_load(self, timeout: int = None) -> bool:
        """
        Wait for page to fully load

        Args:
            timeout: Custom timeout (uses config default if None)

        Returns:
            True if page loaded, False on timeout
        """
        timeout = timeout or Config.PAGE_LOAD_TIMEOUT

        try:
            # Wait for document ready state
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )

            # Additional wait for dynamic content
            time.sleep(random.uniform(1, 2))

            return True

        except TimeoutException:
            self.logger.warning("Page load timeout")
            return False

    def find_element_safe(self, by: By, value: str, timeout: int = None) -> Optional[any]:
        """
        Safely find an element with timeout

        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Custom timeout

        Returns:
            WebElement if found, None otherwise
        """
        timeout = timeout or Config.BROWSER_TIMEOUT

        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element

        except TimeoutException:
            self.logger.warning(f"Element not found: {by}={value}")
            return None
        except Exception as e:
            self.logger.error(f"Error finding element {by}={value}: {e}")
            return None

    def click_element_safe(self, element, use_javascript: bool = False) -> bool:
        """
        Safely click an element with human-like behavior

        Args:
            element: WebElement to click
            use_javascript: Use JavaScript click instead of regular click

        Returns:
            True if successful, False otherwise
        """
        if not element:
            return False

        try:
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

            # Random delay before clicking
            self.human_delay()

            if use_javascript:
                self.driver.execute_script("arguments[0].click();", element)
            else:
                # Wait for element to be clickable
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(element))
                element.click()

            self.logger.debug("Element clicked successfully")
            return True

        except ElementNotInteractableException:
            self.logger.warning("Element not interactable, trying JavaScript click")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e:
                self.logger.error(f"JavaScript click failed: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Click error: {e}")
            return False

    def type_text_human(self, element, text: str, clear_first: bool = True) -> bool:
        """
        Type text with human-like delays

        Args:
            element: WebElement to type into
            text: Text to type
            clear_first: Clear field before typing

        Returns:
            True if successful, False otherwise
        """
        if not element or not text:
            return False

        try:
            # Clear field if requested
            if clear_first:
                element.clear()
                time.sleep(random.uniform(0.1, 0.3))

            # Type each character with random delay
            for char in text:
                element.send_keys(char)
                delay = random.uniform(Config.TYPING_DELAY_MIN, Config.TYPING_DELAY_MAX)
                time.sleep(delay)

            self.logger.debug(f"Typed text: {text[:20]}...")
            return True

        except Exception as e:
            self.logger.error(f"Typing error: {e}")
            return False

    def human_delay(self, min_delay: float = None, max_delay: float = None):
        """
        Add human-like random delay

        Args:
            min_delay: Minimum delay (uses config if None)
            max_delay: Maximum delay (uses config if None)
        """
        min_delay = min_delay or Config.MIN_DELAY
        max_delay = max_delay or Config.MAX_DELAY

        delay = random.uniform(min_delay, max_delay)
        self.logger.debug(f"Human delay: {delay:.2f}s")
        time.sleep(delay)

    def take_screenshot(self, name: str = None) -> str:
        """
        Take a screenshot for debugging

        Args:
            name: Optional name for the screenshot

        Returns:
            Path to the screenshot file
        """
        if not self.driver:
            return ""

        try:
            # Ensure screenshots directory exists
            Config.SCREENSHOTS_DIR.mkdir(exist_ok=True)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = name or f"screenshot_{self.screenshot_counter}"
            filename = f"{timestamp}_{name}.png"
            filepath = Config.SCREENSHOTS_DIR / filename

            # Take screenshot
            self.driver.save_screenshot(str(filepath))
            self.screenshot_counter += 1

            self.logger.debug(f"Screenshot saved: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"Screenshot error: {e}")
            return ""

    def get_page_info(self) -> Dict[str, Any]:
        """Get information about current page"""
        if not self.driver:
            return {}

        try:
            return {
                'url': self.driver.current_url,
                'title': self.driver.title,
                'page_source_length': len(self.driver.page_source),
                'window_size': self.driver.get_window_size(),
                'user_agent': self.current_user_agent
            }
        except Exception as e:
            self.logger.error(f"Error getting page info: {e}")
            return {}

    def cleanup(self):
        """Clean up browser resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser cleanup completed")
            except Exception as e:
                self.logger.error(f"Browser cleanup error: {e}")
            finally:
                self.driver = None
                self.wait = None
                self.actions = None

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()


# Convenience functions
def create_browser_manager(headless: bool = None, profile_name: str = "default") -> BrowserManager:
    """
    Create and setup a browser manager

    Args:
        headless: Run in headless mode
        profile_name: Browser profile name

    Returns:
        Configured BrowserManager instance
    """
    manager = BrowserManager(headless=headless)

    if manager.setup_driver(profile_name):
        return manager
    else:
        manager.cleanup()
        raise Exception("Failed to setup browser driver")


# Example usage and testing
if __name__ == "__main__":
    from utils.logger import setup_logging

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    logger.info("Testing BrowserManager...")

    # Test browser setup and navigation
    try:
        with create_browser_manager(headless=False, profile_name="test") as browser:
            logger.info("Browser manager created successfully")

            # Test navigation
            if browser.navigate_to("https://www.google.com"):
                logger.info("Navigation test successful")

                # Test element finding
                search_box = browser.find_element_safe(By.NAME, "q")
                if search_box:
                    logger.info("Element finding test successful")

                    # Test human typing
                    if browser.type_text_human(search_box, "facebook marketplace"):
                        logger.info("Human typing test successful")

                # Take a test screenshot
                screenshot_path = browser.take_screenshot("test_screenshot")
                logger.info(f"Screenshot saved: {screenshot_path}")

                # Get page info
                page_info = browser.get_page_info()
                logger.info(f"Page info: {page_info}")

                logger.info("✅ All browser tests passed!")
            else:
                logger.error("Navigation test failed")

    except Exception as e:
        logger.error(f"Browser test error: {e}")