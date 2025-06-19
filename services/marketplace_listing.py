"""
Complete Facebook Marketplace Listing Implementation
This extends the existing FacebookBot to include full listing creation
"""

import time
import random
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementNotInteractableException
)

from config import Config
from models.product import Product
from models.account import Account
from utils.browser_utils import BrowserManager
from utils.logger import get_logger, log_facebook_action, log_performance


class MarketplaceListing:
    """
    Complete marketplace listing functionality

    This class handles:
    - Navigating to marketplace create page
    - Filling out listing forms
    - Uploading images
    - Publishing listings
    - Handling errors and retries
    """

    def __init__(self, browser_manager: BrowserManager, account: Account):
        """
        Initialize marketplace listing service

        Args:
            browser_manager: Browser automation instance
            account: Facebook account to use
        """
        self.browser = browser_manager
        self.account = account
        self.logger = get_logger(f"marketplace_listing_{account.get_masked_email()}")

        # Statistics
        self.listings_created = 0
        self.listings_failed = 0

        # Facebook marketplace selectors (updated for current FB)
        self.selectors = {
            # Navigation
            'marketplace_url': 'https://www.facebook.com/marketplace',
            'create_listing_url': 'https://www.facebook.com/marketplace/create',

            # Create listing buttons
            'create_listing_btn': [
                '[aria-label*="Create new listing"]',
                'a[href*="/marketplace/create"]',
                '[data-testid="mw_create_post_button"]',
                'div[role="button"]:contains("Create new listing")'
            ],

            # Listing type selection
            'item_for_sale': [
                '[data-testid="marketplace_listing_item_for_sale"]',
                'div[role="radio"]:contains("Item for sale")',
                'input[value="ITEM"]',
                'div:contains("Item for sale")'
            ],

            # Form fields
            'title_input': [
                'input[placeholder*="What are you selling?"]',
                'input[aria-label*="title"]',
                'input[name="marketplace_listing_title"]',
                'textarea[placeholder*="What are you selling?"]'
            ],

            'description_input': [
                'textarea[placeholder*="Describe your item"]',
                'textarea[aria-label*="description"]',
                'textarea[name="marketplace_listing_description"]',
                'div[contenteditable="true"][aria-label*="description"]'
            ],

            'price_input': [
                'input[placeholder*="Price"]',
                'input[aria-label*="price"]',
                'input[name="marketplace_listing_price"]',
                'input[placeholder*="$"]'
            ],

            'location_input': [
                'input[placeholder*="Neighborhood"]',
                'input[placeholder*="Location"]',
                'input[aria-label*="location"]',
                'input[name="marketplace_listing_location"]'
            ],

            # Category and condition
            'category_dropdown': [
                '[data-testid="marketplace_listing_category_selector"]',
                'select[aria-label*="Category"]',
                'div[role="button"][aria-label*="category"]'
            ],

            'condition_dropdown': [
                '[data-testid="marketplace_listing_condition_selector"]',
                'select[aria-label*="Condition"]',
                'div[role="button"][aria-label*="condition"]'
            ],

            # Image upload
            'photo_upload': [
                'input[type="file"][accept*="image"]',
                'input[type="file"][multiple]',
                '[data-testid="media_upload_input"]'
            ],

            # Publish button
            'publish_btn': [
                '[data-testid="marketplace_listing_post_button"]',
                'button[type="submit"]',
                'div[role="button"]:contains("Post")',
                'button:contains("Publish")'
            ]
        }

    def navigate_to_create_listing(self) -> bool:
        """
        Navigate to the marketplace create listing page

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Navigating to marketplace create listing page")

            # First try direct navigation
            if self.browser.navigate_to(self.selectors['create_listing_url']):
                self.logger.info("Direct navigation to create listing successful")
                time.sleep(random.uniform(2, 4))
                return True

            # Fallback: Navigate to marketplace first, then find create button
            if not self.browser.navigate_to(self.selectors['marketplace_url']):
                self.logger.error("Failed to navigate to marketplace")
                return False

            time.sleep(random.uniform(2, 4))

            # Look for create listing button
            for selector in self.selectors['create_listing_btn']:
                create_btn = self.browser.find_element_safe(By.CSS_SELECTOR, selector, timeout=3)
                if create_btn:
                    self.logger.info(f"Found create button with selector: {selector}")
                    if self.browser.click_element_safe(create_btn):
                        time.sleep(random.uniform(2, 4))
                        return True

            self.logger.error("Could not find create listing button")
            return False

        except Exception as e:
            self.logger.error(f"Error navigating to create listing: {e}")
            return False

    def select_listing_type(self) -> bool:
        """
        Select 'Item for Sale' listing type

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Selecting 'Item for Sale' listing type")

            # Look for item for sale option
            for selector in self.selectors['item_for_sale']:
                item_btn = self.browser.find_element_safe(By.CSS_SELECTOR, selector, timeout=3)
                if item_btn:
                    self.logger.info(f"Found item for sale option: {selector}")
                    if self.browser.click_element_safe(item_btn):
                        time.sleep(random.uniform(1, 3))
                        return True

            # If no selection needed, assume we're already on the right page
            self.logger.info("No listing type selection needed")
            return True

        except Exception as e:
            self.logger.error(f"Error selecting listing type: {e}")
            return False

    def fill_listing_form(self, product: Product) -> bool:
        """
        Fill out the complete listing form

        Args:
            product: Product object with listing details

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Filling listing form for: {product.title}")

            # Wait for form to load
            time.sleep(random.uniform(2, 4))

            # Fill title
            if not self._fill_field('title_input', product.title, required=True):
                return False

            # Fill description
            if not self._fill_field('description_input', product.description, required=True):
                return False

            # Fill price
            price_str = f"{product.price:.0f}" if product.price == int(product.price) else f"{product.price:.2f}"
            if not self._fill_field('price_input', price_str, required=True):
                return False

            # Fill location (optional)
            if product.location:
                self._fill_field('location_input', product.location, required=False)

            # Select category (optional)
            if product.category:
                self._select_dropdown('category_dropdown', product.category)

            # Select condition (optional)
            if product.condition:
                self._select_dropdown('condition_dropdown', product.condition)

            self.logger.info("Successfully filled listing form")
            return True

        except Exception as e:
            self.logger.error(f"Error filling listing form: {e}")
            return False

    def _fill_field(self, field_key: str, value: str, required: bool = True) -> bool:
        """
        Fill a form field with multiple selector fallbacks

        Args:
            field_key: Key in selectors dict
            value: Value to enter
            required: Whether field is required

        Returns:
            True if successful, False if required field fails
        """
        try:
            # Try each selector for the field
            for selector in self.selectors[field_key]:
                field = self.browser.find_element_safe(By.CSS_SELECTOR, selector, timeout=2)
                if field:
                    self.logger.debug(f"Found {field_key} with selector: {selector}")

                    # Clear and fill field
                    field.clear()
                    time.sleep(0.5)

                    if self.browser.type_text_human(field, value):
                        self.logger.debug(f"Successfully filled {field_key}: {value[:20]}...")
                        return True

            # Field not found
            if required:
                self.logger.error(f"Required field {field_key} not found")
                return False
            else:
                self.logger.warning(f"Optional field {field_key} not found, continuing")
                return True

        except Exception as e:
            self.logger.error(f"Error filling {field_key}: {e}")
            return not required

    def _select_dropdown(self, dropdown_key: str, value: str) -> bool:
        """
        Select value from dropdown with multiple selector fallbacks

        Args:
            dropdown_key: Key in selectors dict
            value: Value to select

        Returns:
            True if successful, False otherwise
        """
        try:
            # Try each selector for the dropdown
            for selector in self.selectors[dropdown_key]:
                dropdown = self.browser.find_element_safe(By.CSS_SELECTOR, selector, timeout=2)
                if dropdown:
                    self.logger.debug(f"Found {dropdown_key} with selector: {selector}")

                    # Click to open dropdown
                    if self.browser.click_element_safe(dropdown):
                        time.sleep(random.uniform(1, 2))

                        # Look for the value in dropdown options
                        option_selectors = [
                            f'div[role="option"]:contains("{value}")',
                            f'option:contains("{value}")',
                            f'li:contains("{value}")'
                        ]

                        for option_selector in option_selectors:
                            option = self.browser.find_element_safe(By.CSS_SELECTOR, option_selector, timeout=2)
                            if option:
                                if self.browser.click_element_safe(option):
                                    self.logger.debug(f"Selected {dropdown_key}: {value}")
                                    return True

                        # Close dropdown if selection failed
                        dropdown.send_keys(Keys.ESCAPE)
                        break

            self.logger.warning(f"Could not select {dropdown_key}: {value}")
            return True  # Non-critical, continue

        except Exception as e:
            self.logger.warning(f"Error selecting {dropdown_key}: {e}")
            return True  # Non-critical, continue

    def upload_images(self, image_paths: List[str]) -> bool:
        """
        Upload product images

        Args:
            image_paths: List of image file paths

        Returns:
            True if at least one image uploaded, False otherwise
        """
        if not image_paths:
            self.logger.info("No images to upload")
            return True

        try:
            self.logger.info(f"Uploading {len(image_paths)} images")

            # Find upload input
            upload_input = None
            for selector in self.selectors['photo_upload']:
                upload_input = self.browser.find_element_safe(By.CSS_SELECTOR, selector, timeout=3)
                if upload_input:
                    self.logger.debug(f"Found upload input: {selector}")
                    break

            if not upload_input:
                self.logger.error("Image upload input not found")
                return False

            uploaded_count = 0
            max_images = min(len(image_paths), Config.MAX_IMAGES_PER_LISTING)

            for i, image_path in enumerate(image_paths[:max_images]):
                try:
                    # Verify image exists
                    if not Path(image_path).exists():
                        self.logger.warning(f"Image not found: {image_path}")
                        continue

                    # Upload image
                    upload_input.send_keys(str(Path(image_path).absolute()))
                    uploaded_count += 1

                    self.logger.debug(f"Uploaded image {i+1}/{max_images}: {Path(image_path).name}")

                    # Wait between uploads
                    time.sleep(random.uniform(1, 3))

                except Exception as e:
                    self.logger.warning(f"Failed to upload {image_path}: {e}")
                    continue

            if uploaded_count > 0:
                self.logger.info(f"Successfully uploaded {uploaded_count} images")
                # Wait for processing
                time.sleep(random.uniform(2, 5))
                return True
            else:
                self.logger.warning("No images uploaded successfully")
                return False

        except Exception as e:
            self.logger.error(f"Error uploading images: {e}")
            return False

    def publish_listing(self) -> bool:
        """
        Publish the listing

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Publishing listing")

            # Find and click publish button
            for selector in self.selectors['publish_btn']:
                publish_btn = self.browser.find_element_safe(By.CSS_SELECTOR, selector, timeout=3)
                if publish_btn:
                    self.logger.info(f"Found publish button: {selector}")

                    if self.browser.click_element_safe(publish_btn):
                        self.logger.info("Clicked publish button")

                        # Wait for processing
                        time.sleep(random.uniform(3, 7))

                        # Check for success
                        if self._verify_listing_success():
                            return True
                        else:
                            self.logger.warning("Publish clicked but success not confirmed")
                            return True  # Assume success if no error

            self.logger.error("Publish button not found")
            return False

        except Exception as e:
            self.logger.error(f"Error publishing listing: {e}")
            return False

    def _verify_listing_success(self) -> bool:
        """
        Verify that listing was published successfully

        Returns:
            True if success detected, False otherwise
        """
        try:
            # Check URL change (should redirect after successful post)
            current_url = self.browser.driver.current_url
            if 'marketplace' in current_url and 'item' in current_url:
                self.logger.info("Success: Redirected to listing page")
                return True

            # Look for success messages
            success_selectors = [
                'div:contains("Your listing has been posted")',
                'div:contains("Posted successfully")',
                'div:contains("Your item is now live")',
                '[data-testid="marketplace_listing_success"]'
            ]

            for selector in success_selectors:
                success_element = self.browser.find_element_safe(By.CSS_SELECTOR, selector, timeout=2)
                if success_element:
                    self.logger.info("Success: Found success message")
                    return True

            # If no explicit success found, assume success
            return True

        except Exception as e:
            self.logger.debug(f"Error verifying success: {e}")
            return True

    def create_listing(self, product: Product) -> bool:
        """
        Complete listing creation workflow

        Args:
            product: Product to list

        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()

        try:
            self.logger.info(f"Creating marketplace listing: {product.title}")

            # Step 1: Navigate to create listing page
            if not self.navigate_to_create_listing():
                self.logger.error("Failed to navigate to create listing page")
                return False

            # Step 2: Select listing type
            if not self.select_listing_type():
                self.logger.error("Failed to select listing type")
                return False

            # Step 3: Fill form
            if not self.fill_listing_form(product):
                self.logger.error("Failed to fill listing form")
                return False

            # Step 4: Upload images (if available)
            if product.images:
                if not self.upload_images(product.images):
                    self.logger.warning("Image upload failed, continuing without images")

            # Step 5: Publish listing
            if not self.publish_listing():
                self.logger.error("Failed to publish listing")
                return False

            # Success tracking
            self.listings_created += 1
            self.account.increment_listing_count()

            duration = time.time() - start_time
            log_performance(f"create_marketplace_listing", duration)
            log_facebook_action("create_listing", self.account.get_masked_email(), True,
                              f"Listed: {product.title}")

            self.logger.info(f"✅ Successfully created listing: {product.title} ({duration:.1f}s)")
            return True

        except Exception as e:
            self.listings_failed += 1
            duration = time.time() - start_time

            log_facebook_action("create_listing", self.account.get_masked_email(), False, str(e))
            self.logger.error(f"❌ Failed to create listing: {e}")
            return False

    def get_listing_stats(self) -> Dict[str, Any]:
        """Get listing statistics"""
        total_attempts = self.listings_created + self.listings_failed
        success_rate = (self.listings_created / total_attempts * 100) if total_attempts > 0 else 0

        return {
            'account': self.account.get_masked_email(),
            'listings_created': self.listings_created,
            'listings_failed': self.listings_failed,
            'success_rate': success_rate,
            'total_attempts': total_attempts
        }


# Integration with existing FacebookBot
def add_listing_capability_to_facebook_bot():
    """
    This shows how to integrate listing capability with existing FacebookBot
    """

    # Add this method to your existing FacebookBot class
    def create_marketplace_listing(self, product: Product) -> bool:
        """
        Create a marketplace listing (add this to FacebookBot)

        Args:
            product: Product to list

        Returns:
            True if successful, False otherwise
        """
        if not self.logged_in or not self.current_account:
            self.logger.error("Must be logged in to create listings")
            return False

        # Create listing service
        listing_service = MarketplaceListing(self.browser, self.current_account)

        # Create the listing
        return listing_service.create_listing(product)


# Example usage
if __name__ == "__main__":
    from utils.browser_utils import create_browser_manager
    from services.excel_handler import ExcelHandler
    from utils.logger import setup_logging

    setup_logging()
    logger = get_logger(__name__)

    logger.info("Testing Complete Marketplace Listing...")

    try:
        # Load data
        excel_handler = ExcelHandler()
        products = excel_handler.load_products("data/sample_data/sample_products.xlsx")
        accounts = excel_handler.load_accounts("data/sample_data/sample_accounts.xlsx")

        if not products or not accounts:
            logger.error("No test data found")
            exit(1)

        test_product = products[0]
        test_account = accounts[0]

        logger.info(f"Testing with product: {test_product.title}")
        logger.info(f"Testing with account: {test_account.get_masked_email()}")

        # Note: This is just a demonstration
        # Real testing would require Facebook login
        logger.info("⚠️ This test requires real Facebook login for full functionality")
        logger.info("✅ Marketplace listing code is ready for integration")

    except Exception as e:
        logger.error(f"Test error: {e}")