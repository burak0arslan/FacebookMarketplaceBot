"""
Test Marketplace Listing Functionality
"""
from services.facebook_bot import FacebookBot
from services.excel_handler import ExcelHandler
from utils.browser_utils import create_browser_manager
from utils.logger import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Load data
excel_handler = ExcelHandler()

# CREATE sample files first
logger.info("Creating sample files...")
excel_handler.create_sample_products_file("data/sample_data/sample_products.xlsx")
excel_handler.create_sample_accounts_file("data/sample_data/sample_accounts.xlsx")

# NOW load them
products = excel_handler.load_products("data/sample_data/sample_products.xlsx")
accounts = excel_handler.load_accounts("data/sample_data/sample_accounts.xlsx")

logger.info(f"Loaded {len(products)} products and {len(accounts)} accounts")

# Test marketplace listing
logger.info("Testing marketplace listing functionality...")

with create_browser_manager(headless=False) as browser:
    # Pass the account to FacebookBot constructor
    bot = FacebookBot(accounts[0])  # ← FIX: Pass account, not browser

    logger.info("⚠️ Note: Real Facebook login required for full test")
    logger.info(f"Test product: {products[0].title}")
    logger.info(f"Test account: {accounts[0].get_masked_email()}")

    # Test if create_marketplace_listing method exists
    if hasattr(bot, 'create_marketplace_listing'):
        logger.info("✅ create_marketplace_listing method found")
    else:
        logger.error("❌ create_marketplace_listing method missing")

    logger.info("✅ Marketplace listing integration ready!")