#!/usr/bin/env python3
"""
Phase 3: Complete Automated Listing Implementation
This script implements the marketplace listing functionality and integrates with your working AI system.
"""

import sys
import os
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.product import Product
from models.account import Account
from services.excel_handler import ExcelHandler
from services.facebook_bot import FacebookBot
from utils.browser_utils import create_browser_manager
from utils.logger import setup_logging, get_logger
from config import Config


class AutomatedListingManager:
    """
    Complete automated listing management system

    Features:
    - Load products from Excel
    - Load accounts from Excel
    - Create listings on Facebook Marketplace
    - Track success/failure rates
    - Handle multiple accounts
    - Integrate with AI system for responses
    """

    def __init__(self):
        """Initialize the listing manager"""
        setup_logging()
        self.logger = get_logger(__name__)

        # Ensure directories exist
        Config.ensure_directories()

        # Initialize components
        self.excel_handler = ExcelHandler()
        self.products: List[Product] = []
        self.accounts: List[Account] = []

        # Statistics
        self.total_listings_attempted = 0
        self.total_listings_successful = 0
        self.total_listings_failed = 0
        self.account_stats = {}

        # Runtime settings
        self.dry_run = False  # Set to False for real listing creation
        self.max_listings_per_account = 3  # Limit for safety
        self.delay_between_listings = (30, 60)  # seconds

    def load_data(self) -> bool:
        """Load products and accounts from Excel files"""
        try:
            self.logger.info("📋 Loading data from Excel files...")

            # Create sample files if they don't exist
            products_file = Config.DATA_DIR / "sample_data" / "sample_products.xlsx"
            accounts_file = Config.DATA_DIR / "sample_data" / "sample_accounts.xlsx"

            if not products_file.exists():
                self.logger.info("Creating sample products file...")
                self.excel_handler.create_sample_products_file(str(products_file))

            if not accounts_file.exists():
                self.logger.info("Creating sample accounts file...")
                self.excel_handler.create_sample_accounts_file(str(accounts_file))

            # Load data
            self.products = self.excel_handler.load_products(str(products_file))
            self.accounts = self.excel_handler.load_accounts(str(accounts_file))

            self.logger.info(f"✅ Loaded {len(self.products)} products")
            self.logger.info(f"✅ Loaded {len(self.accounts)} accounts")

            # Validate data
            active_accounts = [acc for acc in self.accounts if acc.is_usable()]
            if not active_accounts:
                self.logger.error("❌ No usable accounts found!")
                return False

            if not self.products:
                self.logger.error("❌ No products found!")
                return False

            self.logger.info(f"✅ {len(active_accounts)} usable accounts available")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error loading data: {e}")
            return False

    def create_listing_for_product(self, product: Product, account: Account, browser_manager) -> bool:
        """
        Create a single listing for a product using specified account

        Args:
            product: Product to list
            account: Account to use for listing
            browser_manager: Browser automation instance

        Returns:
            True if listing created successfully, False otherwise
        """
        try:
            self.logger.info(f"📱 Creating listing: {product.title}")
            self.logger.info(f"👤 Using account: {account.get_masked_email()}")

            # Initialize FacebookBot for this account
            bot = FacebookBot(account)
            bot.browser = browser_manager

            if self.dry_run:
                # Simulate listing creation
                self.logger.info("🔄 DRY RUN MODE - Simulating listing creation...")

                # Simulate the steps
                steps = [
                    "Navigating to Facebook Marketplace",
                    "Clicking 'Create New Listing'",
                    "Selecting 'Item for Sale'",
                    f"Entering title: '{product.title}'",
                    f"Entering description: '{product.description[:50]}...'",
                    f"Setting price: ${product.price}",
                    f"Setting category: '{product.category}'",
                    f"Setting condition: '{product.condition}'",
                    "Uploading images (simulated)",
                    "Publishing listing"
                ]

                for step in steps:
                    self.logger.info(f"  ✓ {step}")
                    time.sleep(random.uniform(0.5, 1.5))  # Simulate processing time

                self.logger.info("✅ Listing created successfully (simulated)")
                return True

            else:
                # Real listing creation
                self.logger.info("🚀 LIVE MODE - Creating real listing...")

                # Navigate to marketplace
                if not bot.navigate_to_marketplace():
                    self.logger.error("❌ Failed to navigate to marketplace")
                    return False

                # Create the listing
                if not bot.create_marketplace_listing(product):
                    self.logger.error("❌ Failed to create listing")
                    return False

                self.logger.info("✅ Listing created successfully!")
                return True

        except Exception as e:
            self.logger.error(f"❌ Error creating listing: {e}")
            return False

    def run_bulk_listing(self, max_products: int = None) -> Dict[str, Any]:
        """
        Run bulk listing across multiple products and accounts

        Args:
            max_products: Maximum number of products to list (None = all)

        Returns:
            Dictionary with results and statistics
        """
        try:
            self.logger.info("🚀 Starting bulk listing process...")

            # Prepare products and accounts
            active_accounts = [acc for acc in self.accounts if acc.is_usable()]
            products_to_list = self.products[:max_products] if max_products else self.products

            self.logger.info(f"📋 Will attempt to list {len(products_to_list)} products")
            self.logger.info(f"👥 Using {len(active_accounts)} active accounts")

            results = {
                'total_attempted': 0,
                'total_successful': 0,
                'total_failed': 0,
                'account_results': {},
                'product_results': [],
                'start_time': datetime.now(),
                'end_time': None
            }

            # Create browser manager
            with create_browser_manager(headless=False) as browser:
                self.logger.info("🌐 Browser initialized")

                account_index = 0

                for product_index, product in enumerate(products_to_list):
                    # Select account (round-robin)
                    current_account = active_accounts[account_index % len(active_accounts)]

                    # Check account listing limit
                    account_email = current_account.email
                    if account_email not in self.account_stats:
                        self.account_stats[account_email] = {'listings': 0, 'successes': 0, 'failures': 0}

                    if self.account_stats[account_email]['listings'] >= self.max_listings_per_account:
                        self.logger.info(f"⏸️ Account {current_account.get_masked_email()} reached listing limit")
                        account_index += 1
                        if account_index >= len(active_accounts):
                            self.logger.warning("⚠️ All accounts reached listing limits")
                            break
                        continue

                    # Attempt to create listing
                    self.total_listings_attempted += 1
                    results['total_attempted'] += 1
                    self.account_stats[account_email]['listings'] += 1

                    self.logger.info(f"\n📱 Listing {product_index + 1}/{len(products_to_list)}")

                    success = self.create_listing_for_product(product, current_account, browser)

                    # Record results
                    product_result = {
                        'product_title': product.title,
                        'account_email': current_account.get_masked_email(),
                        'success': success,
                        'timestamp': datetime.now()
                    }
                    results['product_results'].append(product_result)

                    if success:
                        self.total_listings_successful += 1
                        results['total_successful'] += 1
                        self.account_stats[account_email]['successes'] += 1
                        self.logger.info("✅ Listing successful")
                    else:
                        self.total_listings_failed += 1
                        results['total_failed'] += 1
                        self.account_stats[account_email]['failures'] += 1
                        self.logger.info("❌ Listing failed")

                    # Add delay between listings
                    if product_index < len(products_to_list) - 1:  # Don't delay after last listing
                        delay = random.uniform(*self.delay_between_listings)
                        self.logger.info(f"⏸️ Waiting {delay:.1f}s before next listing...")
                        time.sleep(delay)

                    # Move to next account for next listing
                    account_index += 1

            results['end_time'] = datetime.now()
            results['account_results'] = dict(self.account_stats)

            return results

        except Exception as e:
            self.logger.error(f"❌ Bulk listing error: {e}")
            return {'error': str(e)}

    def show_statistics(self, results: Dict[str, Any] = None):
        """Display listing statistics"""
        self.logger.info("\n📊 LISTING STATISTICS")
        self.logger.info("=" * 50)

        if results:
            duration = results['end_time'] - results['start_time']
            success_rate = (results['total_successful'] / results['total_attempted'] * 100) if results[
                                                                                                   'total_attempted'] > 0 else 0

            self.logger.info(f"📋 Total Attempted: {results['total_attempted']}")
            self.logger.info(f"✅ Successful: {results['total_successful']}")
            self.logger.info(f"❌ Failed: {results['total_failed']}")
            self.logger.info(f"📈 Success Rate: {success_rate:.1f}%")
            self.logger.info(f"⏱️ Duration: {duration}")

            # Account breakdown
            self.logger.info("\n👥 Account Performance:")
            for email, stats in results['account_results'].items():
                masked_email = email[:3] + "*" * (len(email) - 6) + email[-3:]
                self.logger.info(f"  {masked_email}: {stats['successes']}/{stats['listings']} successful")

        else:
            self.logger.info(f"📋 Total Attempted: {self.total_listings_attempted}")
            self.logger.info(f"✅ Successful: {self.total_listings_successful}")
            self.logger.info(f"❌ Failed: {self.total_listings_failed}")

            if self.total_listings_attempted > 0:
                success_rate = (self.total_listings_successful / self.total_listings_attempted) * 100
                self.logger.info(f"📈 Success Rate: {success_rate:.1f}%")

    def test_integration_with_ai(self):
        """Test integration with the AI system"""
        try:
            self.logger.info("\n🤖 Testing AI Integration...")

            # Import AI system
            from services.llama_ai import LlamaAI
            from models.message import Message

            # Initialize AI
            ai = LlamaAI()

            if not ai.test_connection():
                self.logger.warning("⚠️ AI system not available - listings will work without AI responses")
                return False

            # Test AI with a product
            if self.products:
                test_product = self.products[0]
                test_message = Message.create_customer_message(
                    content="Is this still available? What's your best price?",
                    sender_name="Test Customer",
                    conversation_id="test_conv"
                )

                response = ai.generate_response(test_message, test_product)

                if response:
                    self.logger.info(f"✅ AI Response: {response}")
                    self.logger.info("✅ AI integration working! Listings will have intelligent responses.")
                    return True
                else:
                    self.logger.warning("⚠️ AI response generation failed")
                    return False
            else:
                self.logger.warning("⚠️ No products available for AI testing")
                return False

        except Exception as e:
            self.logger.error(f"❌ AI integration test error: {e}")
            return False


def main():
    """Main execution function"""
    print("🚀 Facebook Marketplace Bot - Phase 3: Automated Listing")
    print("=" * 60)
    print("This will create automated listings and integrate with your AI system.")
    print()

    # Initialize manager
    manager = AutomatedListingManager()

    # Load data
    if not manager.load_data():
        print("❌ Failed to load data. Cannot proceed.")
        return False

    # Test AI integration
    ai_working = manager.test_integration_with_ai()

    # Show configuration
    print(f"\n⚙️ Configuration:")
    print(f"   Mode: {'DRY RUN (Safe)' if manager.dry_run else 'LIVE (Real listings)'}")
    print(f"   Max listings per account: {manager.max_listings_per_account}")
    print(f"   Delay between listings: {manager.delay_between_listings[0]}-{manager.delay_between_listings[1]}s")
    print(f"   AI integration: {'✅ Working' if ai_working else '⚠️ Not available'}")

    # Ask user for confirmation
    print(
        f"\n📋 Ready to process {len(manager.products)} products with {len([a for a in manager.accounts if a.is_usable()])} accounts")

    if manager.dry_run:
        choice = input("\n🔄 Run DRY RUN (safe simulation)? [y/N]: ").strip().lower()
    else:
        choice = input("\n⚠️ Run LIVE MODE (creates real listings)? [y/N]: ").strip().lower()

    if choice != 'y':
        print("❌ Operation cancelled by user.")
        return False

    # Run the bulk listing
    print("\n🚀 Starting automated listing process...")
    results = manager.run_bulk_listing(max_products=5)  # Limit to 5 for testing

    # Show results
    if 'error' in results:
        print(f"❌ Error during bulk listing: {results['error']}")
        return False

    manager.show_statistics(results)

    # Next steps
    print("\n🎯 Next Steps:")
    if manager.dry_run:
        print("1. ✅ Dry run completed successfully!")
        print("2. 🔧 Set manager.dry_run = False for real listing creation")
        print("3. 🤖 AI system is ready to handle customer responses")
        print("4. 📈 Proceed to Phase 4: Message Monitoring")
    else:
        print("1. ✅ Live listings created!")
        print("2. 🤖 AI will handle customer responses automatically")
        print("3. 📈 Monitor listing performance and customer messages")

    print(f"\n💾 Logs saved to: {Config.LOGS_DIR}")
    return True


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Phase 3 implementation completed successfully!")
        else:
            print("\n❌ Phase 3 implementation encountered issues.")
    except KeyboardInterrupt:
        print("\n\n⏹️ Process interrupted by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")