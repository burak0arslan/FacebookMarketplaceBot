#!/usr/bin/env python3
"""
Test Script for Updated Facebook Message Selectors
Run this to test if the new selectors work with current Facebook
"""

import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from services.excel_handler import ExcelHandler
from services.facebook_bot import FacebookBot
from selenium.webdriver.common.by import By


def test_updated_message_selectors():
    """Test the updated message selectors"""

    print("🧪 Testing Updated Facebook Message Selectors")
    print("=" * 60)

    try:
        # Load test account
        excel_handler = ExcelHandler()
        accounts = excel_handler.load_accounts("data/sample_accounts.xlsx")

        if not accounts:
            print("❌ No accounts found")
            return False

        # Use Bruce's account (has message monitoring enabled)
        test_account = accounts[0]  # Bruce Arslan

        print(f"🤖 Testing with account: {test_account.get_masked_email()}")
        print(f"📧 Message monitoring: {test_account.message_monitor}")

        # Initialize bot
        bot = FacebookBot(test_account)

        print("\n🌐 Starting Facebook session...")

        # Start session (this will handle login)
        if not bot.start_facebook_session():
            print("❌ Failed to start Facebook session")
            return False

        print("✅ Facebook session started successfully")

        # Navigate to messages
        print("\n📨 Navigating to Facebook Messages...")
        messages_url = "https://www.facebook.com/messages"

        if not bot.browser.navigate_to(messages_url):
            print("❌ Failed to navigate to messages")
            return False

        print("✅ Successfully navigated to messages")

        # Wait for page to load
        time.sleep(5)

        # Test new selectors
        print("\n🔍 Testing conversation list selectors...")

        conversation_list_selectors = [
            '[role="main"] [role="grid"]',
            '[data-pagelet="MessengerConversations"]',
            '[aria-label*="Conversations"] [role="grid"]',
            'div[role="grid"][aria-label*="Conversations"]',
            '[role="navigation"] + div [role="grid"]',
            'div[role="grid"]'
        ]

        working_selectors = []

        for selector in conversation_list_selectors:
            try:
                element = bot.browser.find_element_safe(
                    By.CSS_SELECTOR,
                    selector,
                    timeout=2
                )

                if element:
                    print(f"✅ WORKS: {selector}")
                    working_selectors.append(selector)

                    # Test finding conversations within this element
                    conv_selectors = [
                        '[data-testid="conversation"]',
                        '[role="gridcell"]',
                        'div[role="gridcell"] a'
                    ]

                    for conv_sel in conv_selectors:
                        try:
                            convs = element.find_elements(By.CSS_SELECTOR, conv_sel)
                            if convs:
                                print(f"   → Found {len(convs)} conversations with: {conv_sel}")
                                break
                        except:
                            continue
                else:
                    print(f"❌ FAILS: {selector}")

            except Exception as e:
                print(f"❌ ERROR: {selector} - {str(e)[:50]}...")

        # Test message monitoring
        if working_selectors:
            print(f"\n🎉 SUCCESS! Found {len(working_selectors)} working selectors")
            print("\n🤖 Testing message monitoring...")

            try:
                # Initialize message monitor with updated bot
                from services.message_monitor import MessageMonitor
                monitor = MessageMonitor(bot.browser, test_account)

                # Test scanning for messages
                conversations = monitor._get_conversation_list()

                if conversations:
                    print(f"✅ Message monitoring working! Found {len(conversations)} conversations")
                    for conv in conversations[:3]:  # Show first 3
                        unread_status = "🔴 UNREAD" if conv.get('has_unread') else "✅ Read"
                        print(f"   - {conv.get('name', 'Unknown')} ({unread_status})")
                else:
                    print("⚠️ No conversations found (this might be normal if no messages exist)")

            except Exception as e:
                print(f"⚠️ Message monitoring test error: {e}")

        else:
            print("❌ No working selectors found")

            # Save page source for debugging
            try:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                debug_file = f"debug_facebook_messages_{timestamp}.html"

                page_source = bot.browser.driver.page_source
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(page_source)

                print(f"📝 Page source saved to {debug_file} for manual inspection")

            except Exception as e:
                print(f"Could not save debug file: {e}")

        # Cleanup
        print("\n🧹 Cleaning up...")
        bot.end_facebook_session()

        return len(working_selectors) > 0

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def run_quick_selector_test():
    """Quick test without full login"""

    print("🚀 Quick Selector Test (No Login Required)")
    print("=" * 50)

    try:
        from utils.browser_utils import BrowserManager

        # Create browser instance
        with BrowserManager(headless=False) as browser:
            print("🌐 Opening Facebook Messages page...")
            browser.navigate_to("https://www.facebook.com/messages")

            print("⏳ Please log in manually in the browser window...")
            input("Press Enter when you're logged in and on the messages page...")

            # Test selectors
            print("\n🔍 Testing selectors...")

            selectors_to_test = [
                '[role="main"] [role="grid"]',
                '[data-pagelet="MessengerConversations"]',
                '[aria-label*="Conversations"]',
                'div[role="grid"]'
            ]

            for selector in selectors_to_test:
                element = browser.find_element_safe(By.CSS_SELECTOR, selector, timeout=2)
                if element:
                    print(f"✅ {selector}")
                else:
                    print(f"❌ {selector}")

            # Save current page source
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            debug_file = f"facebook_messages_source_{timestamp}.html"

            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(browser.driver.page_source)

            print(f"\n📝 Page source saved to: {debug_file}")
            print("You can inspect this file to find the correct selectors")

        return True

    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False


if __name__ == "__main__":
    print("Facebook Message Selector Testing")
    print("=" * 40)
    print("1. Full test (with bot login)")
    print("2. Quick test (manual login)")
    print("3. Exit")

    choice = input("\nEnter choice (1/2/3): ").strip()

    if choice == "1":
        success = test_updated_message_selectors()
    elif choice == "2":
        success = run_quick_selector_test()
    elif choice == "3":
        print("👋 Goodbye!")
        sys.exit(0)
    else:
        print("❌ Invalid choice")
        sys.exit(1)

    if success:
        print("\n🎉 Selector testing completed successfully!")
        print("💡 Update your message_monitor.py with the working selectors")
    else:
        print("\n⚠️ Some issues found. Check the output above for details.")