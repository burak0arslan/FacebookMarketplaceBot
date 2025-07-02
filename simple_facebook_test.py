#!/usr/bin/env python3
"""
Simple Browser Opener for Manual Facebook Test
Bypasses all bot logic and just opens a clean browser
"""

import sys
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import chromedriver_autoinstaller


def open_clean_browser_for_facebook():
    """
    Open a clean browser for manual Facebook testing
    """

    print("🌐 Opening Clean Browser for Facebook Test")
    print("=" * 50)
    print("This will open a fresh browser window where you can:")
    print("• Manually log into Facebook")
    print("• Navigate to Messages")
    print("• Test selectors manually")
    print("=" * 50)

    driver = None

    try:
        # Install chromedriver
        print("🔧 Setting up Chrome driver...")
        chromedriver_autoinstaller.install()

        # Configure Chrome options
        chrome_options = Options()

        # Don't use headless mode - we want to see the browser
        # chrome_options.add_argument("--headless")  # DISABLED

        # Disable some automation detection
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Set a normal user agent
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Create driver
        print("🚀 Opening browser...")
        driver = webdriver.Chrome(options=chrome_options)

        # Disable automation flags
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("✅ Browser opened successfully!")
        print("\n📋 Manual Test Instructions:")
        print("=" * 40)

        # Navigate to Facebook
        print("1. 🌐 Navigating to Facebook...")
        driver.get("https://www.facebook.com")
        time.sleep(3)

        current_url = driver.current_url
        page_title = driver.title

        print(f"   Current URL: {current_url}")
        print(f"   Page Title: {page_title}")

        print("\n2. 📝 Please complete the following manually:")
        print("   • Log into Facebook with your credentials")
        print("   • Complete any verification Facebook asks for")
        print("   • Navigate to Messages (facebook.com/messages)")

        input("\nPress Enter when you've logged in and are on the Messages page...")

        # Check final status
        final_url = driver.current_url
        final_title = driver.title

        print(f"\n📊 Final Status:")
        print(f"   URL: {final_url}")
        print(f"   Title: {final_title}")

        if "messages" in final_url.lower():
            print("✅ Successfully on Messages page!")

            # Test selectors manually
            print("\n3. 🔍 Testing Facebook selectors...")

            # Test basic selectors
            test_selectors = [
                ('[role="grid"]', 'Grid elements'),
                ('[role="main"]', 'Main content'),
                ('[role="gridcell"]', 'Grid cells (conversations)'),
                ('[data-testid*="conversation"]', 'Conversation elements'),
                ('a[href*="/messages/t/"]', 'Message links'),
                ('[aria-label*="Conversations"]', 'Conversation containers'),
                ('[role="main"] [role="grid"]', 'Main grid container')
            ]

            working_selectors = []

            for selector, description in test_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    count = len(elements)

                    if count > 0:
                        print(f"   ✅ {description}: {count} elements found")
                        working_selectors.append(selector)
                    else:
                        print(f"   ❌ {description}: No elements found")

                except Exception as e:
                    print(f"   ❌ {description}: Error - {str(e)[:50]}...")

            print(f"\n📊 Selector Test Results:")
            print(f"   Working selectors: {len(working_selectors)}/{len(test_selectors)}")

            if working_selectors:
                print(f"\n✅ Working selectors found:")
                for selector in working_selectors:
                    print(f"      • {selector}")

                # Test the best working selector
                best_selector = working_selectors[0]
                print(f"\n🔍 Testing best selector: {best_selector}")

                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, best_selector)
                    print(f"   Found {len(elements)} elements")

                    if elements:
                        # Try to extract conversation info from first element
                        first_element = elements[0]

                        # Look for conversation children
                        children = first_element.find_elements(By.XPATH, "./*")
                        print(f"   First element has {len(children)} children")

                        # Look for text content
                        try:
                            text_elements = first_element.find_elements(By.CSS_SELECTOR, "span, div, a")
                            text_content = [elem.text.strip() for elem in text_elements[:5] if elem.text.strip()]
                            if text_content:
                                print(f"   Sample text content: {text_content[:3]}")
                        except:
                            print("   Could not extract text content")

                        print("\n🎉 SELECTOR TESTING SUCCESSFUL!")
                        print("✅ Your bot should be able to detect messages")
                        success = True
                    else:
                        print("   No elements found with best selector")
                        success = False

                except Exception as e:
                    print(f"   Error testing best selector: {e}")
                    success = False
            else:
                print("\n⚠️ No working selectors found")
                print("💡 Facebook may have changed their layout")
                success = False

        else:
            print("❌ Not on Messages page")
            print("💡 Please navigate to facebook.com/messages manually")
            success = False

        # Keep browser open for inspection
        print(f"\n🔍 Browser will stay open for inspection...")
        print("You can inspect the page elements manually to find working selectors")

        input("Press Enter when you're done inspecting...")

        return success

    except Exception as e:
        print(f"❌ Browser test failed: {e}")
        return False

    finally:
        if driver:
            print("🧹 Closing browser...")
            driver.quit()


def test_facebook_credentials():
    """
    Simple test to verify Facebook credentials work
    """

    print("🔐 Facebook Credentials Test")
    print("=" * 35)

    # Load credentials
    try:
        project_root = Path(__file__).parent
        sys.path.append(str(project_root))

        from services.excel_handler import ExcelHandler

        excel_handler = ExcelHandler()
        accounts = excel_handler.load_accounts("data/sample_accounts.xlsx")

        if not accounts:
            print("❌ No accounts found in sample_accounts.xlsx")
            return False

        test_account = accounts[0]
        print(f"📧 Testing account: {test_account.get_masked_email()}")
        print(f"👤 Profile name: {test_account.profile_name}")
        print(f"📱 Message monitor: {test_account.message_monitor}")

        # Show credentials (masked password)
        masked_password = test_account.password[:2] + "*" * (len(test_account.password) - 4) + test_account.password[
                                                                                               -2:]
        print(f"🔑 Password: {masked_password}")

        print(f"\n💡 Use these credentials to log in manually:")
        print(f"   Email: {test_account.email}")
        print(f"   Password: [use the actual password from your Excel file]")

        return True

    except Exception as e:
        print(f"❌ Credentials test failed: {e}")
        return False


def run_page_source_analysis():
    """
    Save current Facebook page source for analysis
    """

    print("📄 Facebook Page Source Analysis")
    print("=" * 40)

    driver = None

    try:
        # Setup browser
        chromedriver_autoinstaller.install()
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)

        print("🌐 Opening Facebook...")
        driver.get("https://www.facebook.com")
        time.sleep(3)

        print("📝 Please log in manually and navigate to Messages")
        input("Press Enter when you're on the Messages page...")

        # Save page source
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"facebook_messages_source_{timestamp}.html"

        page_source = driver.page_source

        with open(filename, "w", encoding="utf-8") as f:
            f.write(page_source)

        print(f"✅ Page source saved to: {filename}")
        print("📖 You can inspect this file to find the correct selectors")

        # Quick element analysis
        grid_elements = driver.find_elements(By.CSS_SELECTOR, '[role="grid"]')
        main_elements = driver.find_elements(By.CSS_SELECTOR, '[role="main"]')

        print(f"\n📊 Quick Analysis:")
        print(f"   Grid elements: {len(grid_elements)}")
        print(f"   Main elements: {len(main_elements)}")

        return True

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    print("Facebook Manual Testing Tools")
    print("=" * 35)
    print("Choose option:")
    print("1. Open clean browser for manual testing")
    print("2. Test Facebook credentials")
    print("3. Save page source for analysis")
    print("4. Exit")

    choice = input("\nEnter choice (1/2/3/4): ").strip()

    if choice == "1":
        success = open_clean_browser_for_facebook()
    elif choice == "2":
        success = test_facebook_credentials()
    elif choice == "3":
        success = run_page_source_analysis()
    elif choice == "4":
        print("👋 Goodbye!")
        sys.exit(0)
    else:
        print("❌ Invalid choice")
        sys.exit(1)

    if success:
        print("\n🎊 MANUAL TEST COMPLETED!")
        print("💡 Use the information above to update your bot's selectors")
    else:
        print("\n🔧 MANUAL TEST HAD ISSUES")
        print("💡 Try a different option or check your setup")