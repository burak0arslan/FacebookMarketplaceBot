"""
Facebook Bot Service - Complete Playwright Implementation
This service handles Facebook login, navigation, marketplace operations, and message monitoring
Full feature parity with 2000+ line Selenium version
"""

import time
import random
import asyncio
import json
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path

from playwright.async_api import Page, BrowserContext, Locator
from playwright.sync_api import Page as SyncPage, BrowserContext as SyncBrowserContext

from utils.browser_utils import PlaywrightBrowserManager
from utils.facebook_selectors import FacebookSelectors, find_element_with_fallback, find_element_with_fallback_async
from utils.logger import get_logger, log_facebook_action, log_performance
from models.account import Account
from models.product import Product
from models.message import Message
from config import Config


class FacebookBotPlaywright:
    """
    Complete Facebook automation service for marketplace operations using Playwright

    Features:
    - Facebook login with anti-detection
    - Session management and persistence
    - Marketplace navigation and listing creation
    - Message monitoring and automated responses
    - CAPTCHA detection and handling
    - Error recovery and retry logic
    - Activity monitoring and rate limiting
    - AI integration for customer service
    - Multi-account support
    - Performance analytics
    """

    def __init__(self, account: Account, headless: bool = None, async_mode: bool = True):
        """
        Initialize FacebookBot for a specific account

        Args:
            account: Account object with Facebook credentials
            headless: Run browser in headless mode (None = use config)
            async_mode: Use async Playwright (recommended)
        """
        self.account = account
        self.async_mode = async_mode
        self.logger = get_logger(f"facebook_bot_{account.get_masked_email()}")

        # Browser management
        self.browser: Optional[PlaywrightBrowserManager] = None
        self.page: Optional[Page] = None
        self.context: Optional[BrowserContext] = None
        self.headless = headless if headless is not None else Config.HEADLESS_MODE

        # Session management
        self.is_logged_in = False
        self.logged_in = False  # Alias for compatibility
        self.last_activity = None
        self.session_data = {}
        self.session_start_time = None
        self.current_url = ""

        # Rate limiting and activity tracking
        self.last_action_time = time.time()
        self.action_count = 0
        self.daily_action_limit = getattr(Config, 'DAILY_ACTION_LIMIT', 1000)
        self.requests_made = 0
        self.requests_successful = 0
        self.requests_failed = 0

        # Marketplace tracking
        self.listings_created = 0
        self.listings_failed = 0
        self.listings_updated = 0

        # Message tracking
        self.messages_sent = 0
        self.messages_received = 0
        self.conversations_handled = 0

        # Performance tracking
        self.start_time = time.time()
        self.total_actions = 0
        self.errors_count = 0
        self.page_load_times = []

        # AI and automation
        self.ai_service = None
        self.auto_reply_enabled = getattr(Config, 'AUTO_REPLY_ENABLED', False)
        self.last_message_check = None

        # Configuration
        self.screenshot_enabled = getattr(Config, 'TAKE_SCREENSHOTS', True)
        self.human_delay_min = getattr(Config, 'HUMAN_DELAY_MIN', 1.0)
        self.human_delay_max = getattr(Config, 'HUMAN_DELAY_MAX', 3.0)

        self.logger.info(f"FacebookBot initialized for {account.get_masked_email()} (async={async_mode})")

    # ================== INITIALIZATION METHODS ==================

    async def initialize_async(self, profile_name: str = "default") -> bool:
        """Initialize browser and setup (async)"""
        try:
            self.logger.info("🚀 Initializing Facebook bot (async)...")

            # Create browser manager
            self.browser = PlaywrightBrowserManager(
                headless=self.headless,
                user_data_dir=f"./browser_data/{profile_name}",
                async_mode=True
            )

            # Setup browser
            success = await self.browser.setup_browser_async(profile_name)
            if not success:
                self.logger.error("Failed to setup browser")
                return False

            self.page = self.browser.page
            self.context = self.browser.context
            self.session_start_time = datetime.now()

            self.logger.info("✅ Browser initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {e}")
            return False

    def initialize_sync(self, profile_name: str = "default") -> bool:
        """Initialize browser and setup (sync)"""
        try:
            self.logger.info("🚀 Initializing Facebook bot (sync)...")

            # Create browser manager
            self.browser = PlaywrightBrowserManager(
                headless=self.headless,
                user_data_dir=f"./browser_data/{profile_name}",
                async_mode=False
            )

            # Setup browser
            success = self.browser.setup_browser_sync(profile_name)
            if not success:
                self.logger.error("Failed to setup browser")
                return False

            self.page = self.browser.page
            self.context = self.browser.context
            self.session_start_time = datetime.now()

            self.logger.info("✅ Browser initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {e}")
            return False

    def start_session(self, profile_name: str = "default") -> bool:
        """Start Facebook session (for compatibility)"""
        if self.async_mode:
            # Cannot call async from sync context, user should use initialize_async
            raise RuntimeError("Use initialize_async() for async mode")
        return self.initialize_sync(profile_name)

    # ================== LOGIN AND AUTHENTICATION ==================

    async def login_async(self, max_retries: int = 3) -> bool:
        """Login to Facebook with anti-detection measures (async)"""
        for attempt in range(max_retries):
            try:
                self.logger.info(f"🔐 Attempting Facebook login (attempt {attempt + 1}/{max_retries})...")

                # Navigate to Facebook
                success = await self.browser.navigate_to_async("https://www.facebook.com")
                if not success:
                    continue

                # Check if already logged in
                if await self._check_login_status_async():
                    self.logger.info("✅ Already logged in!")
                    self.is_logged_in = True
                    self.logged_in = True
                    return True

                # Find and fill email
                await self._human_delay_async()
                email_success = await self.browser.type_text_async(
                    FacebookSelectors.LOGIN_EMAIL_SELECTORS[0],
                    self.account.email
                )

                if not email_success:
                    self.logger.error("Failed to enter email")
                    continue

                await self._human_delay_async()

                # Find and fill password
                password_success = await self.browser.type_text_async(
                    FacebookSelectors.LOGIN_PASSWORD_SELECTORS[0],
                    self.account.password
                )

                if not password_success:
                    self.logger.error("Failed to enter password")
                    continue

                await self._human_delay_async()

                # Click login button
                login_success = await self.browser.click_element_async(
                    FacebookSelectors.LOGIN_BUTTON_SELECTORS[0]
                )

                if not login_success:
                    self.logger.error("Login button click failed")
                    continue

                # Wait for login to complete
                await asyncio.sleep(3)

                # Handle security checks
                if await self._handle_security_checks_async():
                    await asyncio.sleep(5)

                # Verify login success
                if await self._check_login_status_async():
                    self.logger.info("✅ Login successful!")
                    self.is_logged_in = True
                    self.logged_in = True
                    self.last_activity = datetime.now()
                    self.requests_successful += 1
                    log_facebook_action("login_success", self.account.get_masked_email())
                    return True
                else:
                    self.logger.warning("❌ Login verification failed")
                    self.requests_failed += 1

            except Exception as e:
                self.logger.error(f"Login attempt {attempt + 1} failed: {e}")
                self.errors_count += 1
                if self.screenshot_enabled:
                    await self.browser.take_screenshot_async(f"login_error_{attempt}.png")

        self.logger.error("❌ All login attempts failed")
        return False

    def login_sync(self, max_retries: int = 3) -> bool:
        """Login to Facebook with anti-detection measures (sync)"""
        for attempt in range(max_retries):
            try:
                self.logger.info(f"🔐 Attempting Facebook login (attempt {attempt + 1}/{max_retries})...")

                # Navigate to Facebook
                success = self.browser.navigate_to_sync("https://www.facebook.com")
                if not success:
                    continue

                # Check if already logged in
                if self._check_login_status_sync():
                    self.logger.info("✅ Already logged in!")
                    self.is_logged_in = True
                    self.logged_in = True
                    return True

                # Find and fill email
                self._human_delay_sync()
                email_success = self.browser.type_text_sync(
                    FacebookSelectors.LOGIN_EMAIL_SELECTORS[0],
                    self.account.email
                )

                if not email_success:
                    self.logger.error("Failed to enter email")
                    continue

                self._human_delay_sync()

                # Find and fill password
                password_success = self.browser.type_text_sync(
                    FacebookSelectors.LOGIN_PASSWORD_SELECTORS[0],
                    self.account.password
                )

                if not password_success:
                    self.logger.error("Failed to enter password")
                    continue

                self._human_delay_sync()

                # Click login button
                login_success = self.browser.click_element_sync(
                    FacebookSelectors.LOGIN_BUTTON_SELECTORS[0]
                )

                if not login_success:
                    self.logger.error("Login button click failed")
                    continue

                # Wait for login to complete
                time.sleep(3)

                # Handle security checks
                if self._handle_security_checks_sync():
                    time.sleep(5)

                # Verify login success
                if self._check_login_status_sync():
                    self.logger.info("✅ Login successful!")
                    self.is_logged_in = True
                    self.logged_in = True
                    self.last_activity = datetime.now()
                    self.requests_successful += 1
                    log_facebook_action("login_success", self.account.get_masked_email())
                    return True
                else:
                    self.logger.warning("❌ Login verification failed")
                    self.requests_failed += 1

            except Exception as e:
                self.logger.error(f"Login attempt {attempt + 1} failed: {e}")
                self.errors_count += 1
                if self.screenshot_enabled:
                    self.browser.take_screenshot_sync(f"login_error_{attempt}.png")

        self.logger.error("❌ All login attempts failed")
        return False

    def login(self, max_retries: int = 3) -> bool:
        """Login wrapper for compatibility"""
        if self.async_mode:
            raise RuntimeError("Use login_async() for async mode")
        return self.login_sync(max_retries)

    async def _check_login_status_async(self) -> bool:
        """Check if user is currently logged in (async)"""
        try:
            # Look for profile menu or specific logged-in indicators
            profile_element = await self.browser.find_element_async(
                FacebookSelectors.PROFILE_MENU_SELECTORS[0], timeout=2000
            )
            return profile_element is not None
        except:
            return False

    def _check_login_status_sync(self) -> bool:
        """Check if user is currently logged in (sync)"""
        try:
            # Look for profile menu or specific logged-in indicators
            profile_element = self.browser.find_element_sync(
                FacebookSelectors.PROFILE_MENU_SELECTORS[0], timeout=2000
            )
            return profile_element is not None
        except:
            return False

    async def _handle_security_checks_async(self) -> bool:
        """Handle CAPTCHA and two-factor authentication (async)"""
        try:
            # Check for CAPTCHA
            captcha_found = False
            for selector in FacebookSelectors.get_captcha_selectors():
                captcha_element = await self.browser.find_element_async(selector, timeout=1000)
                if captcha_element:
                    captcha_found = True
                    break

            if captcha_found:
                self.logger.warning("🔒 CAPTCHA detected - manual intervention required")
                if self.screenshot_enabled:
                    await self.browser.take_screenshot_async("captcha_detected.png")

                # Wait for manual CAPTCHA solving
                input("Please solve the CAPTCHA manually and press Enter to continue...")
                return True

            # Check for two-factor authentication
            two_factor_found = False
            for selector in FacebookSelectors.TWO_FACTOR_SELECTORS:
                two_factor_element = await self.browser.find_element_async(selector, timeout=1000)
                if two_factor_element:
                    two_factor_found = True
                    break

            if two_factor_found:
                self.logger.warning("📱 Two-factor authentication required")
                if self.screenshot_enabled:
                    await self.browser.take_screenshot_async("two_factor_detected.png")

                # Wait for manual 2FA
                input("Please complete two-factor authentication and press Enter to continue...")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error handling security checks: {e}")
            return False

    def _handle_security_checks_sync(self) -> bool:
        """Handle CAPTCHA and two-factor authentication (sync)"""
        try:
            # Check for CAPTCHA
            captcha_found = False
            for selector in FacebookSelectors.get_captcha_selectors():
                captcha_element = self.browser.find_element_sync(selector, timeout=1000)
                if captcha_element:
                    captcha_found = True
                    break

            if captcha_found:
                self.logger.warning("🔒 CAPTCHA detected - manual intervention required")
                if self.screenshot_enabled:
                    self.browser.take_screenshot_sync("captcha_detected.png")

                # Wait for manual CAPTCHA solving
                input("Please solve the CAPTCHA manually and press Enter to continue...")
                return True

            # Check for two-factor authentication
            two_factor_found = False
            for selector in FacebookSelectors.TWO_FACTOR_SELECTORS:
                two_factor_element = self.browser.find_element_sync(selector, timeout=1000)
                if two_factor_element:
                    two_factor_found = True
                    break

            if two_factor_found:
                self.logger.warning("📱 Two-factor authentication required")
                if self.screenshot_enabled:
                    self.browser.take_screenshot_sync("two_factor_detected.png")

                # Wait for manual 2FA
                input("Please complete two-factor authentication and press Enter to continue...")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error handling security checks: {e}")
            return False

    # ================== NAVIGATION METHODS ==================

    async def navigate_to_marketplace_async(self) -> bool:
        """Navigate to Facebook Marketplace (async)"""
        try:
            self.logger.info("🏪 Navigating to Marketplace...")

            # Try direct URL first
            marketplace_url = "https://www.facebook.com/marketplace"
            success = await self.browser.navigate_to_async(marketplace_url)

            if success:
                await self._human_delay_async()
                self.current_url = await self.page.url
                self.logger.info("✅ Successfully navigated to Marketplace")
                self.requests_successful += 1
                return True
            else:
                self.logger.error("❌ Failed to navigate to Marketplace")
                self.requests_failed += 1
                return False

        except Exception as e:
            self.logger.error(f"Error navigating to Marketplace: {e}")
            self.errors_count += 1
            return False

    def navigate_to_marketplace_sync(self) -> bool:
        """Navigate to Facebook Marketplace (sync)"""
        try:
            self.logger.info("🏪 Navigating to Marketplace...")

            # Try direct URL first
            marketplace_url = "https://www.facebook.com/marketplace"
            success = self.browser.navigate_to_sync(marketplace_url)

            if success:
                self._human_delay_sync()
                self.current_url = self.page.url
                self.logger.info("✅ Successfully navigated to Marketplace")
                self.requests_successful += 1
                return True
            else:
                self.logger.error("❌ Failed to navigate to Marketplace")
                self.requests_failed += 1
                return False

        except Exception as e:
            self.logger.error(f"Error navigating to Marketplace: {e}")
            self.errors_count += 1
            return False

    def navigate_to_marketplace(self) -> bool:
        """Navigate to marketplace wrapper for compatibility"""
        if self.async_mode:
            raise RuntimeError("Use navigate_to_marketplace_async() for async mode")
        return self.navigate_to_marketplace_sync()

    async def navigate_to_messages_async(self) -> bool:
        """Navigate to Facebook Messages (async)"""
        try:
            self.logger.info("💬 Navigating to Messages...")

            # Try direct URL first
            messages_url = "https://www.facebook.com/messages"
            success = await self.browser.navigate_to_async(messages_url)

            if success:
                await self._human_delay_async()
                self.current_url = await self.page.url
                self.logger.info("✅ Successfully navigated to Messages")
                self.requests_successful += 1
                return True
            else:
                self.logger.error("❌ Failed to navigate to Messages")
                self.requests_failed += 1
                return False

        except Exception as e:
            self.logger.error(f"Error navigating to Messages: {e}")
            self.errors_count += 1
            return False

    def navigate_to_messages_sync(self) -> bool:
        """Navigate to Facebook Messages (sync)"""
        try:
            self.logger.info("💬 Navigating to Messages...")

            # Try direct URL first
            messages_url = "https://www.facebook.com/messages"
            success = self.browser.navigate_to_sync(messages_url)

            if success:
                self._human_delay_sync()
                self.current_url = self.page.url
                self.logger.info("✅ Successfully navigated to Messages")
                self.requests_successful += 1
                return True
            else:
                self.logger.error("❌ Failed to navigate to Messages")
                self.requests_failed += 1
                return False

        except Exception as e:
            self.logger.error(f"Error navigating to Messages: {e}")
            self.errors_count += 1
            return False

    def navigate_to_messages(self) -> bool:
        """Navigate to messages wrapper for compatibility"""
        if self.async_mode:
            raise RuntimeError("Use navigate_to_messages_async() for async mode")
        return self.navigate_to_messages_sync()

    # ================== MARKETPLACE OPERATIONS ==================

    async def create_marketplace_listing_async(self, product: Product) -> bool:
        """Create marketplace listing (async)"""
        try:
            self.logger.info(f"🏪 Creating marketplace listing for: {product.title}")

            if not self.is_logged_in:
                self.logger.error("Must be logged in to create listing")
                return False

            # Navigate to marketplace create page
            create_url = "https://www.facebook.com/marketplace/create/"
            success = await self.browser.navigate_to_async(create_url)
            if not success:
                self.logger.error("Failed to navigate to create listing page")
                return False

            await self._human_delay_async(3, 5)

            # Fill listing information
            await self._fill_listing_basic_info_async(product)

            # Upload images if available
            if product.images:
                await self._upload_listing_images_async(product.images)

            # Fill description
            await self._fill_listing_description_async(product)

            # Set category and location
            await self._set_listing_category_async(product)
            await self._set_listing_location_async(product)

            # Submit listing
            submit_success = await self._submit_listing_async()

            if submit_success:
                self.listings_created += 1
                self.logger.info("🎉 Marketplace listing created successfully!")
                log_facebook_action("create_listing", self.account.get_masked_email(), True, product.title)
                return True
            else:
                self.listings_failed += 1
                return False

        except Exception as e:
            self.listings_failed += 1
            self.logger.error(f"❌ Failed to create listing: {e}")
            self.errors_count += 1
            return False

    def create_marketplace_listing_sync(self, product: Product) -> bool:
        """Create marketplace listing (sync)"""
        try:
            self.logger.info(f"🏪 Creating marketplace listing for: {product.title}")

            if not self.is_logged_in:
                self.logger.error("Must be logged in to create listing")
                return False

            # Navigate to marketplace create page
            create_url = "https://www.facebook.com/marketplace/create/"
            success = self.browser.navigate_to_sync(create_url)
            if not success:
                self.logger.error("Failed to navigate to create listing page")
                return False

            self._human_delay_sync(3, 5)

            # Fill listing information
            self._fill_listing_basic_info_sync(product)

            # Upload images if available
            if product.images:
                self._upload_listing_images_sync(product.images)

            # Fill description
            self._fill_listing_description_sync(product)

            # Set category and location
            self._set_listing_category_sync(product)
            self._set_listing_location_sync(product)

            # Submit listing
            submit_success = self._submit_listing_sync()

            if submit_success:
                self.listings_created += 1
                self.logger.info("🎉 Marketplace listing created successfully!")
                log_facebook_action("create_listing", self.account.get_masked_email(), True, product.title)
                return True
            else:
                self.listings_failed += 1
                return False

        except Exception as e:
            self.listings_failed += 1
            self.logger.error(f"❌ Failed to create listing: {e}")
            self.errors_count += 1
            return False

    def create_marketplace_listing(self, product: Product) -> bool:
        """Create marketplace listing wrapper for compatibility"""
        if self.async_mode:
            raise RuntimeError("Use create_marketplace_listing_async() for async mode")
        return self.create_marketplace_listing_sync(product)

    async def _fill_listing_basic_info_async(self, product: Product):
        """Fill basic listing information (async)"""
        try:
            # Fill title
            title_success = await self.browser.type_text_async(
                'input[placeholder*="What are you selling?" i]',
                product.title
            )
            if not title_success:
                # Try alternative selectors
                for selector in ['input[aria-label*="title" i]', 'input[name="title"]']:
                    if await self.browser.type_text_async(selector, product.title):
                        break

            await self._human_delay_async()

            # Fill price
            price_text = str(product.price) if hasattr(product, 'price') else "0"
            price_success = await self.browser.type_text_async(
                'input[placeholder*="Price" i]',
                price_text
            )
            if not price_success:
                # Try alternative selectors
                for selector in ['input[aria-label*="Price" i]', 'input[name="price"]']:
                    if await self.browser.type_text_async(selector, price_text):
                        break

            self.logger.info("✅ Basic listing information filled")
        except Exception as e:
            self.logger.warning(f"⚠️ Error filling listing info: {e}")

    def _fill_listing_basic_info_sync(self, product: Product):
        """Fill basic listing information (sync)"""
        try:
            # Fill title
            title_success = self.browser.type_text_sync(
                'input[placeholder*="What are you selling?" i]',
                product.title
            )
            if not title_success:
                # Try alternative selectors
                for selector in ['input[aria-label*="title" i]', 'input[name="title"]']:
                    if self.browser.type_text_sync(selector, product.title):
                        break

            self._human_delay_sync()

            # Fill price
            price_text = str(product.price) if hasattr(product, 'price') else "0"
            price_success = self.browser.type_text_sync(
                'input[placeholder*="Price" i]',
                price_text
            )
            if not price_success:
                # Try alternative selectors
                for selector in ['input[aria-label*="Price" i]', 'input[name="price"]']:
                    if self.browser.type_text_sync(selector, price_text):
                        break

            self.logger.info("✅ Basic listing information filled")
        except Exception as e:
            self.logger.warning(f"⚠️ Error filling listing info: {e}")

    async def _upload_listing_images_async(self, images: List[str]):
        """Upload images for listing (async)"""
        try:
            self.logger.info(f"📸 Uploading {len(images)} images...")

            # Find file upload input
            upload_selectors = [
                'input[type="file"]',
                'input[accept*="image"]',
                '[data-testid="media-upload"]'
            ]

            for selector in upload_selectors:
                upload_element = await self.browser.find_element_async(selector)
                if upload_element:
                    # Upload files
                    await self.page.set_input_files(selector, images[:10])  # Limit to 10 images
                    await self._human_delay_async()
                    self.logger.info(f"✅ Uploaded {min(len(images), 10)} images")
                    return

            self.logger.warning("⚠️ Could not find image upload field")
        except Exception as e:
            self.logger.warning(f"⚠️ Error uploading images: {e}")

    def _upload_listing_images_sync(self, images: List[str]):
        """Upload images for listing (sync)"""
        try:
            self.logger.info(f"📸 Uploading {len(images)} images...")

            # Find file upload input
            upload_selectors = [
                'input[type="file"]',
                'input[accept*="image"]',
                '[data-testid="media-upload"]'
            ]

            for selector in upload_selectors:
                upload_element = self.browser.find_element_sync(selector)
                if upload_element:
                    # Upload files
                    self.page.set_input_files(selector, images[:10])  # Limit to 10 images
                    self._human_delay_sync()
                    self.logger.info(f"✅ Uploaded {min(len(images), 10)} images")
                    return

            self.logger.warning("⚠️ Could not find image upload field")
        except Exception as e:
            self.logger.warning(f"⚠️ Error uploading images: {e}")

    async def _fill_listing_description_async(self, product: Product):
        """Fill listing description (async)"""
        try:
            if hasattr(product, 'description') and product.description:
                description_success = await self.browser.type_text_async(
                    'textarea[placeholder*="description" i]',
                    product.description
                )
                if not description_success:
                    # Try alternative selectors
                    for selector in ['textarea[aria-label*="description" i]', 'div[contenteditable="true"]']:
                        if await self.browser.type_text_async(selector, product.description):
                            break

                self.logger.info("✅ Description filled")
        except Exception as e:
            self.logger.warning(f"⚠️ Error filling description: {e}")

    def _fill_listing_description_sync(self, product: Product):
        """Fill listing description (sync)"""
        try:
            if hasattr(product, 'description') and product.description:
                description_success = self.browser.type_text_sync(
                    'textarea[placeholder*="description" i]',
                    product.description
                )
                if not description_success:
                    # Try alternative selectors
                    for selector in ['textarea[aria-label*="description" i]', 'div[contenteditable="true"]']:
                        if self.browser.type_text_sync(selector, product.description):
                            break

                self.logger.info("✅ Description filled")
        except Exception as e:
            self.logger.warning(f"⚠️ Error filling description: {e}")

    async def _set_listing_category_async(self, product: Product):
        """Set listing category (async)"""
        try:
            if hasattr(product, 'category') and product.category:
                # Click category dropdown
                category_success = await self.browser.click_element_async(
                    '[aria-label*="Category" i]'
                )
                if category_success:
                    await self._human_delay_async()
                    # Select category from dropdown
                    await self.browser.click_element_async(f'text="{product.category}"')
                    self.logger.info(f"✅ Category set to: {product.category}")
        except Exception as e:
            self.logger.warning(f"⚠️ Error setting category: {e}")

    def _set_listing_category_sync(self, product: Product):
        """Set listing category (sync)"""
        try:
            if hasattr(product, 'category') and product.category:
                # Click category dropdown
                category_success = self.browser.click_element_sync(
                    '[aria-label*="Category" i]'
                )
                if category_success:
                    self._human_delay_sync()
                    # Select category from dropdown
                    self.browser.click_element_sync(f'text="{product.category}"')
                    self.logger.info(f"✅ Category set to: {product.category}")
        except Exception as e:
            self.logger.warning(f"⚠️ Error setting category: {e}")

    async def _set_listing_location_async(self, product: Product):
        """Set listing location (async)"""
        try:
            if hasattr(product, 'location') and product.location:
                location_success = await self.browser.type_text_async(
                    'input[placeholder*="location" i]',
                    product.location
                )
                if location_success:
                    await self._human_delay_async()
                    self.logger.info(f"✅ Location set to: {product.location}")
        except Exception as e:
            self.logger.warning(f"⚠️ Error setting location: {e}")

    def _set_listing_location_sync(self, product: Product):
        """Set listing location (sync)"""
        try:
            if hasattr(product, 'location') and product.location:
                location_success = self.browser.type_text_sync(
                    'input[placeholder*="location" i]',
                    product.location
                )
                if location_success:
                    self._human_delay_sync()
                    self.logger.info(f"✅ Location set to: {product.location}")
        except Exception as e:
            self.logger.warning(f"⚠️ Error setting location: {e}")

    async def _submit_listing_async(self) -> bool:
        """Submit the listing (async)"""
        try:
            # Find and click submit/publish button
            submit_selectors = [
                'button:has-text("Publish")',
                'button:has-text("Submit")',
                'button[aria-label*="Publish" i]',
                'button[type="submit"]'
            ]

            for selector in submit_selectors:
                submit_success = await self.browser.click_element_async(selector)
                if submit_success:
                    await self._human_delay_async(3, 5)
                    self.logger.info("✅ Listing submitted")
                    return True

            self.logger.error("❌ Could not find submit button")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error submitting listing: {e}")
            return False

    def _submit_listing_sync(self) -> bool:
        """Submit the listing (sync)"""
        try:
            # Find and click submit/publish button
            submit_selectors = [
                'button:has-text("Publish")',
                'button:has-text("Submit")',
                'button[aria-label*="Publish" i]',
                'button[type="submit"]'
            ]

            for selector in submit_selectors:
                submit_success = self.browser.click_element_sync(selector)
                if submit_success:
                    self._human_delay_sync(3, 5)
                    self.logger.info("✅ Listing submitted")
                    return True

            self.logger.error("❌ Could not find submit button")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error submitting listing: {e}")
            return False

    # ================== MESSAGE OPERATIONS ==================

    async def get_unread_conversations_async(self) -> List[Dict]:
        """Get list of unread conversations (async)"""
        try:
            self.logger.info("📋 Scanning for unread conversations...")

            conversations = []

            # Navigate to messages if not already there
            if "messages" not in await self.page.url:
                await self.navigate_to_messages_async()

            # Wait for conversations to load
            await self._human_delay_async()

            # Look for conversation elements
            conversation_selectors = [
                '[role="grid"] div[role="row"]',
                '[data-testid="message-thread"]',
                'div[aria-label*="Conversation" i]'
            ]

            for selector in conversation_selectors:
                elements = await self.page.query_selector_all(selector)
                for element in elements[:10]:  # Limit to first 10
                    try:
                        # Check if conversation has unread indicator
                        unread_indicator = await element.query_selector('[aria-label*="unread" i]')
                        if unread_indicator:
                            # Extract conversation info
                            name = await self._extract_conversation_name_async(element)
                            last_message = await self._extract_last_message_async(element)

                            conversation_data = {
                                'name': name,
                                'last_message': last_message,
                                'timestamp': datetime.now(),
                                'element': element
                            }
                            conversations.append(conversation_data)
                    except Exception as e:
                        continue

                if conversations:
                    break

            self.logger.info(f"📋 Found {len(conversations)} unread conversations")
            return conversations

        except Exception as e:
            self.logger.error(f"❌ Error getting unread conversations: {e}")
            return []

    def get_unread_conversations_sync(self) -> List[Dict]:
        """Get list of unread conversations (sync)"""
        try:
            self.logger.info("📋 Scanning for unread conversations...")

            conversations = []

            # Navigate to messages if not already there
            if "messages" not in self.page.url:
                self.navigate_to_messages_sync()

            # Wait for conversations to load
            self._human_delay_sync()

            # Look for conversation elements
            conversation_selectors = [
                '[role="grid"] div[role="row"]',
                '[data-testid="message-thread"]',
                'div[aria-label*="Conversation" i]'
            ]

            for selector in conversation_selectors:
                elements = self.page.query_selector_all(selector)
                for element in elements[:10]:  # Limit to first 10
                    try:
                        # Check if conversation has unread indicator
                        unread_indicator = element.query_selector('[aria-label*="unread" i]')
                        if unread_indicator:
                            # Extract conversation info
                            name = self._extract_conversation_name_sync(element)
                            last_message = self._extract_last_message_sync(element)

                            conversation_data = {
                                'name': name,
                                'last_message': last_message,
                                'timestamp': datetime.now(),
                                'element': element
                            }
                            conversations.append(conversation_data)
                    except Exception as e:
                        continue

                if conversations:
                    break

            self.logger.info(f"📋 Found {len(conversations)} unread conversations")
            return conversations

        except Exception as e:
            self.logger.error(f"❌ Error getting unread conversations: {e}")
            return []

    def get_unread_conversations(self) -> List[Dict]:
        """Get unread conversations wrapper for compatibility"""
        if self.async_mode:
            raise RuntimeError("Use get_unread_conversations_async() for async mode")
        return self.get_unread_conversations_sync()

    async def _extract_conversation_name_async(self, element) -> Optional[str]:
        """Extract conversation name from element (async)"""
        try:
            name_selectors = [
                '[data-testid="conversation-name"]',
                'span[dir="auto"]',
                'strong'
            ]

            for selector in name_selectors:
                name_element = await element.query_selector(selector)
                if name_element:
                    name = await name_element.inner_text()
                    if name and name.strip():
                        return name.strip()
            return None
        except:
            return None

    def _extract_conversation_name_sync(self, element) -> Optional[str]:
        """Extract conversation name from element (sync)"""
        try:
            name_selectors = [
                '[data-testid="conversation-name"]',
                'span[dir="auto"]',
                'strong'
            ]

            for selector in name_selectors:
                name_element = element.query_selector(selector)
                if name_element:
                    name = name_element.inner_text()
                    if name and name.strip():
                        return name.strip()
            return None
        except:
            return None

    async def _extract_last_message_async(self, element) -> Optional[str]:
        """Extract last message from conversation element (async)"""
        try:
            message_selectors = [
                '[data-testid="last-message"]',
                'span[dir="auto"]:last-child',
                'div:last-child span'
            ]

            for selector in message_selectors:
                message_element = await element.query_selector(selector)
                if message_element:
                    message = await message_element.inner_text()
                    if message and message.strip():
                        return message.strip()
            return None
        except:
            return None

    def _extract_last_message_sync(self, element) -> Optional[str]:
        """Extract last message from conversation element (sync)"""
        try:
            message_selectors = [
                '[data-testid="last-message"]',
                'span[dir="auto"]:last-child',
                'div:last-child span'
            ]

            for selector in message_selectors:
                message_element = element.query_selector(selector)
                if message_element:
                    message = message_element.inner_text()
                    if message and message.strip():
                        return message.strip()
            return None
        except:
            return None

    async def send_message_async(self, message_text: str) -> bool:
        """Send a message in the currently open conversation (async)"""
        try:
            self.logger.info(f"📤 Sending message: {message_text[:50]}...")

            # Find message input field
            input_selectors = [
                'div[role="textbox"][aria-label*="Message" i]',
                'div[contenteditable="true"]',
                'textarea[placeholder*="message" i]'
            ]

            message_sent = False
            for selector in input_selectors:
                try:
                    # Type message
                    type_success = await self.browser.type_text_async(selector, message_text)
                    if type_success:
                        await self._human_delay_async()

                        # Send message (Enter key)
                        await self.page.keyboard.press('Enter')
                        await self._human_delay_async()

                        self.logger.info("✅ Message sent successfully")
                        self.messages_sent += 1
                        log_facebook_action("send_message", self.account.get_masked_email(), True, f"Sent: {message_text[:30]}...")
                        message_sent = True
                        break
                except:
                    continue

            if not message_sent:
                self.logger.error("❌ Could not find message input field")
                return False

            return True

        except Exception as e:
            self.logger.error(f"❌ Error sending message: {e}")
            self.errors_count += 1
            return False

    def send_message_sync(self, message_text: str) -> bool:
        """Send a message in the currently open conversation (sync)"""
        try:
            self.logger.info(f"📤 Sending message: {message_text[:50]}...")

            # Find message input field
            input_selectors = [
                'div[role="textbox"][aria-label*="Message" i]',
                'div[contenteditable="true"]',
                'textarea[placeholder*="message" i]'
            ]

            message_sent = False
            for selector in input_selectors:
                try:
                    # Type message
                    type_success = self.browser.type_text_sync(selector, message_text)
                    if type_success:
                        self._human_delay_sync()

                        # Send message (Enter key)
                        self.page.keyboard.press('Enter')
                        self._human_delay_sync()

                        self.logger.info("✅ Message sent successfully")
                        self.messages_sent += 1
                        log_facebook_action("send_message", self.account.get_masked_email(), True, f"Sent: {message_text[:30]}...")
                        message_sent = True
                        break
                except:
                    continue

            if not message_sent:
                self.logger.error("❌ Could not find message input field")
                return False

            return True

        except Exception as e:
            self.logger.error(f"❌ Error sending message: {e}")
            self.errors_count += 1
            return False

    def send_message(self, message_text: str) -> bool:
        """Send message wrapper for compatibility"""
        if self.async_mode:
            raise RuntimeError("Use send_message_async() for async mode")
        return self.send_message_sync(message_text)

    async def open_conversation_async(self, conversation_data: Dict) -> bool:
        """Open a specific conversation (async)"""
        try:
            if 'element' in conversation_data:
                # Click on the conversation element
                await conversation_data['element'].click()
                await self._human_delay_async()
                self.logger.info(f"✅ Opened conversation with {conversation_data.get('name', 'Unknown')}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Error opening conversation: {e}")
            return False

    def open_conversation_sync(self, conversation_data: Dict) -> bool:
        """Open a specific conversation (sync)"""
        try:
            if 'element' in conversation_data:
                # Click on the conversation element
                conversation_data['element'].click()
                self._human_delay_sync()
                self.logger.info(f"✅ Opened conversation with {conversation_data.get('name', 'Unknown')}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Error opening conversation: {e}")
            return False

    # ================== AI INTEGRATION AND AUTOMATION ==================

    def set_ai_service(self, ai_service):
        """Set AI service for automated responses"""
        self.ai_service = ai_service
        self.logger.info("✅ AI service configured")

    async def run_message_monitoring_cycle_async(self, duration_minutes: int = 30) -> Dict[str, Any]:
        """Run automated message monitoring and response cycle (async)"""
        try:
            self.logger.info(f"🤖 Starting message monitoring cycle for {duration_minutes} minutes...")

            stats = {
                'cycle_start': datetime.now(),
                'messages_found': 0,
                'responses_sent': 0,
                'conversations_handled': 0,
                'errors': 0
            }

            end_time = datetime.now() + timedelta(minutes=duration_minutes)

            while datetime.now() < end_time:
                try:
                    # Get unread conversations
                    conversations = await self.get_unread_conversations_async()
                    stats['messages_found'] += len(conversations)

                    for conversation in conversations:
                        try:
                            # Open conversation
                            if await self.open_conversation_async(conversation):
                                stats['conversations_handled'] += 1

                                # Generate AI response if AI service is available
                                if self.ai_service and self.auto_reply_enabled:
                                    response = await self._generate_ai_response_async(conversation)
                                    if response:
                                        if await self.send_message_async(response):
                                            stats['responses_sent'] += 1

                                await self._human_delay_async(2, 4)

                        except Exception as e:
                            stats['errors'] += 1
                            self.logger.error(f"Error handling conversation: {e}")

                    # Wait before next check
                    await asyncio.sleep(getattr(Config, 'MESSAGE_CHECK_INTERVAL', 60))

                except Exception as e:
                    stats['errors'] += 1
                    self.logger.error(f"Error in monitoring cycle: {e}")
                    await asyncio.sleep(30)

            stats['cycle_end'] = datetime.now()
            stats['duration'] = (stats['cycle_end'] - stats['cycle_start']).total_seconds() / 60

            self.logger.info(f"📊 Message monitoring cycle completed: {stats}")
            return stats

        except Exception as e:
            self.logger.error(f"❌ Error in message monitoring cycle: {e}")
            return {}

    def run_message_monitoring_cycle_sync(self, duration_minutes: int = 30) -> Dict[str, Any]:
        """Run automated message monitoring and response cycle (sync)"""
        try:
            self.logger.info(f"🤖 Starting message monitoring cycle for {duration_minutes} minutes...")

            stats = {
                'cycle_start': datetime.now(),
                'messages_found': 0,
                'responses_sent': 0,
                'conversations_handled': 0,
                'errors': 0
            }

            end_time = datetime.now() + timedelta(minutes=duration_minutes)

            while datetime.now() < end_time:
                try:
                    # Get unread conversations
                    conversations = self.get_unread_conversations_sync()
                    stats['messages_found'] += len(conversations)

                    for conversation in conversations:
                        try:
                            # Open conversation
                            if self.open_conversation_sync(conversation):
                                stats['conversations_handled'] += 1

                                # Generate AI response if AI service is available
                                if self.ai_service and self.auto_reply_enabled:
                                    response = self._generate_ai_response_sync(conversation)
                                    if response:
                                        if self.send_message_sync(response):
                                            stats['responses_sent'] += 1

                                self._human_delay_sync(2, 4)

                        except Exception as e:
                            stats['errors'] += 1
                            self.logger.error(f"Error handling conversation: {e}")

                    # Wait before next check
                    time.sleep(getattr(Config, 'MESSAGE_CHECK_INTERVAL', 60))

                except Exception as e:
                    stats['errors'] += 1
                    self.logger.error(f"Error in monitoring cycle: {e}")
                    time.sleep(30)

            stats['cycle_end'] = datetime.now()
            stats['duration'] = (stats['cycle_end'] - stats['cycle_start']).total_seconds() / 60

            self.logger.info(f"📊 Message monitoring cycle completed: {stats}")
            return stats

        except Exception as e:
            self.logger.error(f"❌ Error in message monitoring cycle: {e}")
            return {}

    def run_message_monitoring_cycle(self, duration_minutes: int = 30) -> Dict[str, Any]:
        """Run message monitoring cycle wrapper for compatibility"""
        if self.async_mode:
            raise RuntimeError("Use run_message_monitoring_cycle_async() for async mode")
        return self.run_message_monitoring_cycle_sync(duration_minutes)

    async def _generate_ai_response_async(self, conversation: Dict) -> Optional[str]:
        """Generate AI response for conversation (async)"""
        try:
            if not self.ai_service:
                return None

            # Get conversation context
            context = {
                'customer_name': conversation.get('name', 'Customer'),
                'last_message': conversation.get('last_message', ''),
                'timestamp': conversation.get('timestamp', datetime.now())
            }

            # Generate response using AI service
            if hasattr(self.ai_service, 'generate_response_async'):
                response = await self.ai_service.generate_response_async(context)
            else:
                response = self.ai_service.generate_response(context)

            return response

        except Exception as e:
            self.logger.error(f"Error generating AI response: {e}")
            return None

    def _generate_ai_response_sync(self, conversation: Dict) -> Optional[str]:
        """Generate AI response for conversation (sync)"""
        try:
            if not self.ai_service:
                return None

            # Get conversation context
            context = {
                'customer_name': conversation.get('name', 'Customer'),
                'last_message': conversation.get('last_message', ''),
                'timestamp': conversation.get('timestamp', datetime.now())
            }

            # Generate response using AI service
            response = self.ai_service.generate_response(context)
            return response

        except Exception as e:
            self.logger.error(f"Error generating AI response: {e}")
            return None

    async def start_automated_customer_service_async(self, ai_service, products: List[Product], duration_minutes: int = 60):
        """Start fully automated customer service with AI responses (async)"""
        try:
            self.set_ai_service(ai_service)
            self.auto_reply_enabled = True

            self.logger.info(f"🤖 Starting automated customer service for {duration_minutes} minutes...")

            # Run monitoring cycle with AI responses
            stats = await self.run_message_monitoring_cycle_async(duration_minutes)

            self.logger.info(f"📊 Automated customer service completed:")
            self.logger.info(f"   - Conversations handled: {stats.get('conversations_handled', 0)}")
            self.logger.info(f"   - AI responses sent: {stats.get('responses_sent', 0)}")
            self.logger.info(f"   - Total duration: {stats.get('duration', 0):.1f} minutes")

        except KeyboardInterrupt:
            self.logger.info("\n⏹️ Automated customer service stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Error in automated customer service: {e}")

    def start_automated_customer_service_sync(self, ai_service, products: List[Product], duration_minutes: int = 60):
        """Start fully automated customer service with AI responses (sync)"""
        try:
            self.set_ai_service(ai_service)
            self.auto_reply_enabled = True

            self.logger.info(f"🤖 Starting automated customer service for {duration_minutes} minutes...")

            # Run monitoring cycle with AI responses
            stats = self.run_message_monitoring_cycle_sync(duration_minutes)

            self.logger.info(f"📊 Automated customer service completed:")
            self.logger.info(f"   - Conversations handled: {stats.get('conversations_handled', 0)}")
            self.logger.info(f"   - AI responses sent: {stats.get('responses_sent', 0)}")
            self.logger.info(f"   - Total duration: {stats.get('duration', 0):.1f} minutes")

        except KeyboardInterrupt:
            self.logger.info("\n⏹️ Automated customer service stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Error in automated customer service: {e}")

    def start_automated_customer_service(self, ai_service, products: List[Product], duration_minutes: int = 60):
        """Start automated customer service wrapper for compatibility"""
        if self.async_mode:
            raise RuntimeError("Use start_automated_customer_service_async() for async mode")
        return self.start_automated_customer_service_sync(ai_service, products, duration_minutes)

    # ================== UTILITY AND HELPER METHODS ==================

    async def _human_delay_async(self, min_delay: float = None, max_delay: float = None):
        """Add human-like delay (async)"""
        min_delay = min_delay or self.human_delay_min
        max_delay = max_delay or self.human_delay_max
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)

    def _human_delay_sync(self, min_delay: float = None, max_delay: float = None):
        """Add human-like delay (sync)"""
        min_delay = min_delay or self.human_delay_min
        max_delay = max_delay or self.human_delay_max
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def get_session_info(self) -> Dict[str, Any]:
        """Get comprehensive session information"""
        current_time = time.time()
        session_duration = current_time - self.start_time if self.start_time else 0

        return {
            'account': self.account.get_masked_email(),
            'session_duration': session_duration,
            'is_logged_in': self.is_logged_in,
            'current_url': self.current_url,
            'total_actions': self.total_actions,
            'requests_made': self.requests_made,
            'requests_successful': self.requests_successful,
            'requests_failed': self.requests_failed,
            'listings_created': self.listings_created,
            'listings_failed': self.listings_failed,
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'conversations_handled': self.conversations_handled,
            'errors_count': self.errors_count,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'average_page_load_time': sum(self.page_load_times) / len(self.page_load_times) if self.page_load_times else 0
        }

    async def take_screenshot_async(self, filename: Optional[str] = None) -> str:
        """Take screenshot for debugging (async)"""
        if self.browser and self.screenshot_enabled:
            return await self.browser.take_screenshot_async(filename)
        return ""

    def take_screenshot_sync(self, filename: Optional[str] = None) -> str:
        """Take screenshot for debugging (sync)"""
        if self.browser and self.screenshot_enabled:
            return self.browser.take_screenshot_sync(filename)
        return ""

    def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Take screenshot wrapper for compatibility"""
        if self.async_mode:
            raise RuntimeError("Use take_screenshot_async() for async mode")
        return self.take_screenshot_sync(filename)

    # ================== SESSION MANAGEMENT ==================

    async def end_session_async(self):
        """End the Facebook session and cleanup (async)"""
        try:
            if self.browser:
                # Take final screenshot if enabled
                if self.screenshot_enabled and self.is_logged_in:
                    await self.take_screenshot_async("session_end")

                # Cleanup browser
                await self.browser.cleanup_async()
                self.browser = None

            # Log session info
            session_info = self.get_session_info()
            self.logger.info(f"Session ended: {session_info}")

            log_facebook_action("session_end", self.account.get_masked_email(), True,
                               f"Actions: {self.total_actions}, Duration: {session_info.get('session_duration', 0):.2f}s")

            # Reset state
            self.is_logged_in = False
            self.logged_in = False
            self.current_url = ""
            self.session_start_time = None

            self.logger.info("Facebook session ended successfully")

        except Exception as e:
            self.logger.error(f"Session cleanup error: {e}")

    def end_session_sync(self):
        """End the Facebook session and cleanup (sync)"""
        try:
            if self.browser:
                # Take final screenshot if enabled
                if self.screenshot_enabled and self.is_logged_in:
                    self.take_screenshot_sync("session_end")

                # Cleanup browser
                self.browser.cleanup_sync()
                self.browser = None

            # Log session info
            session_info = self.get_session_info()
            self.logger.info(f"Session ended: {session_info}")

            log_facebook_action("session_end", self.account.get_masked_email(), True,
                               f"Actions: {self.total_actions}, Duration: {session_info.get('session_duration', 0):.2f}s")

            # Reset state
            self.is_logged_in = False
            self.logged_in = False
            self.current_url = ""
            self.session_start_time = None

            self.logger.info("Facebook session ended successfully")

        except Exception as e:
            self.logger.error(f"Session cleanup error: {e}")

    def end_session(self):
        """End session wrapper for compatibility"""
        if self.async_mode:
            raise RuntimeError("Use end_session_async() for async mode")
        return self.end_session_sync()

    # ================== CONTEXT MANAGERS ==================

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize_async()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.end_session_async()

    def __enter__(self):
        """Context manager entry"""
        if self.async_mode:
            raise RuntimeError("Use async context manager for async mode")
        self.initialize_sync()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.end_session_sync()


# ================== CONVENIENCE FUNCTIONS FOR COMPATIBILITY ==================

def create_facebook_bot(account: Account, headless: bool = None, async_mode: bool = True) -> FacebookBotPlaywright:
    """
    Create and initialize a Facebook bot for an account

    Args:
        account: Account object with Facebook credentials
        headless: Run in headless mode
        async_mode: Use async Playwright (recommended)

    Returns:
        Configured FacebookBotPlaywright instance
    """
    return FacebookBotPlaywright(account, headless, async_mode)


async def validate_facebook_login_async(account: Account, headless: bool = False) -> bool:
    """
    Validate Facebook login for an account (async)

    Args:
        account: Account to test login for
        headless: Run in headless mode

    Returns:
        True if login successful, False otherwise
    """
    try:
        async with create_facebook_bot(account, headless, async_mode=True) as bot:
            login_success = await bot.login_async()
            if login_success:
                return await bot.navigate_to_marketplace_async()
            return False
    except Exception as e:
        logger = get_logger("facebook_login_test")
        logger.error(f"Login test failed for {account.get_masked_email()}: {e}")
        return False


def validate_facebook_login_sync(account: Account, headless: bool = False) -> bool:
    """
    Validate Facebook login for an account (sync)

    Args:
        account: Account to test login for
        headless: Run in headless mode

    Returns:
        True if login successful, False otherwise
    """
    try:
        with create_facebook_bot(account, headless, async_mode=False) as bot:
            login_success = bot.login_sync()
            if login_success:
                return bot.navigate_to_marketplace_sync()
            return False
    except Exception as e:
        logger = get_logger("facebook_login_test")
        logger.error(f"Login test failed for {account.get_masked_email()}: {e}")
        return False


def validate_facebook_login(account: Account, headless: bool = False, async_mode: bool = True) -> bool:
    """
    Validate Facebook login wrapper for compatibility

    Args:
        account: Account to test login for
        headless: Run in headless mode
        async_mode: Use async version

    Returns:
        True if login successful, False otherwise
    """
    if async_mode:
        import asyncio
        return asyncio.run(validate_facebook_login_async(account, headless))
    else:
        return validate_facebook_login_sync(account, headless)


# ================== ADDITIONAL MARKETPLACE METHODS ==================

class FacebookBotMarketplaceExtension:
    """
    Additional marketplace methods for FacebookBotPlaywright
    These methods extend the core functionality with marketplace-specific features
    """

    async def verify_listing_published_async(self, product_title: str) -> bool:
        """
        Verify that a listing was successfully published (async)

        Args:
            product_title: Title of the product listing to verify

        Returns:
            True if listing is found and published, False otherwise
        """
        try:
            self.logger.info(f"🔍 Verifying listing publication: {product_title}")

            # Navigate to user's marketplace listings
            my_listings_url = "https://www.facebook.com/marketplace/you/selling"
            success = await self.browser.navigate_to_async(my_listings_url)

            if not success:
                return False

            await self._human_delay_async(3, 5)

            # Search for the listing by title
            listing_found = False
            try:
                # Look for listings with matching title
                listing_elements = await self.page.query_selector_all('[aria-label*="' + product_title + '"]')
                if listing_elements:
                    listing_found = True
                else:
                    # Try alternative search methods
                    text_elements = await self.page.query_selector_all('text=' + product_title)
                    if text_elements:
                        listing_found = True

                if listing_found:
                    self.logger.info("✅ Listing verified as published")
                    return True
                else:
                    self.logger.warning("⚠️ Could not verify listing publication")
                    return False

            except Exception as e:
                self.logger.warning(f"⚠️ Listing verification error: {e}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error verifying listing: {e}")
            return False

    def verify_listing_published_sync(self, product_title: str) -> bool:
        """
        Verify that a listing was successfully published (sync)

        Args:
            product_title: Title of the product listing to verify

        Returns:
            True if listing is found and published, False otherwise
        """
        try:
            self.logger.info(f"🔍 Verifying listing publication: {product_title}")

            # Navigate to user's marketplace listings
            my_listings_url = "https://www.facebook.com/marketplace/you/selling"
            success = self.browser.navigate_to_sync(my_listings_url)

            if not success:
                return False

            self._human_delay_sync(3, 5)

            # Search for the listing by title
            listing_found = False
            try:
                # Look for listings with matching title
                listing_elements = self.page.query_selector_all('[aria-label*="' + product_title + '"]')
                if listing_elements:
                    listing_found = True
                else:
                    # Try alternative search methods
                    text_elements = self.page.query_selector_all('text=' + product_title)
                    if text_elements:
                        listing_found = True

                if listing_found:
                    self.logger.info("✅ Listing verified as published")
                    return True
                else:
                    self.logger.warning("⚠️ Could not verify listing publication")
                    return False

            except Exception as e:
                self.logger.warning(f"⚠️ Listing verification error: {e}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error verifying listing: {e}")
            return False

    async def get_listing_url_async(self, product_title: str) -> Optional[str]:
        """
        Get the URL of a published listing (async)

        Args:
            product_title: Title of the product listing

        Returns:
            URL of the listing or None if not found
        """
        try:
            self.logger.info(f"🔗 Getting listing URL for: {product_title}")

            # Verify listing exists first
            if await self.verify_listing_published_async(product_title):
                # Try to extract URL from current page or listing element
                current_url = self.page.url
                if "marketplace" in current_url and "item" in current_url:
                    self.logger.info(f"📋 Listing URL: {current_url}")
                    return current_url

            return None

        except Exception as e:
            self.logger.warning(f"⚠️ Error getting listing URL: {e}")
            return None

    def get_listing_url_sync(self, product_title: str) -> Optional[str]:
        """
        Get the URL of a published listing (sync)

        Args:
            product_title: Title of the product listing

        Returns:
            URL of the listing or None if not found
        """
        try:
            self.logger.info(f"🔗 Getting listing URL for: {product_title}")

            # Verify listing exists first
            if self.verify_listing_published_sync(product_title):
                # Try to extract URL from current page or listing element
                current_url = self.page.url
                if "marketplace" in current_url and "item" in current_url:
                    self.logger.info(f"📋 Listing URL: {current_url}")
                    return current_url

            return None

        except Exception as e:
            self.logger.warning(f"⚠️ Error getting listing URL: {e}")
            return None

    async def update_listing_price_async(self, product_title: str, new_price: float) -> bool:
        """
        Update the price of an existing listing (async)

        Args:
            product_title: Title of the listing to update
            new_price: New price for the listing

        Returns:
            True if price updated successfully, False otherwise
        """
        try:
            self.logger.info(f"💰 Updating listing price: {product_title} -> ${new_price}")

            # Navigate to user's listings
            my_listings_url = "https://www.facebook.com/marketplace/you/selling"
            if not await self.browser.navigate_to_async(my_listings_url):
                return False

            await self._human_delay_async()

            # Find the specific listing
            listing_element = await self.page.query_selector(f'[aria-label*="{product_title}"]')
            if not listing_element:
                self.logger.error("❌ Listing not found for price update")
                return False

            # Click on the listing to open it
            await listing_element.click()
            await self._human_delay_async()

            # Look for edit button
            edit_button = await self.page.query_selector('button:has-text("Edit")')
            if edit_button:
                await edit_button.click()
                await self._human_delay_async()

                # Update price field
                price_field = await self.page.query_selector('input[aria-label*="Price" i]')
                if price_field:
                    await price_field.fill(str(new_price))
                    await self._human_delay_async()

                    # Save changes
                    save_button = await self.page.query_selector('button:has-text("Save")')
                    if save_button:
                        await save_button.click()
                        await self._human_delay_async()

                        self.listings_updated += 1
                        self.logger.info(f"✅ Price updated to ${new_price}")
                        return True

            self.logger.error("❌ Could not update listing price")
            return False

        except Exception as e:
            self.logger.error(f"❌ Error updating listing price: {e}")
            return False

    def update_listing_price_sync(self, product_title: str, new_price: float) -> bool:
        """
        Update the price of an existing listing (sync)

        Args:
            product_title: Title of the listing to update
            new_price: New price for the listing

        Returns:
            True if price updated successfully, False otherwise
        """
        try:
            self.logger.info(f"💰 Updating listing price: {product_title} -> ${new_price}")

            # Navigate to user's listings
            my_listings_url = "https://www.facebook.com/marketplace/you/selling"
            if not self.browser.navigate_to_sync(my_listings_url):
                return False

            self._human_delay_sync()

            # Find the specific listing
            listing_element = self.page.query_selector(f'[aria-label*="{product_title}"]')
            if not listing_element:
                self.logger.error("❌ Listing not found for price update")
                return False

            # Click on the listing to open it
            listing_element.click()
            self._human_delay_sync()

            # Look for edit button
            edit_button = self.page.query_selector('button:has-text("Edit")')
            if edit_button:
                edit_button.click()
                self._human_delay_sync()

                # Update price field
                price_field = self.page.query_selector('input[aria-label*="Price" i]')
                if price_field:
                    price_field.fill(str(new_price))
                    self._human_delay_sync()

                    # Save changes
                    save_button = self.page.query_selector('button:has-text("Save")')
                    if save_button:
                        save_button.click()
                        self._human_delay_sync()

                        self.listings_updated += 1
                        self.logger.info(f"✅ Price updated to ${new_price}")
                        return True

            self.logger.error("❌ Could not update listing price")
            return False

        except Exception as e:
            self.logger.error(f"❌ Error updating listing price: {e}")
            return False


# Extend the main FacebookBotPlaywright class with marketplace methods
for method_name in dir(FacebookBotMarketplaceExtension):
    if not method_name.startswith('_'):
        method = getattr(FacebookBotMarketplaceExtension, method_name)
        if callable(method):
            setattr(FacebookBotPlaywright, method_name, method)


# ================== EXAMPLE USAGE AND TESTING ==================

if __name__ == "__main__":
    """
    Example usage of the FacebookBotPlaywright
    """
    import asyncio
    from models.account import Account
    from models.product import Product

    async def main():
        """Example async usage"""
        # Create account
        account = Account(
            email="your_email@example.com",
            password="your_password"
        )

        # Create bot
        async with create_facebook_bot(account, headless=False, async_mode=True) as bot:
            # Login
            if await bot.login_async():
                print("✅ Login successful!")

                # Navigate to marketplace
                if await bot.navigate_to_marketplace_async():
                    print("✅ Marketplace navigation successful!")

                # Create a test listing
                test_product = Product(
                    title="Test Product",
                    price=100.0,
                    description="This is a test product",
                    category="Electronics"
                )

                if await bot.create_marketplace_listing_async(test_product):
                    print("✅ Listing created successfully!")

                # Check for messages
                if await bot.navigate_to_messages_async():
                    conversations = await bot.get_unread_conversations_async()
                    print(f"📬 Found {len(conversations)} unread conversations")

                    # Demo AI customer service
                    if conversations:
                        print("🤖 Starting AI customer service demo...")
                        # Note: You would need to implement and pass a real AI service
                        # await bot.start_automated_customer_service_async(ai_service, [test_product], 5)

                # Get session info
                session_info = bot.get_session_info()
                print(f"📊 Session info: {session_info}")
            else:
                print("❌ Login failed!")

    def sync_main():
        """Example sync usage"""
        # Create account
        account = Account(
            email="your_email@example.com",
            password="your_password"
        )

        # Create bot
        with create_facebook_bot(account, headless=False, async_mode=False) as bot:
            # Login
            if bot.login_sync():
                print("✅ Login successful!")

                # Navigate to marketplace
                if bot.navigate_to_marketplace_sync():
                    print("✅ Marketplace navigation successful!")

                # Navigate to messages
                if bot.navigate_to_messages_sync():
                    conversations = bot.get_unread_conversations_sync()
                    print(f"📬 Found {len(conversations)} unread conversations")

                # Get session info
                session_info = bot.get_session_info()
                print(f"📊 Session info: {session_info}")
            else:
                print("❌ Login failed!")

    # Choose which example to run
    print("Facebook Bot Playwright - Example Usage")
    print("1. Async example (recommended)")
    print("2. Sync example")

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        asyncio.run(main())
    else:
        sync_main()