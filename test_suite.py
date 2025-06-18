"""
Comprehensive Test Suite for Facebook Marketplace Bot - Windows Compatible
Tests all implemented components in Phases 1 and 2
"""

import sys
import os
from pathlib import Path
import pandas as pd
import time
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all modules can be imported successfully"""
    print("Testing imports...")

    try:
        # Test config import
        from config import Config
        print("✓ Config imported successfully")

        # Test models
        from models.product import Product
        from models.account import Account
        from models.message import Message
        print("✓ Models imported successfully")

        # Test services
        from services.excel_handler import ExcelHandler
        print("✓ Services imported successfully")

        # Test utilities
        from utils.logger import setup_logging, get_logger
        from utils.browser_utils import BrowserManager
        print("✓ Utilities imported successfully")

        return True

    except Exception as e:
        print(f"✗ Import error: {e}")
        return False


def test_configuration():
    """Test configuration system"""
    print("\nTesting configuration...")

    try:
        from config import Config

        # Test directory creation
        Config.ensure_directories()
        print("✓ Directories created successfully")

        # Test validation
        issues = Config.validate_settings()
        if issues:
            print(f"! Configuration issues found: {issues}")
        else:
            print("✓ Configuration validation passed")

        # Test key settings
        print(f"Data directory: {Config.DATA_DIR}")
        print(f"Logs directory: {Config.LOGS_DIR}")
        print(f"Debug mode: {Config.DEBUG_MODE}")
        print(f"Facebook URL: {Config.FB_MARKETPLACE_URL}")

        return True

    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False


def test_logging_system():
    """Test logging system"""
    print("\nTesting logging system...")

    try:
        from utils.logger import setup_logging, get_logger, log_performance, log_facebook_action

        # Setup logging
        setup_logging()
        logger = get_logger("test")

        # Test different log levels
        logger.debug("Debug message test")
        logger.info("Info message test")
        logger.warning("Warning message test")
        logger.error("Error message test")

        # Test convenience functions
        log_performance("test_operation", 1.5)
        log_facebook_action("test_login", "t**t@example.com", True, "Test login successful")

        print("✓ Logging system working")
        return True

    except Exception as e:
        print(f"✗ Logging error: {e}")
        return False


def test_data_models():
    """Test data models (Product, Account, Message)"""
    print("\nTesting data models...")

    try:
        from models.product import Product
        from models.account import Account
        from models.message import Message, MessageType, MessageStatus

        # Test Product model
        product = Product(
            title="Test iPhone",
            description="Test description for iPhone",
            price=500.0,
            category="Electronics",
            keywords=["iphone", "apple", "test"],
            images=["test1.jpg", "test2.jpg"]
        )

        print(f"✓ Product model: {product.title} - {product.get_formatted_price()}")

        # Test Account model
        account = Account(
            email="test@email.com",
            password="test_password",
            profile_name="Test User"
        )

        print(f"✓ Account model: {account.get_masked_email()} - {account.profile_name}")

        # Test Message model
        message = Message.create_customer_message(
            content="Hi, is this item still available?",
            sender_name="John Buyer",
            product_title="Test iPhone"
        )

        print(f"✓ Message model: {message.sender_name} - Priority: {message.get_priority_score()}")

        return True

    except Exception as e:
        print(f"✗ Data models error: {e}")
        return False


def test_excel_handler():
    """Test Excel file handling"""
    print("\nTesting Excel handler...")

    try:
        from services.excel_handler import ExcelHandler

        handler = ExcelHandler()

        # Check if sample files exist, create if not
        sample_products_path = Path("data/sample_products.xlsx")
        sample_accounts_path = Path("data/sample_accounts.xlsx")

        if not sample_products_path.exists():
            print("Creating sample products file...")
            handler.create_sample_products_file()

        if not sample_accounts_path.exists():
            print("Creating sample accounts file...")
            handler.create_sample_accounts_file()

        # Test loading
        products = handler.load_products("data/sample_products.xlsx")
        accounts = handler.load_accounts("data/sample_accounts.xlsx")

        print(f"✓ Loaded {len(products)} products")
        print(f"✓ Loaded {len(accounts)} accounts")

        # Test individual products and accounts
        for product in products:
            print(f"  Product: {product.title}: {product.get_formatted_price()}")

        for account in accounts:
            print(f"  Account: {account.get_masked_email()}: {account.profile_name}")

        return True

    except Exception as e:
        print(f"✗ Excel handler error: {e}")
        return False


def test_browser_utilities():
    """Test browser utilities (basic setup only)"""
    print("\nTesting browser utilities...")

    try:
        from utils.browser_utils import BrowserManager

        # Test browser manager initialization
        browser = BrowserManager(headless=True)  # Use headless for testing
        print("✓ BrowserManager initialized")

        # Test configuration methods
        options = browser._get_chrome_options("test_profile")
        print("✓ Chrome options generated")

        # Test delay settings
        from config import Config
        delay_range = Config.get_delay_range()
        print(f"✓ Delay settings: {delay_range}")

        print("✓ Browser utilities available")

        return True

    except Exception as e:
        print(f"✗ Browser utilities error: {e}")
        return False


def test_file_structure():
    """Test project file structure"""
    print("\nTesting file structure...")

    try:
        from config import Config

        required_files = [
            "config.py",
            "main.py",
            "requirements.txt",
            "models/__init__.py",
            "models/product.py",
            "models/account.py",
            "models/message.py",
            "services/__init__.py",
            "services/excel_handler.py",
            "utils/__init__.py",
            "utils/logger.py",
            "utils/browser_utils.py"
        ]

        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            print(f"! Missing files: {missing_files}")
        else:
            print("✓ All core files present")

        # Check directories
        required_dirs = [Config.DATA_DIR, Config.LOGS_DIR]
        for directory in required_dirs:
            if directory.exists():
                print(f"✓ Directory exists: {directory}")
            else:
                print(f"✗ Directory missing: {directory}")

        return len(missing_files) == 0

    except Exception as e:
        print(f"✗ File structure error: {e}")
        return False


def test_integration():
    """Test integration between components"""
    print("\nTesting component integration...")

    try:
        from utils.logger import get_logger
        from models.product import Product
        from models.account import Account
        from services.excel_handler import ExcelHandler

        logger = get_logger("integration_test")

        # Test models work together
        product = Product(
            title="Test iPhone",
            description="Integration test product",
            price=600.0,
            category="Electronics"
        )

        account = Account(
            email="test@email.com",
            password="test_password",
            profile_name="Test User"
        )

        logger.info(f"Models working: {product.title}, {account.get_masked_email()}")

        # Test Excel handler with models
        handler = ExcelHandler()
        products = handler.load_products("data/sample_products.xlsx")
        accounts = handler.load_accounts("data/sample_accounts.xlsx")

        logger.info(f"Excel handler working: {len(products)} products, {len(accounts)} accounts")

        print("✓ Integration tests passed")
        return True

    except Exception as e:
        print(f"✗ Integration error: {e}")
        return False


def run_performance_tests():
    """Run basic performance tests"""
    print("\nRunning performance tests...")

    try:
        from utils.logger import log_performance

        # Test model creation speed
        start_time = time.time()

        from models.product import Product
        products = []
        for i in range(100):
            product = Product(
                title=f"Test Product {i}",
                description=f"Description for product {i}",
                price=float((i + 1) * 10),
                category="Electronics"
            )
            products.append(product)

        creation_time = time.time() - start_time
        log_performance("create_100_products", creation_time)

        print(f"✓ Created 100 products in {creation_time:.2f}s")

        # Test Excel operations speed
        start_time = time.time()

        from services.excel_handler import ExcelHandler
        handler = ExcelHandler()
        loaded_products = handler.load_products("data/sample_products.xlsx")

        load_time = time.time() - start_time
        log_performance("load_sample_products", load_time)

        print(f"✓ Loaded products in {load_time:.2f}s")

        return True

    except Exception as e:
        print(f"✗ Performance test error: {e}")
        return False


def generate_test_report():
    """Generate a comprehensive test report"""
    print("\n" + "=" * 60)
    print("FACEBOOK MARKETPLACE BOT - TEST REPORT")
    print("=" * 60)

    tests = [
        ("Import Tests", test_imports),
        ("Configuration Tests", test_configuration),
        ("Logging System Tests", test_logging_system),
        ("Data Models Tests", test_data_models),
        ("Excel Handler Tests", test_excel_handler),
        ("Browser Utilities Tests", test_browser_utilities),
        ("File Structure Tests", test_file_structure),
        ("Integration Tests", test_integration),
        ("Performance Tests", run_performance_tests)
    ]

    results = {}
    total_tests = len(tests)
    passed_tests = 0

    start_time = time.time()

    for test_name, test_func in tests:
        print(f"\n{'=' * 40}")
        print(f"Running: {test_name}")
        print('=' * 40)

        try:
            result = test_func()
            results[test_name] = "PASSED" if result else "FAILED"
            if result:
                passed_tests += 1
        except Exception as e:
            results[test_name] = f"ERROR: {e}"

    total_time = time.time() - start_time

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, result in results.items():
        status_icon = "✓" if result == "PASSED" else "✗"
        print(f"{status_icon} {test_name}: {result}")

    print(f"\nResults: {passed_tests}/{total_tests} tests passed")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Test date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    if passed_tests == total_tests:
        print("✓ All tests passed! Your Phase 1 implementation is solid.")
        print("✓ Ready to move to Phase 2 completion or Phase 3.")
    else:
        print("! Some tests failed. Review the errors above.")
        print("! Focus on fixing failing components before proceeding.")

    print("\nNext Steps:")
    print("1. Review any failed tests and fix issues")
    print("2. Complete Phase 2 by implementing facebook_bot.py")
    print("3. Test Facebook login functionality")
    print("4. Move to Phase 3 (Marketplace Listing)")

    return results


if __name__ == "__main__":
    print("Starting Facebook Marketplace Bot Test Suite...")
    results = generate_test_report()
    print("\nTest suite completed!")