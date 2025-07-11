"""
Browser Utilities for Facebook Marketplace Bot
Advanced Playwright management with anti-detection features
"""

import time
import random
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from playwright.sync_api import sync_playwright, Browser as SyncBrowser, BrowserContext as SyncBrowserContext, Page as SyncPage
from fake_useragent import UserAgent

from config import Config
from utils.logger import get_logger


class PlaywrightBrowserManager:
    """
    Advanced browser management with Playwright and anti-detection features

    Features:
    - Automatic Playwright setup and management
    - Random user agents and browser fingerprints
    - Human-like delays and mouse movements
    - Screenshot capture for debugging
    - Session persistence and recovery
    - Anti-detection measures
    - Both sync and async support
    """

    def __init__(self, headless: bool = None, user_data_dir: Optional[str] = None, async_mode: bool = False):
        """
        Initialize PlaywrightBrowserManager

        Args:
            headless: Run browser in headless mode (None = use config)
            user_data_dir: Custom user data directory for session persistence
            async_mode: Use async Playwright (recommended for better performance)
        """
        self.logger = get_logger(__name__)
        self.async_mode = async_mode

        # Playwright objects
        self.playwright: Optional[Union[Playwright, any]] = None
        self.browser: Optional[Union[Browser, SyncBrowser]] = None
        self.context: Optional[Union[BrowserContext, SyncBrowserContext]] = None
        self.page: Optional[Union[Page, SyncPage]] = None

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

        self.logger.info(f"PlaywrightBrowserManager initialized (async={async_mode})")

    async def setup_browser_async(self, profile_name: str = "default") -> bool:
        """
        Set up Playwright browser with anti-detection features (async)

        Args:
            profile_name: Name for the browser profile

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("🚀 Setting up Playwright browser (async)...")

            # Start Playwright
            self.playwright = await async_playwright().start()

            # Configure browser options
            browser_options = self._get_browser_options(profile_name)

            # For user data persistence, use launch_persistent_context instead
            if self.user_data_dir:
                # Use persistent context for user data
                user_data_path = Path(self.user_data_dir or f'./browser_data/{profile_name}')
                user_data_path.mkdir(parents=True, exist_ok=True)

                context_options = self._get_context_options()
                context_options.update(browser_options)

                self.context = await self.playwright.chromium.launch_persistent_context(
                    str(user_data_path),
                    **context_options
                )
                self.browser = None  # Not needed with persistent context

                # Create page from context
                if len(self.context.pages) > 0:
                    self.page = self.context.pages[0]
                else:
                    self.page = await self.context.new_page()
            else:
                # Standard browser launch without persistence
                self.browser = await self.playwright.chromium.launch(**browser_options)

                # Create context with anti-detection
                context_options = self._get_context_options()
                self.context = await self.browser.new_context(**context_options)

                # Create page
                self.page = await self.context.new_page()

            # Apply anti-detection measures
            await self._apply_anti_detection_async()

            self.logger.info("✅ Playwright browser setup completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to setup browser: {e}")
            await self.cleanup_async()
            return False

    def setup_browser_sync(self, profile_name: str = "default") -> bool:
        """
        Set up Playwright browser with anti-detection features (sync)

        Args:
            profile_name: Name for the browser profile

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("🚀 Setting up Playwright browser (sync)...")

            # Start Playwright
            self.playwright = sync_playwright().start()

            # Configure browser options
            browser_options = self._get_browser_options(profile_name)

            # For user data persistence, use launch_persistent_context instead
            if self.user_data_dir:
                # Use persistent context for user data
                user_data_path = Path(self.user_data_dir or f'./browser_data/{profile_name}')
                user_data_path.mkdir(parents=True, exist_ok=True)

                context_options = self._get_context_options()
                context_options.update(browser_options)

                self.context = self.playwright.chromium.launch_persistent_context(
                    str(user_data_path),
                    **context_options
                )
                self.browser = None  # Not needed with persistent context

                # Create page from context
                if len(self.context.pages) > 0:
                    self.page = self.context.pages[0]
                else:
                    self.page = self.context.new_page()
            else:
                # Standard browser launch without persistence
                self.browser = self.playwright.chromium.launch(**browser_options)

                # Create context with anti-detection
                context_options = self._get_context_options()
                self.context = self.browser.new_context(**context_options)

                # Create page
                self.page = self.context.new_page()

            # Apply anti-detection measures
            self._apply_anti_detection_sync()

            self.logger.info("✅ Playwright browser setup completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to setup browser: {e}")
            self.cleanup_sync()
            return False

    def _get_browser_options(self, profile_name: str) -> Dict[str, Any]:
        """Get browser launch options"""
        return {
            "headless": self.headless,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions-except",
                "--disable-extensions",
                "--no-first-run",
                "--disable-default-apps",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection"
                # Removed --user-data-dir from args since Playwright handles it differently
            ]
        }

    def _get_context_options(self) -> Dict[str, Any]:
        """Get browser context options with anti-detection"""
        self.current_user_agent = self.ua.random

        return {
            "user_agent": self.current_user_agent,
            "viewport": {"width": 1920, "height": 1080},
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation"],
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        }

    async def _apply_anti_detection_async(self):
        """Apply anti-detection measures (async)"""
        # Remove webdriver property
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)

        # Override plugins
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)

        # Override languages
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)

    def _apply_anti_detection_sync(self):
        """Apply anti-detection measures (sync)"""
        # Remove webdriver property
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)

        # Override plugins
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)

        # Override languages
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)

    async def navigate_to_async(self, url: str, wait_for: str = "load") -> bool:
        """
        Navigate to URL (async)

        Args:
            url: URL to navigate to
            wait_for: What to wait for ("load", "domcontentloaded", "networkidle")

        Returns:
            True if successful, False otherwise
        """
        try:
            start_time = time.time()
            self.logger.info(f"🌐 Navigating to: {url}")

            await self.page.goto(url, wait_until=wait_for, timeout=30000)

            load_time = time.time() - start_time
            self.page_load_times.append(load_time)
            self.logger.info(f"✅ Page loaded in {load_time:.2f}s")

            return True

        except Exception as e:
            self.logger.error(f"❌ Navigation failed: {e}")
            return False

    def navigate_to_sync(self, url: str, wait_for: str = "load") -> bool:
        """
        Navigate to URL (sync)

        Args:
            url: URL to navigate to
            wait_for: What to wait for ("load", "domcontentloaded", "networkidle")

        Returns:
            True if successful, False otherwise
        """
        try:
            start_time = time.time()
            self.logger.info(f"🌐 Navigating to: {url}")

            self.page.goto(url, wait_until=wait_for, timeout=30000)

            load_time = time.time() - start_time
            self.page_load_times.append(load_time)
            self.logger.info(f"✅ Page loaded in {load_time:.2f}s")

            return True

        except Exception as e:
            self.logger.error(f"❌ Navigation failed: {e}")
            return False

    async def find_element_async(self, selector: str, timeout: int = 5000) -> Optional[any]:
        """
        Find element using CSS selector (async)

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds

        Returns:
            Element if found, None otherwise
        """
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            return element
        except Exception as e:
            self.logger.warning(f"Element not found: {selector} - {e}")
            return None

    def find_element_sync(self, selector: str, timeout: int = 5000) -> Optional[any]:
        """
        Find element using CSS selector (sync)

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds

        Returns:
            Element if found, None otherwise
        """
        try:
            element = self.page.wait_for_selector(selector, timeout=timeout)
            return element
        except Exception as e:
            self.logger.warning(f"Element not found: {selector} - {e}")
            return None

    async def click_element_async(self, selector: str, timeout: int = 5000) -> bool:
        """
        Click element with human-like behavior (async)

        Args:
            selector: CSS selector or element
            timeout: Timeout in milliseconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add human delay
            await self.human_delay_async()

            # Click element
            await self.page.click(selector, timeout=timeout)

            self.logger.debug(f"Clicked element: {selector}")
            return True

        except Exception as e:
            self.logger.error(f"Click failed on {selector}: {e}")
            return False

    def click_element_sync(self, selector: str, timeout: int = 5000) -> bool:
        """
        Click element with human-like behavior (sync)

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add human delay
            self.human_delay_sync()

            # Click element
            self.page.click(selector, timeout=timeout)

            self.logger.debug(f"Clicked element: {selector}")
            return True

        except Exception as e:
            self.logger.error(f"Click failed on {selector}: {e}")
            return False

    async def type_text_async(self, selector: str, text: str, delay: int = 50) -> bool:
        """
        Type text with human-like delays (async)

        Args:
            selector: CSS selector
            text: Text to type
            delay: Delay between keystrokes in milliseconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear field first
            await self.page.fill(selector, "")

            # Type with human-like delay
            await self.page.type(selector, text, delay=delay)

            self.logger.debug(f"Typed text into {selector}")
            return True

        except Exception as e:
            self.logger.error(f"Type failed on {selector}: {e}")
            return False

    def type_text_sync(self, selector: str, text: str, delay: int = 50) -> bool:
        """
        Type text with human-like delays (sync)

        Args:
            selector: CSS selector
            text: Text to type
            delay: Delay between keystrokes in milliseconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear field first
            self.page.fill(selector, "")

            # Type with human-like delay
            self.page.type(selector, text, delay=delay)

            self.logger.debug(f"Typed text into {selector}")
            return True

        except Exception as e:
            self.logger.error(f"Type failed on {selector}: {e}")
            return False

    async def human_delay_async(self, min_delay: float = 0.5, max_delay: float = 2.0):
        """Add human-like delay (async)"""
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)

    def human_delay_sync(self, min_delay: float = 0.5, max_delay: float = 2.0):
        """Add human-like delay (sync)"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    async def take_screenshot_async(self, filename: Optional[str] = None) -> str:
        """
        Take screenshot for debugging (async)

        Args:
            filename: Custom filename (optional)

        Returns:
            Screenshot filename
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}_{self.screenshot_counter}.png"
            self.screenshot_counter += 1

        screenshot_path = Path("screenshots") / filename
        screenshot_path.parent.mkdir(exist_ok=True)

        await self.page.screenshot(path=str(screenshot_path), full_page=True)
        self.logger.info(f"📸 Screenshot saved: {screenshot_path}")

        return str(screenshot_path)

    def take_screenshot_sync(self, filename: Optional[str] = None) -> str:
        """
        Take screenshot for debugging (sync)

        Args:
            filename: Custom filename (optional)

        Returns:
            Screenshot filename
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}_{self.screenshot_counter}.png"
            self.screenshot_counter += 1

        screenshot_path = Path("screenshots") / filename
        screenshot_path.parent.mkdir(exist_ok=True)

        self.page.screenshot(path=str(screenshot_path), full_page=True)
        self.logger.info(f"📸 Screenshot saved: {screenshot_path}")

        return str(screenshot_path)

    async def cleanup_async(self):
        """Clean up browser resources (async)"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

            self.logger.info("🧹 Browser cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def cleanup_sync(self):
        """Clean up browser resources (sync)"""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()

            self.logger.info("🧹 Browser cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def __enter__(self):
        """Context manager entry"""
        if self.async_mode:
            raise RuntimeError("Use async context manager for async mode")
        self.setup_browser_sync()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup_sync()

    async def __aenter__(self):
        """Async context manager entry"""
        await self.setup_browser_async()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup_async()


# Convenience functions for backward compatibility
def find_element_robust(browser_manager, selectors: List[str], timeout: int = 5000):
    """
    Try multiple selectors to find an element

    Args:
        browser_manager: PlaywrightBrowserManager instance
        selectors: List of CSS selectors
        timeout: Timeout for each selector attempt

    Returns:
        Element if found, None otherwise
    """
    for selector in selectors:
        element = browser_manager.find_element_sync(selector, timeout=timeout)
        if element:
            return element
    return None