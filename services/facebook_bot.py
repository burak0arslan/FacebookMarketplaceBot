"""
Facebook Bot Service - Main Automation for Facebook Marketplace
This service handles Facebook login, navigation, and marketplace operations
"""

import time
import random
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import json

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementNotInteractableException, WebDriverException
)

from utils.browser_utils import BrowserManager
from utils.logger import get_logger, log_facebook_action, log_performance
from models.account import Account
from models.product import Product
from models.message import Message
from config import Config


class FacebookBot:
    """
    Main Facebook automation service for marketplace operations

    Features:
    - Facebook login with anti-detection
    - Session management and persistence
    - Marketplace navigation
    - CAPTCHA detection and handling
    - Error recovery and retry logic
    - Activity monitoring and rate limiting
    """

    def __init__(self, account: Account, headless: bool = None):
        """
        Initialize FacebookBot for a specific account

        Args:
            account: Account object with Facebook credentials
            headless: Run browser in headless mode (None = use config)
        """
        self.account = account
        self.logger = get_logger(f"facebook_bot_{account.get_masked_email()}")

        # Browser management
        self.browser: Optional[BrowserManager] = None
        self.headless = headless if headless is not None else not Config.DEBUG_MODE

        # Session state
        self.is_logged_in = False
        self.current_url = ""
        self.last_activity = None
        self.session_start_time = None

        # Activity tracking for rate limiting
        self.action_count = 0
        self.hourly_actions = []
        self.daily_actions = []

        # Error tracking
        self.consecutive_errors = 0
        self.last_error_time = None

        # Facebook element selectors (updated for current Facebook)
        self.selectors = {
            'login': {
                'email': 'input[name="email"]',
                'password': 'input[name="pass"]',
                'login_button': 'button[name="login"]',
                'login_button_alt': 'input[type="submit"]'
            },
            'navigation': {
                'marketplace_link': 'a[href*="marketplace"]',
                'marketplace_menu': '[aria-label="Marketplace"]',
                'create_listing': 'a[href*="marketplace/create"]',
                'messages': 'a[href*="messages"]'
            },
            'security': {
                'captcha': '[data-testid="captcha"]',
                'security_check': 'form[method="post"]',
                'checkpoint': '[data-testid="checkpoint"]',
                'save_device': 'input[name="save_device"]'
            },
            'marketplace': {
                'create_button': '[data-testid="marketplace-cta-button"]',
                'category_dropdown': 'select[aria-label*="Category"]',
                'title_input': 'input[aria-label*="Title"]',
                'description_textarea': 'textarea[aria-label*="Description"]',
                'price_input': 'input[aria-label*="Price"]',
                'location_input': 'input[aria-label*="Location"]'
            }
        }

        self.logger.info(f"FacebookBot initialized for {account.get_masked_email()}")

    def start_session(self) -> bool:
        """
        Start a new Facebook session

        Returns:
            True if session started successfully, False otherwise
        """
        try:
            start_time = time.time()
            self.logger.info("Starting Facebook session...")

            # Initialize browser
            if not self._setup_browser():
                return False

            # Navigate to Facebook
            if not self._navigate_to_facebook():
                return False

            # Perform login
            if not self._perform_login():
                return False

            # Verify login success
            if not self._verify_login():
                return False

            # Session setup complete
            self.session_start_time = datetime.now()
            self.last_activity = datetime.now()
            session_time = time.time() - start_time

            log_performance(f"facebook_session_start_{self.account.get_masked_email()}", session_time)
            log_facebook_action("session_start", self.account.get_masked_email(), True,
                               f"Session started in {session_time:.2f}s")

            self.logger.info(f"Facebook session started successfully in {session_time:.2f}s")
            return True

        except Exception as e:
            log_facebook_action("session_start", self.account.get_masked_email(), False, str(e))
            self.logger.error(f"Failed to start Facebook session: {e}")
            return False

    def _setup_browser(self) -> bool:
        """Set up browser manager"""
        try:
            # Create browser with account-specific profile
            clean_email = self.account.email.replace('@', '_at_').replace('.', '_dot_')
            clean_email = ''.join(c for c in clean_email if c.isalnum() or c in ['_', '-'])
            profile_name = f"fb_{clean_email}"

            self.browser = BrowserManager(
                headless=self.headless,
                user_data_dir=str(Config.DRIVERS_DIR / "profiles")
            )

            if not self.browser.setup_driver(profile_name):
                self.logger.error("Failed to setup browser driver")
                return False

            self.logger.info("Browser setup completed")
            return True

        except Exception as e:
            self.logger.error(f"Browser setup error: {e}")
            return False

    def _navigate_to_facebook(self) -> bool:
        """Navigate to Facebook login page"""
        try:
            self.logger.info("Navigating to Facebook...")

            if not self.browser.navigate_to(Config.FB_LOGIN_URL):
                self.logger.error("Failed to navigate to Facebook")
                return False

            # Wait for page to load and check for login form
            self._wait_for_page_stability()

            # Check if already logged in
            if self._check_if_already_logged_in():
                self.logger.info("Already logged in to Facebook")
                self.is_logged_in = True
                return True

            # Verify we're on the login page
            email_field = self.browser.find_element_safe(By.CSS_SELECTOR, self.selectors['login']['email'], timeout=10)
            if not email_field:
                self.logger.error("Login form not found - may be blocked or different page layout")
                if Config.SCREENSHOT_ON_ERROR:
                    self.browser.take_screenshot("login_form_not_found")
                return False

            self.logger.info("Successfully navigated to Facebook login page")
            return True

        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            return False

    def _check_if_already_logged_in(self) -> bool:
        """Check if already logged in by looking for user-specific elements"""
        try:
            # Look for elements that indicate we're logged in
            login_indicators = [
                '[data-testid="user_menu"]',
                '[aria-label="Account"]',
                'a[href*="/me"]',
                '[data-testid="left_nav_menu_item"]'
            ]

            for selector in login_indicators:
                element = self.browser.find_element_safe(By.CSS_SELECTOR, selector, timeout=3)
                if element:
                    self.logger.info("Found login indicator - already logged in")
                    return True

            return False

        except Exception as e:
            self.logger.debug(f"Login check error (normal if not logged in): {e}")
            return False

    def _perform_login(self) -> bool:
        """Perform Facebook login process"""
        if self.is_logged_in:
            return True

        try:
            self.logger.info("Starting login process...")

            # Find login form elements
            email_field = self.browser.find_element_safe(By.CSS_SELECTOR, self.selectors['login']['email'])
            password_field = self.browser.find_element_safe(By.CSS_SELECTOR, self.selectors['login']['password'])

            if not email_field or not password_field:
                self.logger.error("Login form elements not found")
                return False

            # Clear and enter email
            self.logger.info("Entering email...")
            if not self.browser.type_text_human(email_field, self.account.email, clear_first=True):
                self.logger.error("Failed to enter email")
                return False

            # Random delay between email and password
            self.browser.human_delay(1, 3)

            # Enter password
            self.logger.info("Entering password...")
            if not self.browser.type_text_human(password_field, self.account.password, clear_first=True):
                self.logger.error("Failed to enter password")
                return False

            # Random delay before clicking login
            self.browser.human_delay(1, 2)

            # Find and click login button
            login_button = self.browser.find_element_safe(By.CSS_SELECTOR, self.selectors['login']['login_button'])
            if not login_button:
                # Try alternative selector
                login_button = self.browser.find_element_safe(By.CSS_SELECTOR, self.selectors['login']['login_button_alt'])

            if not login_button:
                self.logger.error("Login button not found")
                return False

            self.logger.info("Clicking login button...")
            if not self.browser.click_element_safe(login_button):
                self.logger.error("Failed to click login button")
                return False

            # Wait for login to process
            self._wait_for_login_completion()

            return True

        except Exception as e:
            self.logger.error(f"Login process error: {e}")
            return False

    def _wait_for_login_completion(self) -> bool:
        """Wait for login process to complete and handle potential security checks"""
        try:
            self.logger.info("Waiting for login completion...")

            # Wait for page to change after login attempt
            time.sleep(3)

            # Check for various post-login scenarios
            max_wait_time = 30
            start_time = time.time()

            while time.time() - start_time < max_wait_time:
                current_url = self.browser.driver.current_url

                # Check if we're successfully logged in
                if self._check_if_already_logged_in():
                    self.logger.info("Login successful - user logged in")
                    return True

                # Check for security challenges
                if self._handle_security_challenges():
                    continue

                # Check for login errors
                if self._check_for_login_errors():
                    return False

                # Still on login page - wait a bit more
                time.sleep(2)

            self.logger.warning("Login completion timeout reached")
            return False

        except Exception as e:
            self.logger.error(f"Login completion wait error: {e}")
            return False

    def _handle_security_challenges(self) -> bool:
        """Handle Facebook security challenges (CAPTCHA, checkpoint, etc.)"""
        try:
            # Check for CAPTCHA
            captcha = self.browser.find_element_safe(By.CSS_SELECTOR, self.selectors['security']['captcha'], timeout=2)
            if captcha:
                self.logger.warning("CAPTCHA detected - manual intervention required")
                log_facebook_action("captcha_detected", self.account.get_masked_email(), False, "Manual intervention needed")

                if Config.SCREENSHOT_ON_ERROR:
                    self.browser.take_screenshot("captcha_detected")

                # Wait for manual resolution if not headless
                if not self.headless:
                    self.logger.info("Please solve the CAPTCHA manually...")
                    input("Press Enter after solving CAPTCHA...")
                    return True
                else:
                    return False

            # Check for checkpoint/security verification
            checkpoint = self.browser.find_element_safe(By.CSS_SELECTOR, self.selectors['security']['checkpoint'], timeout=2)
            if checkpoint:
                self.logger.warning("Facebook checkpoint detected")
                log_facebook_action("checkpoint_detected", self.account.get_masked_email(), False, "Account flagged for review")

                if Config.SCREENSHOT_ON_ERROR:
                    self.browser.take_screenshot("checkpoint_detected")

                return False

            # Check for "Save Device" option
            save_device = self.browser.find_element_safe(By.CSS_SELECTOR, self.selectors['security']['save_device'], timeout=2)
            if save_device:
                self.logger.info("Save device prompt found - clicking to save session")
                self.browser.click_element_safe(save_device)
                time.sleep(2)
                return True

            return False

        except Exception as e:
            self.logger.error(f"Security challenge handling error: {e}")
            return False

    def _check_for_login_errors(self) -> bool:
        """Check for login error messages"""
        try:
            error_selectors = [
                '[data-testid="royal_login_form"] div[role="alert"]',
                '[data-testid="login_error"]',
                'div[aria-live="polite"]'
            ]

            for selector in error_selectors:
                error_element = self.browser.find_element_safe(By.CSS_SELECTOR, selector, timeout=1)
                if error_element:
                    error_text = error_element.text
                    self.logger.error(f"Login error detected: {error_text}")
                    log_facebook_action("login_error", self.account.get_masked_email(), False, error_text)

                    if Config.SCREENSHOT_ON_ERROR:
                        self.browser.take_screenshot("login_error")

                    return True

            return False

        except Exception as e:
            self.logger.debug(f"Login error check failed: {e}")
            return False

    def _verify_login(self) -> bool:
        """Verify that login was successful"""
        try:
            # Final verification that we're logged in
            if self._check_if_already_logged_in():
                self.is_logged_in = True
                self.account.update_login_stats()

                # Take success screenshot
                if Config.TAKE_SCREENSHOTS:
                    self.browser.take_screenshot("login_success")

                self.logger.info("Login verification successful")
                return True
            else:
                self.logger.error("Login verification failed - not logged in")
                return False

        except Exception as e:
            self.logger.error(f"Login verification error: {e}")
            return False

    def navigate_to_marketplace(self) -> bool:
        """Navigate to Facebook Marketplace"""
        if not self._ensure_logged_in():
            return False

        try:
            self.logger.info("Navigating to Facebook Marketplace...")

            # Try direct navigation first
            if self.browser.navigate_to(Config.FB_MARKETPLACE_URL):
                self._wait_for_page_stability()

                # Verify we're on marketplace
                if "marketplace" in self.browser.driver.current_url.lower():
                    self.logger.info("Successfully navigated to Marketplace")
                    self._update_activity()
                    return True

            # If direct navigation failed, try clicking marketplace link
            marketplace_selectors = [
                self.selectors['navigation']['marketplace_link'],
                self.selectors['navigation']['marketplace_menu'],
                'a[href="/marketplace/"]',
                '[data-testid="left_nav_marketplace"]'
            ]

            for selector in marketplace_selectors:
                marketplace_link = self.browser.find_element_safe(By.CSS_SELECTOR, selector, timeout=5)
                if marketplace_link:
                    self.logger.info(f"Found marketplace link with selector: {selector}")
                    if self.browser.click_element_safe(marketplace_link):
                        self._wait_for_page_stability()

                        if "marketplace" in self.browser.driver.current_url.lower():
                            self.logger.info("Successfully navigated to Marketplace via link")
                            self._update_activity()
                            return True
                        break

            self.logger.error("Failed to navigate to Marketplace")
            return False

        except Exception as e:
            self.logger.error(f"Marketplace navigation error: {e}")
            log_facebook_action("marketplace_navigation", self.account.get_masked_email(), False, str(e))
            return False

    def navigate_to_messages(self) -> bool:
        """Navigate to Facebook Messages"""
        if not self._ensure_logged_in():
            return False

        try:
            self.logger.info("Navigating to Facebook Messages...")

            # Try direct navigation
            if self.browser.navigate_to(Config.FB_MESSENGER_URL):
                self._wait_for_page_stability()

                if "messages" in self.browser.driver.current_url.lower():
                    self.logger.info("Successfully navigated to Messages")
                    self._update_activity()
                    return True

            self.logger.error("Failed to navigate to Messages")
            return False

        except Exception as e:
            self.logger.error(f"Messages navigation error: {e}")
            return False

    def _ensure_logged_in(self) -> bool:
        """Ensure we're still logged in, re-login if necessary"""
        if not self.is_logged_in:
            self.logger.warning("Not logged in - attempting to log in")
            return self.start_session()

        # Check if session is still valid
        if not self._check_if_already_logged_in():
            self.logger.warning("Session expired - attempting to re-login")
            self.is_logged_in = False
            return self.start_session()

        return True

    def _wait_for_page_stability(self, timeout: int = 10):
        """Wait for page to be stable and fully loaded"""
        try:
            # Wait for document ready state
            WebDriverWait(self.browser.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )

            # Additional wait for dynamic content
            time.sleep(random.uniform(2, 4))

        except TimeoutException:
            self.logger.warning("Page stability timeout")

    def _update_activity(self):
        """Update last activity timestamp and action count"""
        self.last_activity = datetime.now()
        self.action_count += 1

        # Track hourly and daily actions for rate limiting
        now = datetime.now()
        self.hourly_actions.append(now)
        self.daily_actions.append(now)

        # Clean old entries
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)

        self.hourly_actions = [action for action in self.hourly_actions if action > one_hour_ago]
        self.daily_actions = [action for action in self.daily_actions if action > one_day_ago]

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            'account': self.account.get_masked_email(),
            'is_logged_in': self.is_logged_in,
            'current_url': self.browser.driver.current_url if self.browser and self.browser.driver else "",
            'session_duration': (datetime.now() - self.session_start_time).total_seconds() if self.session_start_time else 0,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'action_count': self.action_count,
            'hourly_actions': len(self.hourly_actions),
            'daily_actions': len(self.daily_actions),
            'consecutive_errors': self.consecutive_errors
        }

    def check_rate_limits(self) -> bool:
        """Check if we're within rate limits"""
        if len(self.hourly_actions) >= Config.MAX_ACTIONS_PER_HOUR:
            self.logger.warning(f"Hourly rate limit reached: {len(self.hourly_actions)}/{Config.MAX_ACTIONS_PER_HOUR}")
            return False

        if len(self.daily_actions) >= Config.MAX_ACTIONS_PER_HOUR * 12:  # Reasonable daily limit
            self.logger.warning(f"Daily rate limit reached: {len(self.daily_actions)}")
            return False

        return True

    def end_session(self):
        """End the Facebook session and cleanup"""
        try:
            if self.browser:
                # Take final screenshot if enabled
                if Config.TAKE_SCREENSHOTS and self.is_logged_in:
                    self.browser.take_screenshot("session_end")

                # Cleanup browser
                self.browser.cleanup()
                self.browser = None

            # Log session info
            session_info = self.get_session_info()
            self.logger.info(f"Session ended: {session_info}")

            log_facebook_action("session_end", self.account.get_masked_email(), True,
                               f"Actions: {self.action_count}, Duration: {session_info.get('session_duration', 0):.2f}s")

            # Reset state
            self.is_logged_in = False
            self.current_url = ""
            self.session_start_time = None

            self.logger.info("Facebook session ended successfully")

        except Exception as e:
            self.logger.error(f"Session cleanup error: {e}")

    def __enter__(self):
        """Context manager entry"""
        if self.start_session():
            return self
        else:
            raise Exception("Failed to start Facebook session")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.end_session()


# Convenience functions for easy usage
def create_facebook_bot(account: Account, headless: bool = None) -> FacebookBot:
    """
    Create and initialize a Facebook bot for an account

    Args:
        account: Account object with Facebook credentials
        headless: Run in headless mode

    Returns:
        Configured FacebookBot instance
    """
    return FacebookBot(account, headless)


def test_facebook_login(account: Account, headless: bool = False) -> bool:
    """
    Test Facebook login for an account

    Args:
        account: Account to test login for
        headless: Run in headless mode

    Returns:
        True if login successful, False otherwise
    """
    try:
        with create_facebook_bot(account, headless) as bot:
            return bot.navigate_to_marketplace()
    except Exception as e:
        logger = get_logger("facebook_login_test")
        logger.error(f"Login test failed for {account.get_masked_email()}: {e}")
        return False


# Example usage and testing
if __name__ == "__main__":
    from utils.logger import setup_logging
    from services.excel_handler import ExcelHandler

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    logger.info("Testing FacebookBot...")

    try:
        # Load test account
        excel_handler = ExcelHandler()
        accounts = excel_handler.load_accounts("data/sample_accounts.xlsx")

        if not accounts:
            logger.error("No accounts found for testing")
            exit(1)

        test_account = accounts[0]  # Use first account
        logger.info(f"Testing with account: {test_account.get_masked_email()}")

        # Create bot instance
        bot = FacebookBot(test_account, headless=False)  # Non-headless for testing

        logger.info("FacebookBot instance created successfully")
        logger.info("To test login, run with a real Facebook account")
        logger.info("Example usage:")
        logger.info("  with create_facebook_bot(account) as bot:")
        logger.info("    bot.navigate_to_marketplace()")

    except Exception as e:
        logger.error(f"FacebookBot test error: {e}")