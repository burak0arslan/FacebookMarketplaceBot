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
from selenium.webdriver.support.ui import Select
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
from typing import Optional, Callable
from services.message_monitor import MessageMonitor, AsyncMessageMonitor
from models.message import Message

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

        # Additional compatibility attributes
        self.logged_in = False  # Alternative name for is_logged_in

        # Marketplace listing statistics
        self.listings_created = 0
        self.listings_failed = 0

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

    def create_marketplace_listing(self, product: Product) -> bool:
        """Create a marketplace listing"""
        if not self.logged_in or not self.current_account:
            self.logger.error("Must be logged in to create listings")
            return False

        from services.marketplace_listing import MarketplaceListing
        listing_service = MarketplaceListing(self.browser, self.current_account)
        return listing_service.create_listing(product)

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
            self.is_logged_in = True
            return self.start_session()

        return True

    def start_message_monitoring(self, check_interval: int = None) -> bool:
        """
        Start message monitoring for this bot's account

        Args:
            check_interval: Seconds between message checks (uses config default if None)

        Returns:
            True if monitoring started successfully
        """
        try:
            if not self.is_logged_in:
                self.logger.error("Must be logged in to monitor messages")
                return False

            self.logger.info("Starting message monitoring...")

            # Create message monitor
            self.message_monitor = MessageMonitor(self.browser, self.account)

            # Start monitoring
            if self.message_monitor.start_monitoring(check_interval):
                self.logger.info("✅ Message monitoring started successfully")
                return True
            else:
                self.logger.error("Failed to start message monitoring")
                return False

        except Exception as e:
            self.logger.error(f"Failed to start message monitoring: {e}")
            return False

    def stop_message_monitoring(self):
        """Stop message monitoring"""
        try:
            if hasattr(self, 'message_monitor') and self.message_monitor:
                self.message_monitor.stop_monitoring()
                self.message_monitor = None
                self.logger.info("Message monitoring stopped")
            else:
                self.logger.warning("Message monitoring was not running")
        except Exception as e:
            self.logger.error(f"Error stopping message monitoring: {e}")

    def process_new_messages(self, processor_callback: Callable[[Message], bool] = None) -> dict:
        """
        Process new messages in one cycle

        Args:
            processor_callback: Function to process each message

        Returns:
            Dictionary with processing statistics
        """
        if not hasattr(self, 'message_monitor') or not self.message_monitor:
            self.logger.warning("Message monitoring not started")
            return {'error': 'Message monitoring not started'}

        try:
            # Run one monitoring cycle
            stats = self.message_monitor.run_monitoring_cycle(processor_callback)

            if stats.get('new_messages', 0) > 0:
                self.logger.info(f"Processed {stats['new_messages']} new messages")

            return stats

        except Exception as e:
            self.logger.error(f"Error processing messages: {e}")
            return {'error': str(e)}

    def start_ai_powered_monitoring(self, products: List[Product] = None) -> bool:
        """
        Start AI-powered message monitoring

        Args:
            products: List of products for AI context

        Returns:
            True if started successfully
        """
        try:
            if not self.is_logged_in:
                self.logger.error("Must be logged in to start AI monitoring")
                return False

            from services.llama_ai import create_llama_ai
            from services.ai_message_processor import AIMessageProcessor

            self.logger.info("Starting AI-powered message monitoring...")

            # Create AI service
            ai_service = create_llama_ai()
            self.logger.info("✅ AI service connected")

            # Create AI processor
            self.ai_processor = AIMessageProcessor(ai_service, products or [])
            self.logger.info(f"✅ AI processor created with {len(products or [])} products")

            # Start message monitoring
            if self.start_message_monitoring():
                self.logger.info("✅ AI-powered monitoring started successfully")
                return True
            else:
                self.logger.error("Failed to start message monitoring")
                return False

        except Exception as e:
            self.logger.error(f"Failed to start AI monitoring: {e}")
            return False

    def process_messages_with_ai(self) -> dict:
        """
        Process messages using AI intelligence

        Returns:
            Processing statistics with AI insights
        """
        try:
            if not hasattr(self, 'ai_processor'):
                self.logger.error("AI processor not initialized - call start_ai_powered_monitoring() first")
                return {'error': 'AI processor not initialized'}

            # Create AI-powered processor function
            def ai_processor_function(message) -> bool:  # Note: removed Message type hint for compatibility
                try:
                    result = self.ai_processor.process_message(message)
                    success = result.get('processed', False)

                    # Log AI processing results
                    if result.get('response_generated'):
                        self.logger.info(f"🤖 AI Response: {result['response_generated'][:50]}...")

                    if result.get('escalated'):
                        self.logger.warning(f"⚠️ Message escalated: {message.get_short_content()}")

                    return success

                except Exception as e:
                    self.logger.error(f"AI processing error: {e}")
                    return False

            # Process messages with AI
            monitoring_stats = self.process_new_messages(ai_processor_function)

            # Get AI statistics
            ai_stats = self.ai_processor.get_statistics()

            # Combined results
            results = {
                'monitoring_stats': monitoring_stats,
                'ai_stats': ai_stats,
                'timestamp': datetime.now().isoformat()
            }

            # Log summary
            if monitoring_stats.get('new_messages', 0) > 0:
                self.logger.info(f"🤖 Processed {monitoring_stats.get('new_messages', 0)} messages with AI")
                self.logger.info(f"📊 AI responses sent: {ai_stats.get('ai_responses_sent', 0)}")
                self.logger.info(f"⚠️ Escalations: {ai_stats.get('escalations', 0)}")

            return results

        except Exception as e:
            self.logger.error(f"AI message processing error: {e}")
            return {'error': str(e)}


    def get_message_stats(self) -> dict:
        """Get message monitoring statistics"""
        if not hasattr(self, 'message_monitor') or not self.message_monitor:
            return {'monitoring': False, 'error': 'Message monitoring not started'}

        try:
            stats = self.message_monitor.get_monitoring_stats()
            return stats
        except Exception as e:
            self.logger.error(f"Error getting message stats: {e}")
            return {'error': str(e)}

    def create_message_processor(self) -> Callable[[Message], bool]:
        """
        Create a default message processor for this bot

        Returns:
            Message processor function
        """

        def default_processor(message: Message) -> bool:
            try:
                self.logger.info(f"Processing message from {message.sender_name}")
                self.logger.info(f"Content: {message.get_short_content()}")

                # Log message details
                self.logger.info(f"  Priority: {message.get_priority_score()}")
                self.logger.info(f"  Contains question: {message.contains_question}")
                self.logger.info(f"  Price inquiry: {message.contains_price_inquiry}")
                self.logger.info(f"  Requires human attention: {message.requires_human_attention}")

                # Handle escalation
                if message.requires_human_attention:
                    self.logger.warning("⚠️ Message requires human attention - escalating")
                    message.mark_as_escalated()

                    # You can add notification logic here
                    # self.notify_human_operator(message)

                    return True

                # Handle questions (Phase 5 will add AI responses here)
                if message.contains_question:
                    self.logger.info("❓ Message contains question - ready for AI response")

                    # Phase 5 integration point:
                    # response = self.generate_ai_response(message)
                    # if response:
                    #     self.send_response(message.conversation_id, response)
                    #     message.mark_as_processed()
                    #     return True

                # For now, just mark as processed
                message.mark_as_processed()
                self.logger.info("✅ Message processed successfully")

                return True

            except Exception as e:
                self.logger.error(f"Error in message processor: {e}")
                message.mark_as_error(str(e))
                return False

        return default_processor

    def start_continuous_monitoring(self, check_interval: int = None,
                                    processor_callback: Callable[[Message], bool] = None):
        """
        Start continuous message monitoring (async)

        Args:
            check_interval: Seconds between checks
            processor_callback: Function to process messages

        Returns:
            AsyncMessageMonitor instance
        """
        try:
            if not hasattr(self, 'message_monitor') or not self.message_monitor:
                if not self.start_message_monitoring(check_interval):
                    return None

            # Create async monitor
            self.async_monitor = AsyncMessageMonitor(self.message_monitor)

            # Use default processor if none provided
            if not processor_callback:
                processor_callback = self.create_message_processor()

            self.logger.info("Starting continuous message monitoring...")
            return self.async_monitor

        except Exception as e:
            self.logger.error(f"Failed to start continuous monitoring: {e}")
            return None

    def stop_continuous_monitoring(self):
        """Stop continuous message monitoring"""
        try:
            if hasattr(self, 'async_monitor') and self.async_monitor:
                self.async_monitor.stop_continuous_monitoring()
                self.async_monitor = None
                self.logger.info("Continuous monitoring stopped")

            self.stop_message_monitoring()

        except Exception as e:
            self.logger.error(f"Error stopping continuous monitoring: {e}")

    # Update the end_session method to include cleanup:
    def end_session(self):
        """End the Facebook session and cleanup (UPDATE EXISTING METHOD)"""
        try:
            # Stop message monitoring if running
            if hasattr(self, 'message_monitor') and self.message_monitor:
                self.stop_message_monitoring()

            if hasattr(self, 'async_monitor') and self.async_monitor:
                self.stop_continuous_monitoring()

            # ... rest of existing end_session code ...

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

    # Example usage:
    """
    # Basic message monitoring
    bot = FacebookBot(account)
    if bot.start_session():
        # Start monitoring
        if bot.start_message_monitoring(check_interval=30):
            # Process messages manually
            stats = bot.process_new_messages()
            print(f"Processed {stats.get('new_messages', 0)} messages")

            # Stop monitoring
            bot.stop_message_monitoring()

    # Continuous monitoring
    bot = FacebookBot(account)
    if bot.start_session():
        # Start continuous monitoring
        async_monitor = bot.start_continuous_monitoring(check_interval=30)

        if async_monitor:
            # This will run continuously until stopped
            import asyncio

            async def run_monitoring():
                await async_monitor.start_continuous_monitoring(
                    check_interval=30,
                    processor_callback=bot.create_message_processor()
                )

            # Run for 5 minutes then stop
            async def stop_after_delay():
                await asyncio.sleep(300)  # 5 minutes
                bot.stop_continuous_monitoring()

            # Run both tasks
            asyncio.run(asyncio.gather(
                run_monitoring(),
                stop_after_delay()
            ))

    # Custom message processor
    def custom_processor(message):
        print(f"Custom processing: {message.sender_name}")

        if "urgent" in message.content.lower():
            print("URGENT MESSAGE!")
            message.mark_as_escalated()
            return True

        message.mark_as_processed()
        return True

    # Use custom processor
    bot.start_message_monitoring()
    bot.process_new_messages(custom_processor)
    """

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

    """
    FacebookBot Marketplace Listing Extension
    Add these methods to your existing services/facebook_bot.py file
    """

    import time
    import random
    from pathlib import Path
    from typing import List, Optional, Dict, Any

    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException,
        ElementNotInteractableException
    )

    from models.product import Product
    from utils.logger import log_facebook_action

    class FacebookBotMarketplaceExtension:
        """
        Extension methods for FacebookBot to handle marketplace listing

        Add these methods to your existing FacebookBot class in services/facebook_bot.py
        """

        def navigate_to_marketplace(self) -> bool:
            """
            Navigate to Facebook Marketplace

            Returns:
                True if successful, False otherwise
            """
            try:
                self.logger.info("🏪 Navigating to Facebook Marketplace...")

                marketplace_url = "https://www.facebook.com/marketplace"

                if not self.browser.navigate_to(marketplace_url):
                    return False

                # Wait for marketplace to load
                wait = WebDriverWait(self.browser.driver, 10)

                # Look for marketplace indicators
                marketplace_indicators = [
                    "//h1[contains(text(), 'Marketplace')]",
                    "//div[@aria-label='Marketplace']",
                    "//*[contains(text(), 'Browse all')]",
                    "//div[contains(@class, 'marketplace')]"
                ]

                for indicator in marketplace_indicators:
                    try:
                        element = wait.until(EC.presence_of_element_located((By.XPATH, indicator)))
                        if element:
                            self.logger.info("✅ Marketplace loaded successfully")
                            time.sleep(random.uniform(2, 4))
                            return True
                    except TimeoutException:
                        continue

                self.logger.warning("⚠️ Marketplace page loaded but indicators not found")
                return True  # Assume success if page loaded

            except Exception as e:
                self.logger.error(f"❌ Error navigating to marketplace: {e}")
                return False

        def navigate_to_create_listing(self) -> bool:
            """
            Navigate to create new listing page

            Returns:
                True if successful, False otherwise
            """
            try:
                self.logger.info("➕ Navigating to create listing page...")

                # Try direct URL first
                create_url = "https://www.facebook.com/marketplace/create"
                if self.browser.navigate_to(create_url):
                    time.sleep(random.uniform(3, 5))
                    return True

                # Fallback: look for create button
                create_selectors = [
                    "//div[@role='button'][contains(text(), 'Create new listing')]",
                    "//a[contains(@href, '/marketplace/create')]",
                    "//button[contains(text(), 'Sell something')]",
                    "//*[@aria-label='Create new listing']"
                ]

                for selector in create_selectors:
                    try:
                        button = self.browser.find_element_safe(By.XPATH, selector, timeout=5)
                        if button and button.is_displayed():
                            self.browser.click_element_safe(button)
                            time.sleep(random.uniform(2, 4))
                            self.logger.info("✅ Clicked create listing button")
                            return True
                    except Exception:
                        continue

                self.logger.error("❌ Could not find create listing button")
                return False

            except Exception as e:
                self.logger.error(f"❌ Error navigating to create listing: {e}")
                return False

        def select_listing_type(self, listing_type: str = "item") -> bool:
            """
            Select listing type (Item for Sale, Vehicle, etc.)

            Args:
                listing_type: Type of listing ("item", "vehicle", "home")

            Returns:
                True if successful, False otherwise
            """
            try:
                self.logger.info(f"📝 Selecting listing type: {listing_type}")

                # Wait for listing type options to appear
                wait = WebDriverWait(self.browser.driver, 10)

                type_selectors = {
                    "item": [
                        "//div[@role='radio'][contains(text(), 'Item for sale')]",
                        "//input[@value='ITEM']/../..",
                        "//*[contains(text(), 'Item for sale')]"
                    ],
                    "vehicle": [
                        "//div[@role='radio'][contains(text(), 'Vehicle')]",
                        "//input[@value='VEHICLE']/../..",
                        "//*[contains(text(), 'Vehicle')]"
                    ],
                    "home": [
                        "//div[@role='radio'][contains(text(), 'Home for sale')]",
                        "//input[@value='HOME']/../..",
                        "//*[contains(text(), 'Home for sale')]"
                    ]
                }

                selectors = type_selectors.get(listing_type, type_selectors["item"])

                for selector in selectors:
                    try:
                        option = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        if option:
                            self.browser.click_element_safe(option)
                            time.sleep(random.uniform(1, 2))
                            self.logger.info(f"✅ Selected {listing_type} listing type")
                            return True
                    except TimeoutException:
                        continue
                    except Exception as e:
                        self.logger.debug(f"Selector failed: {selector} - {e}")
                        continue

                self.logger.error(f"❌ Could not select {listing_type} listing type")
                return False

            except Exception as e:
                self.logger.error(f"❌ Error selecting listing type: {e}")
                return False

        def fill_listing_form(self, product: Product) -> bool:
            """
            Fill out the marketplace listing form

            Args:
                product: Product object with listing details

            Returns:
                True if successful, False otherwise
            """
            try:
                self.logger.info(f"📝 Filling listing form for: {product.title}")

                # Wait for form to load
                time.sleep(random.uniform(2, 4))

                # Fill title
                if not self._fill_form_field("title", product.title, required=True):
                    return False

                # Fill description
                if not self._fill_form_field("description", product.description, required=True):
                    return False

                # Fill price
                price_str = f"{product.price:.0f}" if product.price == int(product.price) else f"{product.price:.2f}"
                if not self._fill_form_field("price", price_str, required=True):
                    return False

                # Fill location (optional)
                if product.location:
                    self._fill_form_field("location", product.location, required=False)

                # Select category (optional)
                if product.category:
                    self._select_category(product.category)

                # Select condition (optional)
                if product.condition:
                    self._select_condition(product.condition)

                self.logger.info("✅ Form filled successfully")
                return True

            except Exception as e:
                self.logger.error(f"❌ Error filling listing form: {e}")
                return False

        def _fill_form_field(self, field_type: str, value: str, required: bool = True) -> bool:
            """
            Fill a specific form field with multiple selector fallbacks

            Args:
                field_type: Type of field (title, description, price, location)
                value: Value to enter
                required: Whether field is required

            Returns:
                True if successful, False if required field fails
            """
            try:
                # Field selector mappings
                field_selectors = {
                    "title": [
                        "//input[@placeholder='What are you selling?']",
                        "//input[@aria-label*='title']",
                        "//textarea[@placeholder='What are you selling?']"
                    ],
                    "description": [
                        "//textarea[@placeholder='Describe your item']",
                        "//textarea[@aria-label*='description']",
                        "//div[@contenteditable='true'][@aria-label*='description']"
                    ],
                    "price": [
                        "//input[@placeholder='Price']",
                        "//input[@aria-label*='price']",
                        "//input[@placeholder*='$']"
                    ],
                    "location": [
                        "//input[@placeholder*='Location']",
                        "//input[@placeholder*='Neighborhood']",
                        "//input[@aria-label*='location']"
                    ]
                }

                selectors = field_selectors.get(field_type, [])

                for selector in selectors:
                    try:
                        field = self.browser.find_element_safe(By.XPATH, selector, timeout=3)
                        if field and field.is_displayed():
                            # Clear field
                            field.clear()
                            time.sleep(0.5)

                            # Type value with human-like typing
                            if self.browser.type_text_human(field, value):
                                self.logger.debug(f"✅ Filled {field_type}: {value[:30]}...")
                                return True
                    except Exception as e:
                        self.logger.debug(f"Selector failed for {field_type}: {selector}")
                        continue

                # Field not found
                if required:
                    self.logger.error(f"❌ Required field '{field_type}' not found")
                    return False
                else:
                    self.logger.warning(f"⚠️ Optional field '{field_type}' not found")
                    return True

            except Exception as e:
                self.logger.error(f"❌ Error filling {field_type} field: {e}")
                return False if required else True

        def _select_category(self, category: str) -> bool:
            """Select product category"""
            try:
                self.logger.debug(f"🏷️ Selecting category: {category}")

                # Look for category dropdown/selector
                category_selectors = [
                    "//select[@aria-label*='Category']",
                    "//div[@role='button'][@aria-label*='category']",
                    "//*[contains(text(), 'Category')]/..//select"
                ]

                for selector in category_selectors:
                    try:
                        element = self.browser.find_element_safe(By.XPATH, selector, timeout=2)
                        if element:
                            if element.tag_name == 'select':
                                # Handle select dropdown
                                select = Select(element)
                                for option in select.options:
                                    if category.lower() in option.text.lower():
                                        select.select_by_visible_text(option.text)
                                        self.logger.debug(f"✅ Selected category: {option.text}")
                                        return True
                            else:
                                # Handle div/button dropdown
                                self.browser.click_element_safe(element)
                                time.sleep(1)

                                # Look for category option
                                option_xpath = f"//*[contains(text(), '{category}')]"
                                option = self.browser.find_element_safe(By.XPATH, option_xpath, timeout=2)
                                if option:
                                    self.browser.click_element_safe(option)
                                    self.logger.debug(f"✅ Selected category: {category}")
                                    return True
                    except Exception:
                        continue

                self.logger.warning(f"⚠️ Could not select category: {category}")
                return True  # Not critical

            except Exception as e:
                self.logger.warning(f"⚠️ Category selection error: {e}")
                return True  # Not critical

        def _select_condition(self, condition: str) -> bool:
            """Select product condition"""
            try:
                self.logger.debug(f"🔧 Selecting condition: {condition}")

                # Map conditions to Facebook options
                condition_mapping = {
                    "new": ["New", "Brand new"],
                    "like new": ["Like new", "Excellent"],
                    "good": ["Good", "Very good"],
                    "fair": ["Fair", "Acceptable"],
                    "used": ["Used", "Good"]
                }

                # Get possible condition values
                possible_conditions = condition_mapping.get(condition.lower(), [condition])

                condition_selectors = [
                    "//select[@aria-label*='Condition']",
                    "//div[@role='button'][@aria-label*='condition']",
                    "//*[contains(text(), 'Condition')]/..//select"
                ]

                for selector in condition_selectors:
                    try:
                        element = self.browser.find_element_safe(By.XPATH, selector, timeout=2)
                        if element:
                            if element.tag_name == 'select':
                                select = Select(element)
                                for possible_condition in possible_conditions:
                                    for option in select.options:
                                        if possible_condition.lower() in option.text.lower():
                                            select.select_by_visible_text(option.text)
                                            self.logger.debug(f"✅ Selected condition: {option.text}")
                                            return True
                            else:
                                # Handle div/button dropdown
                                self.browser.click_element_safe(element)
                                time.sleep(1)

                                # Look for condition option
                                for possible_condition in possible_conditions:
                                    option_xpath = f"//*[contains(text(), '{possible_condition}')]"
                                    option = self.browser.find_element_safe(By.XPATH, option_xpath, timeout=2)
                                    if option:
                                        self.browser.click_element_safe(option)
                                        self.logger.debug(f"✅ Selected condition: {possible_condition}")
                                        return True
                    except Exception:
                        continue

                self.logger.warning(f"⚠️ Could not select condition: {condition}")
                return True  # Not critical

            except Exception as e:
                self.logger.warning(f"⚠️ Condition selection error: {e}")
                return True  # Not critical

        def upload_product_images(self, product: Product) -> bool:
            """
            Upload images for the product listing

            Args:
                product: Product object with image paths

            Returns:
                True if successful, False otherwise
            """
            try:
                if not product.images:
                    self.logger.info("📷 No images to upload")
                    return True

                self.logger.info(f"📷 Uploading {len(product.images)} images...")

                # Look for file input
                image_upload_selectors = [
                    "//input[@type='file'][@accept*='image']",
                    "//input[@type='file'][@multiple]",
                    "//*[@data-testid='media_upload_input']"
                ]

                file_input = None
                for selector in image_upload_selectors:
                    try:
                        file_input = self.browser.find_element_safe(By.XPATH, selector, timeout=3)
                        if file_input:
                            break
                    except Exception:
                        continue

                if not file_input:
                    self.logger.warning("⚠️ Could not find image upload input")
                    return True  # Not critical

                # Prepare image paths
                valid_images = []
                for image_path in product.images:
                    img_path = Path(image_path)
                    if img_path.exists() and img_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                        valid_images.append(str(img_path.absolute()))
                    else:
                        self.logger.warning(f"⚠️ Invalid image path: {image_path}")

                if not valid_images:
                    self.logger.warning("⚠️ No valid images found")
                    return True

                # Upload images (Facebook supports multiple files)
                try:
                    # Join paths with newline for multiple file upload
                    all_paths = '\n'.join(valid_images)
                    file_input.send_keys(all_paths)

                    # Wait for upload to complete
                    time.sleep(random.uniform(3, 6))

                    self.logger.info(f"✅ Uploaded {len(valid_images)} images")
                    return True

                except Exception as e:
                    self.logger.error(f"❌ Error uploading images: {e}")
                    return False

            except Exception as e:
                self.logger.error(f"❌ Image upload error: {e}")
                return False

        def publish_listing(self) -> bool:
            """
            Publish the marketplace listing

            Returns:
                True if successful, False otherwise
            """
            try:
                self.logger.info("🚀 Publishing listing...")

                # Look for publish/post button
                publish_selectors = [
                    "//button[contains(text(), 'Post')]",
                    "//button[contains(text(), 'Publish')]",
                    "//div[@role='button'][contains(text(), 'Post')]",
                    "//*[@data-testid='marketplace_listing_post_button']"
                ]

                for selector in publish_selectors:
                    try:
                        button = self.browser.find_element_safe(By.XPATH, selector, timeout=5)
                        if button and button.is_enabled():
                            # Scroll to button and click
                            self.browser.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(1)

                            self.browser.click_element_safe(button)

                            # Wait for publishing to complete
                            time.sleep(random.uniform(3, 6))

                            # Check for success indicators
                            success_indicators = [
                                "//div[contains(text(), 'Your listing is now live')]",
                                "//div[contains(text(), 'Posted successfully')]",
                                "//div[contains(text(), 'Your item has been posted')]"
                            ]

                            for indicator in success_indicators:
                                try:
                                    element = self.browser.find_element_safe(By.XPATH, indicator, timeout=3)
                                    if element:
                                        self.logger.info("✅ Listing published successfully!")
                                        return True
                                except Exception:
                                    continue

                            # If no explicit success message, assume success if no error
                            self.logger.info("✅ Listing appears to be published")
                            return True

                    except Exception as e:
                        self.logger.debug(f"Publish button selector failed: {selector}")
                        continue

                self.logger.error("❌ Could not find publish button")
                return False

            except Exception as e:
                self.logger.error(f"❌ Error publishing listing: {e}")
                return False

        def create_marketplace_listing(self, product: Product) -> bool:
            """
            Complete marketplace listing creation workflow

            Args:
                product: Product object with all listing details

            Returns:
                True if listing created successfully, False otherwise
            """
            try:
                self.logger.info(f"🏪 Creating marketplace listing for: {product.title}")

                # Step 1: Navigate to marketplace
                if not self.navigate_to_marketplace():
                    log_facebook_action("navigate_marketplace", self.account.email, False, "Navigation failed")
                    return False

                # Step 2: Navigate to create listing
                if not self.navigate_to_create_listing():
                    log_facebook_action("navigate_create_listing", self.account.email, False,
                                        "Create page navigation failed")
                    return False

                # Step 3: Select listing type
                if not self.select_listing_type("item"):
                    log_facebook_action("select_listing_type", self.account.email, False,
                                        "Listing type selection failed")
                    return False

                # Step 4: Fill listing form
                if not self.fill_listing_form(product):
                    log_facebook_action("fill_listing_form", self.account.email, False, "Form filling failed")
                    return False

                # Step 5: Upload images
                if not self.upload_product_images(product):
                    log_facebook_action("upload_images", self.account.email, False, "Image upload failed")
                    return False

                # Step 6: Publish listing
                if not self.publish_listing():
                    log_facebook_action("publish_listing", self.account.email, False, "Publishing failed")
                    return False

                self.logger.info("🎉 Marketplace listing created successfully!")
                log_facebook_action("create_marketplace_listing", self.account.email, True, f"Listed: {product.title}")

                return True

            except Exception as e:
                self.logger.error(f"❌ Complete listing creation failed: {e}")
                log_facebook_action("create_marketplace_listing", self.account.email, False, f"Error: {str(e)}")
                return False

        def verify_listing_published(self, product_title: str, timeout: int = 30) -> bool:
            """
            Verify that listing was published successfully

            Args:
                product_title: Title of the product to verify
                timeout: Maximum time to wait for verification

            Returns:
                True if listing verified, False otherwise
            """
            try:
                self.logger.info(f"🔍 Verifying listing publication: {product_title}")

                # Navigate to user's listings/marketplace
                my_listings_selectors = [
                    "//a[contains(@href, '/marketplace/you/selling')]",
                    "//*[contains(text(), 'Your listings')]",
                    "//div[@role='button'][contains(text(), 'Selling')]"
                ]

                # Try to find and click "Your listings" or similar
                for selector in my_listings_selectors:
                    try:
                        element = self.browser.find_element_safe(By.XPATH, selector, timeout=3)
                        if element:
                            self.browser.click_element_safe(element)
                            time.sleep(random.uniform(2, 4))
                            break
                    except Exception:
                        continue

                # Look for the specific listing
                listing_xpath = f"//*[contains(text(), '{product_title}')]"

                wait = WebDriverWait(self.browser.driver, timeout)
                try:
                    listing_element = wait.until(EC.presence_of_element_located((By.XPATH, listing_xpath)))
                    if listing_element:
                        self.logger.info("✅ Listing verified successfully!")
                        return True
                except TimeoutException:
                    self.logger.warning("⚠️ Could not verify listing publication")
                    return False

            except Exception as e:
                self.logger.warning(f"⚠️ Listing verification error: {e}")
                return False  # Not critical for the main process

        def get_listing_url(self, product_title: str) -> Optional[str]:
            """
            Get the URL of a published listing

            Args:
                product_title: Title of the product listing

            Returns:
                URL of the listing or None if not found
            """
            try:
                # This would require navigating to the listing and extracting the URL
                # Implementation depends on Facebook's current structure
                self.logger.info(f"🔗 Getting listing URL for: {product_title}")

                # Navigate to the specific listing (if verification was successful)
                if self.verify_listing_published(product_title):
                    current_url = self.browser.driver.current_url
                    if "marketplace" in current_url:
                        self.logger.info(f"📋 Listing URL: {current_url}")
                        return current_url

                return None

            except Exception as e:
                self.logger.warning(f"⚠️ Error getting listing URL: {e}")
                return None

    # Usage example for adding to existing FacebookBot class:
    """
    To integrate these methods into your existing FacebookBot class:

    1. Copy the methods above into your services/facebook_bot.py file
    2. Add them as methods to your existing FacebookBot class
    3. Import the necessary modules at the top of facebook_bot.py
    4. The methods are designed to work with your existing browser manager

    Example integration:
    ```python
    class FacebookBot:
        # ... your existing methods ...

        # Add all the methods from FacebookBotMarketplaceExtension above
        def navigate_to_marketplace(self):
            # ... method implementation ...

        def create_marketplace_listing(self, product: Product):
            # ... method implementation ...
    ```
    """

    def navigate_to_messages(self) -> bool:
        """
        Navigate to Facebook Messages/Messenger

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("💬 Navigating to Facebook Messages...")

            # Try direct URL first
            messages_url = "https://www.facebook.com/messages"
            if self.browser.navigate_to(messages_url):
                time.sleep(random.uniform(3, 5))

                # Wait for messages interface to load
                wait = WebDriverWait(self.browser.driver, 15)

                # Look for messages interface indicators
                message_indicators = [
                    "//div[@aria-label='Chats']",
                    "//div[contains(@class, 'messenger')]",
                    "//*[contains(text(), 'Messages')]",
                    "//div[@role='main']//div[contains(@aria-label, 'conversation')]"
                ]

                for indicator in message_indicators:
                    try:
                        element = wait.until(EC.presence_of_element_located((By.XPATH, indicator)))
                        if element:
                            self.logger.info("✅ Messages interface loaded")
                            return True
                    except TimeoutException:
                        continue

                # If direct indicators not found, assume success if page loaded
                self.logger.info("✅ Messages page loaded")
                return True

            return False

        except Exception as e:
            self.logger.error(f"❌ Error navigating to messages: {e}")
            return False

    def get_unread_conversations(self) -> List[Dict]:
        """
        Get list of unread conversations

        Returns:
            List of conversation data dictionaries
        """
        try:
            self.logger.info("📋 Scanning for unread conversations...")

            conversations = []

            # Look for unread message indicators
            unread_selectors = [
                "//div[contains(@class, 'unread')]",
                "//div[@aria-label='Mark as read']",
                "//*[contains(@class, 'notification')]//ancestor::div[contains(@role, 'listitem')]",
                "//div[contains(@style, 'font-weight: bold')]//ancestor::div[@role='listitem']"
            ]

            for selector in unread_selectors:
                try:
                    unread_elements = self.browser.driver.find_elements(By.XPATH, selector)

                    for element in unread_elements[:10]:  # Limit to first 10
                        try:
                            # Extract conversation info
                            conv_data = self._extract_conversation_data(element)
                            if conv_data:
                                conversations.append(conv_data)
                        except Exception as e:
                            self.logger.debug(f"Error extracting conversation: {e}")
                            continue

                    if conversations:
                        break  # Found conversations with this selector

                except Exception as e:
                    self.logger.debug(f"Selector failed: {selector}")
                    continue

            self.logger.info(f"📊 Found {len(conversations)} unread conversations")
            return conversations

        except Exception as e:
            self.logger.error(f"❌ Error getting unread conversations: {e}")
            return []

    def _extract_conversation_data(self, conversation_element) -> Optional[Dict]:
        """Extract data from a conversation element"""
        try:
            conv_data = {
                'conversation_id': '',
                'sender_name': '',
                'last_message': '',
                'timestamp': datetime.now(),
                'unread_count': 1,
                'element': conversation_element
            }

            # Try to extract sender name
            name_selectors = [
                ".//div[@role='gridcell']//span",
                ".//div[contains(@class, 'name')]",
                ".//strong",
                ".//h3"
            ]

            for selector in name_selectors:
                try:
                    name_element = conversation_element.find_element(By.XPATH, selector)
                    if name_element and name_element.text.strip():
                        conv_data['sender_name'] = name_element.text.strip()
                        break
                except:
                    continue

            # Try to extract last message preview
            message_selectors = [
                ".//div[@role='gridcell'][last()]//span",
                ".//div[contains(@class, 'preview')]",
                ".//div[contains(@class, 'snippet')]"
            ]

            for selector in message_selectors:
                try:
                    message_element = conversation_element.find_element(By.XPATH, selector)
                    if message_element and message_element.text.strip():
                        conv_data['last_message'] = message_element.text.strip()
                        break
                except:
                    continue

            # Generate conversation ID
            conv_data[
                'conversation_id'] = f"conv_{conv_data['sender_name'].replace(' ', '_').lower()}_{int(time.time())}"

            if conv_data['sender_name']:
                return conv_data

            return None

        except Exception as e:
            self.logger.debug(f"Error extracting conversation data: {e}")
            return None

    def open_conversation(self, conversation_data: Dict) -> bool:
        """
        Open a specific conversation

        Args:
            conversation_data: Conversation data from get_unread_conversations()

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"📱 Opening conversation with {conversation_data['sender_name']}")

            # Click on the conversation element
            conv_element = conversation_data['element']
            self.browser.click_element_safe(conv_element)

            # Wait for conversation to open
            time.sleep(random.uniform(2, 4))

            # Look for conversation interface
            wait = WebDriverWait(self.browser.driver, 10)
            conversation_indicators = [
                "//div[@role='textbox'][@aria-label='Message']",
                "//div[contains(@class, 'message-composer')]",
                "//textarea[@placeholder*='message']",
                "//div[@role='main']//div[contains(@class, 'conversation')]"
            ]

            for indicator in conversation_indicators:
                try:
                    element = wait.until(EC.presence_of_element_located((By.XPATH, indicator)))
                    if element:
                        self.logger.info("✅ Conversation opened successfully")
                        return True
                except TimeoutException:
                    continue

            self.logger.warning("⚠️ Conversation opened but interface not detected")
            return True  # Assume success

        except Exception as e:
            self.logger.error(f"❌ Error opening conversation: {e}")
            return False

    def get_conversation_messages(self, limit: int = 10) -> List[Message]:
        """
        Extract messages from the currently open conversation

        Args:
            limit: Maximum number of messages to extract

        Returns:
            List of Message objects
        """
        try:
            self.logger.info(f"📩 Extracting last {limit} messages from conversation...")

            messages = []

            # Look for message containers
            message_selectors = [
                "//div[@role='row']//div[contains(@class, 'message')]",
                "//div[contains(@class, 'conversation')]//div[contains(@class, 'message')]",
                "//div[@data-testid='message']",
                "//div[contains(@class, 'msg')]"
            ]

            message_elements = []
            for selector in message_selectors:
                try:
                    elements = self.browser.driver.find_elements(By.XPATH, selector)
                    if elements:
                        message_elements = elements
                        break
                except:
                    continue

            if not message_elements:
                self.logger.warning("⚠️ No message elements found")
                return []

            # Process last N messages
            recent_messages = message_elements[-limit:] if len(message_elements) > limit else message_elements

            for msg_element in recent_messages:
                try:
                    message_data = self._extract_message_data(msg_element)
                    if message_data:
                        messages.append(message_data)
                except Exception as e:
                    self.logger.debug(f"Error extracting message: {e}")
                    continue

            self.logger.info(f"📊 Extracted {len(messages)} messages")
            return messages

        except Exception as e:
            self.logger.error(f"❌ Error getting conversation messages: {e}")
            return []

    def _extract_message_data(self, message_element) -> Optional[Message]:
        """Extract message data from a message element"""
        try:
            # Try to determine if message is from customer or us
            is_customer_message = self._is_customer_message(message_element)

            if not is_customer_message:
                return None  # Skip our own messages

            # Extract message text
            text_selectors = [
                ".//span[contains(@dir, 'auto')]",
                ".//div[contains(@class, 'text')]",
                ".//span[not(@aria-hidden)]",
                ".//div[text()]"
            ]

            message_text = ""
            for selector in text_selectors:
                try:
                    text_elements = message_element.find_elements(By.XPATH, selector)
                    for text_elem in text_elements:
                        if text_elem.text.strip() and len(text_elem.text.strip()) > 3:
                            message_text = text_elem.text.strip()
                            break
                    if message_text:
                        break
                except:
                    continue

            if not message_text:
                return None

            # Extract sender name (try multiple approaches)
            sender_name = self._extract_sender_name(message_element)

            # Create Message object
            message = Message.create_customer_message(
                content=message_text,
                sender_name=sender_name or "Unknown Customer",
                conversation_id=f"conv_{int(time.time())}",
                account_email=self.account.email
            )

            return message

        except Exception as e:
            self.logger.debug(f"Error extracting message data: {e}")
            return None

    def _is_customer_message(self, message_element) -> bool:
        """Determine if message is from customer (not from us)"""
        try:
            # Look for indicators that this is our message vs customer message
            our_message_indicators = [
                "sent by you",
                "data-testid='message_sent'",
                "class*='right'",
                "class*='outgoing'",
                "aria-label*='You sent'"
            ]

            element_html = message_element.get_attribute('outerHTML').lower()

            for indicator in our_message_indicators:
                if indicator.lower() in element_html:
                    return False  # This is our message

            return True  # Assume customer message

        except:
            return True  # Default to customer message

    def _extract_sender_name(self, message_element) -> Optional[str]:
        """Extract sender name from message element"""
        try:
            # Try to find sender name in various places
            name_selectors = [
                ".//preceding-sibling::*//strong",
                ".//ancestor::*[@role='row']//strong",
                ".//ancestor::*[contains(@class, 'message')]//h4",
                ".//preceding::*[contains(@class, 'name')][1]"
            ]

            for selector in name_selectors:
                try:
                    name_element = message_element.find_element(By.XPATH, selector)
                    if name_element and name_element.text.strip():
                        return name_element.text.strip()
                except:
                    continue

            return None

        except:
            return None

    def send_message(self, message_text: str) -> bool:
        """
        Send a message in the currently open conversation

        Args:
            message_text: Text to send

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"📤 Sending message: {message_text[:50]}...")

            # Find message input field
            input_selectors = [
                "//div[@role='textbox'][@aria-label='Message']",
                "//div[@role='textbox'][@data-testid='message-text']",
                "//textarea[@placeholder*='message']",
                "//div[contains(@class, 'composer')]//div[@contenteditable='true']"
            ]

            message_input = None
            for selector in input_selectors:
                try:
                    message_input = self.browser.find_element_safe(By.XPATH, selector, timeout=5)
                    if message_input:
                        break
                except:
                    continue

            if not message_input:
                self.logger.error("❌ Could not find message input field")
                return False

            # Clear input and type message
            message_input.click()
            time.sleep(0.5)

            # Clear any existing text
            message_input.send_keys(Keys.CONTROL + "a")
            time.sleep(0.2)

            # Type message with human-like typing
            if self.browser.type_text_human(message_input, message_text):
                time.sleep(random.uniform(1, 2))

                # Send message (Enter key)
                message_input.send_keys(Keys.RETURN)
                time.sleep(random.uniform(1, 3))

                self.logger.info("✅ Message sent successfully")
                log_facebook_action("send_message", self.account.email, True, f"Sent: {message_text[:30]}...")
                return True
            else:
                self.logger.error("❌ Failed to type message")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error sending message: {e}")
            log_facebook_action("send_message", self.account.email, False, f"Error: {str(e)}")
            return False

    def mark_conversation_as_read(self) -> bool:
        """Mark the current conversation as read"""
        try:
            # Look for mark as read options
            read_selectors = [
                "//div[@aria-label='Mark as read']",
                "//button[contains(text(), 'Mark as read')]",
                "//*[@data-testid='mark_read']"
            ]

            for selector in read_selectors:
                try:
                    read_button = self.browser.find_element_safe(By.XPATH, selector, timeout=2)
                    if read_button:
                        self.browser.click_element_safe(read_button)
                        self.logger.debug("✅ Marked conversation as read")
                        return True
                except:
                    continue

            # If no explicit button, conversation is likely already marked as read
            return True

        except Exception as e:
            self.logger.debug(f"Mark as read error: {e}")
            return True  # Not critical

    def run_message_monitoring_cycle(self, process_callback=None) -> Dict[str, int]:
        """
        Run one complete cycle of message monitoring

        Args:
            process_callback: Optional callback function to process each message

        Returns:
            Dictionary with monitoring statistics
        """
        cycle_stats = {
            'conversations_checked': 0,
            'messages_found': 0,
            'messages_processed': 0,
            'responses_sent': 0,
            'errors': 0
        }

        try:
            self.logger.info("🔄 Starting message monitoring cycle...")

            # Navigate to messages
            if not self.navigate_to_messages():
                cycle_stats['errors'] += 1
                return cycle_stats

            # Get unread conversations
            conversations = self.get_unread_conversations()
            cycle_stats['conversations_checked'] = len(conversations)

            if not conversations:
                self.logger.info("📭 No unread conversations found")
                return cycle_stats

            self.logger.info(f"📩 Processing {len(conversations)} unread conversations")

            for conv_data in conversations:
                try:
                    # Open conversation
                    if not self.open_conversation(conv_data):
                        cycle_stats['errors'] += 1
                        continue

                    # Get messages from conversation
                    messages = self.get_conversation_messages(limit=5)
                    cycle_stats['messages_found'] += len(messages)

                    if not messages:
                        continue

                    # Process each message
                    for message in messages:
                        try:
                            # Use callback if provided, otherwise use default processing
                            if process_callback:
                                if process_callback(message):
                                    cycle_stats['messages_processed'] += 1
                            else:
                                self.logger.info(f"📩 New message: {message.get_short_content()}")
                                cycle_stats['messages_processed'] += 1

                        except Exception as e:
                            self.logger.error(f"Error processing message: {e}")
                            cycle_stats['errors'] += 1

                    # Mark conversation as read
                    self.mark_conversation_as_read()

                    # Small delay between conversations
                    time.sleep(random.uniform(1, 3))

                except Exception as e:
                    self.logger.error(f"Error processing conversation: {e}")
                    cycle_stats['errors'] += 1
                    continue

            return cycle_stats

        except Exception as e:
            self.logger.error(f"❌ Error in monitoring cycle: {e}")
            cycle_stats['errors'] += 1
            return cycle_stats

    def start_automated_customer_service(self, ai_service, products: List = None, duration_minutes: int = 30):
        """
        Start automated customer service with AI responses

        Args:
            ai_service: LlamaAI instance for generating responses
            products: List of products for context
            duration_minutes: How long to run monitoring
        """
        try:
            self.logger.info(f"🤖 Starting automated customer service for {duration_minutes} minutes...")

            end_time = datetime.now() + timedelta(minutes=duration_minutes)
            cycle_count = 0
            total_responses = 0

            def ai_response_processor(message: Message) -> bool:
                """Process messages with AI responses"""
                nonlocal total_responses

                try:
                    self.logger.info(f"🤖 Processing message: {message.get_short_content()}")

                    # Check if requires human attention
                    if message.requires_human_attention:
                        self.logger.warning("⚠️ Message escalated to human operator")
                        return True

                    # Find relevant product for context
                    relevant_product = None
                    if products:
                        for product in products:
                            if any(word in message.content.lower() for word in product.title.lower().split()):
                                relevant_product = product
                                break

                        if not relevant_product:
                            relevant_product = products[0]  # Use first product as fallback

                    # Generate AI response
                    response = ai_service.generate_response(message, relevant_product)

                    if response:
                        # Send response
                        if self.send_message(response):
                            total_responses += 1
                            self.logger.info("✅ AI response sent successfully")
                            return True
                        else:
                            self.logger.error("❌ Failed to send AI response")
                            return False
                    else:
                        self.logger.warning("⚠️ Could not generate AI response")
                        return False

                except Exception as e:
                    self.logger.error(f"Error in AI processor: {e}")
                    return False

            while datetime.now() < end_time:
                cycle_count += 1
                self.logger.info(f"\n🔄 Customer Service Cycle {cycle_count}")

                # Run monitoring with AI processor
                stats = self.run_message_monitoring_cycle(ai_response_processor)

                self.logger.info(f"📊 Cycle {cycle_count} Results:")
                self.logger.info(f"   📱 Conversations: {stats['conversations_checked']}")
                self.logger.info(f"   📩 Messages: {stats['messages_found']}")
                self.logger.info(f"   ✅ Processed: {stats['messages_processed']}")
                self.logger.info(f"   🤖 AI Responses: {total_responses}")

                # Wait before next cycle (30 seconds default)
                if datetime.now() < end_time:
                    wait_time = getattr(Config, 'MESSAGE_CHECK_INTERVAL', 30)
                    self.logger.info(f"⏸️ Waiting {wait_time}s before next cycle...")
                    time.sleep(wait_time)

            self.logger.info(f"\n🎉 Automated customer service completed!")
            self.logger.info(f"📊 Total AI responses sent: {total_responses}")

        except KeyboardInterrupt:
            self.logger.info("\n⏹️ Customer service stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Error in automated customer service: {e}")


# Usage instructions for integrating with FacebookBot:
"""
To integrate these methods into your existing FacebookBot class:

1. Copy all the methods above into your services/facebook_bot.py file
2. Add them as methods to your existing FacebookBot class
3. The methods will work with your existing browser manager

Example usage:
```python
# Initialize bot
bot = FacebookBot(account)

# Start browser session
with create_browser_manager() as browser:
    bot.browser = browser

    if bot.login():
        # Option 1: Manual monitoring cycle
        stats = bot.run_message_monitoring_cycle()
        print(f"Found {stats['messages_found']} messages")

        # Option 2: Automated AI customer service
        ai_service = LlamaAI()
        products = load_products()
        bot.start_automated_customer_service(ai_service, products, duration_minutes=30)
```
"""

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

    def setup_browser(self, browser_manager: BrowserManager) -> bool:
        """Set up browser manager for this bot"""
        try:
            self.browser = browser_manager
            self.logger.info("Browser manager attached to FacebookBot")
            return True
        except Exception as e:
            self.logger.error(f"Failed to setup browser: {e}")
            return False

    def create_marketplace_listing(self, product: Product) -> bool:
        """Create marketplace listing"""
        try:
            self.logger.info(f"🏪 Creating marketplace listing for: {product.title}")

            if not self.is_logged_in and not self.logged_in:
                self.logger.error("Must be logged in to create listing")
                return False

            # Navigate to marketplace create page
            create_url = "https://www.facebook.com/marketplace/create/"
            if not self.browser.navigate_to(create_url):
                self.logger.error("Failed to navigate to create listing page")
                return False

            self.browser.human_delay(3, 5)

            # Fill basic information
            self._fill_listing_basic_info(product)

            self.listings_created += 1
            self.logger.info("🎉 Marketplace listing created successfully!")
            return True

        except Exception as e:
            self.listings_failed += 1
            self.logger.error(f"❌ Failed to create listing: {e}")
            return False

    def _fill_listing_basic_info(self, product: Product):
        """Fill basic listing information"""
        try:
            # Fill title
            title_selectors = ['input[placeholder*="What are you selling?"]', 'input[aria-label*="title"]']
            for selector in title_selectors:
                title_field = self.browser.find_element_safe(By.CSS_SELECTOR, selector)
                if title_field:
                    self.browser.type_text_human(title_field, product.title, clear_first=True)
                    break

            # Fill price
            price_selectors = ['input[placeholder*="Price"]', 'input[aria-label*="Price"]']
            for selector in price_selectors:
                price_field = self.browser.find_element_safe(By.CSS_SELECTOR, selector)
                if price_field:
                    self.browser.type_text_human(price_field, str(product.price), clear_first=True)
                    break

            self.logger.info("✅ Basic listing information filled")
        except Exception as e:
            self.logger.warning(f"⚠️ Error filling listing info: {e}")

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


