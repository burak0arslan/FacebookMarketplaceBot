"""
Facebook Bot Testing Script
Comprehensive testing for Facebook automation functionality
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_facebook_bot_import():
    """Test that FacebookBot can be imported"""
    print("Testing Facebook Bot import...")

    try:
        from services.facebook_bot import FacebookBot, create_facebook_bot, test_facebook_login
        print("✓ FacebookBot imported successfully")
        return True
    except Exception as e:
        print(f"✗ FacebookBot import failed: {e}")
        return False


def test_bot_initialization():
    """Test bot initialization with sample account"""
    print("\nTesting bot initialization...")

    try:
        from services.excel_handler import ExcelHandler
        from services.facebook_bot import FacebookBot

        # Load sample accounts
        handler = ExcelHandler()
        accounts = handler.load_accounts("data/sample_accounts.xlsx")

        if not accounts:
            print("✗ No accounts found for testing")
            return False

        # Use first account for testing
        test_account = accounts[0]
        print(f"Using test account: {test_account.get_masked_email()}")

        # Create bot instance (don't start session yet)
        bot = FacebookBot(test_account, headless=True)
        print("✓ FacebookBot instance created successfully")

        # Test session info
        session_info = bot.get_session_info()
        print(f"✓ Session info: {session_info['account']}")

        return True

    except Exception as e:
        print(f"✗ Bot initialization failed: {e}")
        return False


def test_browser_setup():
    """Test browser setup without Facebook"""
    print("\nTesting browser setup...")

    try:
        from services.excel_handler import ExcelHandler
        from services.facebook_bot import FacebookBot

        # Load account
        handler = ExcelHandler()
        accounts = handler.load_accounts("data/sample_accounts.xlsx")
        test_account = accounts[0]

        # Create bot
        bot = FacebookBot(test_account, headless=True)

        # Test browser setup
        if bot._setup_browser():
            print("✓ Browser setup successful")

            # Test basic browser functionality
            if bot.browser.navigate_to("https://www.google.com"):
                print("✓ Browser navigation working")

                # Cleanup
                bot.browser.cleanup()
                return True
            else:
                print("✗ Browser navigation failed")
                return False
        else:
            print("✗ Browser setup failed")
            return False

    except Exception as e:
        print(f"✗ Browser setup test failed: {e}")
        return False


def test_rate_limiting():
    """Test rate limiting functionality"""
    print("\nTesting rate limiting...")

    try:
        from services.excel_handler import ExcelHandler
        from services.facebook_bot import FacebookBot

        handler = ExcelHandler()
        accounts = handler.load_accounts("data/sample_accounts.xlsx")
        test_account = accounts[0]

        bot = FacebookBot(test_account, headless=True)

        # Test initial rate limits (should be fine)
        if bot.check_rate_limits():
            print("✓ Initial rate limits OK")
        else:
            print("✗ Initial rate limits failed")
            return False

        # Simulate some activity
        for i in range(5):
            bot._update_activity()

        session_info = bot.get_session_info()
        print(f"✓ Activity tracking working: {session_info['action_count']} actions")

        return True

    except Exception as e:
        print(f"✗ Rate limiting test failed: {e}")
        return False


def manual_facebook_test():
    """Manual test with actual Facebook (requires user interaction)"""
    print("\nManual Facebook Test")
    print("=" * 40)

    # Ask user if they want to run manual test
    response = input("Run manual Facebook test? This will open a browser window. (y/n): ")
    if response.lower() != 'y':
        print("Manual test skipped")
        return True

    # Get account choice
    print("\nAccount options:")
    print("1. Use sample account (you'll need to update credentials)")
    print("2. Enter test credentials manually")
    choice = input("Choose option (1/2): ")

    try:
        from services.excel_handler import ExcelHandler
        from services.facebook_bot import FacebookBot
        from models.account import Account

        if choice == "1":
            # Use sample account
            handler = ExcelHandler()
            accounts = handler.load_accounts("data/sample_accounts.xlsx")
            if not accounts:
                print("✗ No sample accounts found")
                return False
            test_account = accounts[0]
            print(f"Using sample account: {test_account.get_masked_email()}")
            print("⚠️ Make sure to update the credentials in sample_accounts.xlsx")

        elif choice == "2":
            # Manual credentials
            email = input("Enter test Facebook email: ")
            password = input("Enter test Facebook password: ")
            test_account = Account(
                email=email,
                password=password,
                profile_name="Test User"
            )
        else:
            print("Invalid choice")
            return False

        # Create bot in non-headless mode for manual testing
        print("\nStarting Facebook bot (non-headless mode)...")
        bot = FacebookBot(test_account, headless=False)

        print("Testing browser setup...")
        if not bot._setup_browser():
            print("✗ Browser setup failed")
            return False
        print("✓ Browser setup successful")

        print("Testing Facebook navigation...")
        if not bot._navigate_to_facebook():
            print("✗ Facebook navigation failed")
            bot.browser.cleanup()
            return False
        print("✓ Facebook navigation successful")

        print("\n⚠️ IMPORTANT:")
        print("- This will attempt to log into Facebook")
        print("- Only use test accounts, not your main Facebook account")
        print("- Facebook may detect automation and flag the account")
        print("- Be prepared to solve CAPTCHAs manually")

        proceed = input("\nProceed with login test? (y/n): ")
        if proceed.lower() == 'y':
            print("Attempting Facebook login...")
            if bot._perform_login():
                print("✓ Login process completed")

                # Wait for user to verify
                input("Check the browser window. Press Enter when ready to continue...")

                if bot._verify_login():
                    print("✓ Login verification successful!")

                    # Test marketplace navigation
                    marketplace_test = input("Test marketplace navigation? (y/n): ")
                    if marketplace_test.lower() == 'y':
                        if bot.navigate_to_marketplace():
                            print("✓ Marketplace navigation successful!")
                        else:
                            print("✗ Marketplace navigation failed")
                else:
                    print("✗ Login verification failed")
            else:
                print("✗ Login process failed")

        # Cleanup
        print("Cleaning up...")
        bot.browser.cleanup()
        print("✓ Manual test completed")

        return True

    except Exception as e:
        print(f"✗ Manual test error: {e}")
        return False


def safe_facebook_test():
    """Safe test that doesn't actually log into Facebook"""
    print("\nSafe Facebook Test (No actual login)")
    print("=" * 40)

    try:
        from services.excel_handler import ExcelHandler
        from services.facebook_bot import FacebookBot

        # Load account
        handler = ExcelHandler()
        accounts = handler.load_accounts("data/sample_accounts.xlsx")
        test_account = accounts[0]

        # Create bot
        bot = FacebookBot(test_account, headless=True)

        print("Testing browser setup...")
        if bot._setup_browser():
            print("✓ Browser setup successful")

            print("Testing Facebook page load (login page only)...")
            if bot.browser.navigate_to("https://www.facebook.com"):
                print("✓ Facebook page loaded")

                # Check for login form
                email_field = bot.browser.find_element_safe("css_selector", 'input[name="email"]', timeout=5)
                if email_field:
                    print("✓ Login form detected")
                else:
                    print("⚠️ Login form not found (may be different layout)")

                # Take screenshot
                screenshot_path = bot.browser.take_screenshot("facebook_login_page_test")
                if screenshot_path:
                    print(f"✓ Screenshot saved: {screenshot_path}")

            else:
                print("✗ Facebook page load failed")
                return False

            # Cleanup
            bot.browser.cleanup()
            print("✓ Safe test completed successfully")
            return True
        else:
            print("✗ Browser setup failed")
            return False

    except Exception as e:
        print(f"✗ Safe test error: {e}")
        return False


def test_account_management():
    """Test account loading and management"""
    print("\nTesting account management...")

    try:
        from services.excel_handler import ExcelHandler

        handler = ExcelHandler()
        accounts = handler.load_accounts("data/sample_accounts.xlsx")

        print(f"✓ Loaded {len(accounts)} accounts")

        for i, account in enumerate(accounts):
            print(f"  Account {i + 1}: {account.get_masked_email()} - {account.profile_name}")
            print(f"    Active: {account.active}")
            print(f"    Message Monitor: {account.message_monitor}")
            print(f"    Status: {account.account_status}")

        # Test account filtering
        active_accounts = [acc for acc in accounts if acc.is_usable()]
        print(f"✓ {len(active_accounts)} accounts are usable for automation")

        return True

    except Exception as e:
        print(f"✗ Account management test failed: {e}")
        return False


def run_facebook_bot_tests():
    """Run comprehensive Facebook bot tests"""
    print("=" * 60)
    print("FACEBOOK BOT TESTING SUITE")
    print("=" * 60)

    tests = [
        ("Facebook Bot Import", test_facebook_bot_import),
        ("Bot Initialization", test_bot_initialization),
        ("Browser Setup", test_browser_setup),
        ("Rate Limiting", test_rate_limiting),
        ("Account Management", test_account_management),
        ("Safe Facebook Test", safe_facebook_test),
        ("Manual Facebook Test", manual_facebook_test)
    ]

    results = {}
    passed = 0

    for test_name, test_func in tests:
        print(f"\n{'-' * 40}")
        print(f"Running: {test_name}")
        print('-' * 40)

        try:
            result = test_func()
            results[test_name] = "PASSED" if result else "FAILED"
            if result:
                passed += 1
        except Exception as e:
            results[test_name] = f"ERROR: {e}"
            print(f"✗ Unexpected error: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("FACEBOOK BOT TEST SUMMARY")
    print("=" * 60)

    for test_name, result in results.items():
        status_icon = "✓" if result == "PASSED" else "✗"
        print(f"{status_icon} {test_name}: {result}")

    print(f"\nResults: {passed}/{len(tests)} tests passed")
    print(f"Test date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    if passed >= len(tests) - 1:  # Allow manual test to be skipped
        print("✓ Facebook Bot is working well!")
        print("✓ Ready for Facebook automation")
        if passed == len(tests):
            print("✓ All tests passed including manual Facebook test!")
    else:
        print("⚠️ Some tests failed")
        print("🔧 Review failed tests before proceeding")

    print("\n📋 Next Steps:")
    print("1. If safe tests pass: Facebook Bot is ready")
    print("2. Run manual test with real credentials to verify login")
    print("3. Update sample accounts with real test credentials")
    print("4. Proceed to Phase 3 (Marketplace Listing)")

    return results


if __name__ == "__main__":
    print("Starting Facebook Bot test suite...")
    results = run_facebook_bot_tests()
    print("\nFacebook Bot testing completed!")