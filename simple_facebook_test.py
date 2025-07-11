#!/usr/bin/env python3
"""
Simple Browser Opener for Manual Facebook Test - Playwright Version
Bypasses all bot logic and just opens a clean browser
"""

import sys
import time
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright


async def open_clean_browser_for_facebook_async():
    """
    Open a clean browser for manual Facebook testing (async version)
    """
    print("🌐 Opening Clean Browser for Facebook Test (Playwright Async)")
    print("=" * 60)
    print("This will open a fresh browser window where you can:")
    print("• Manually log into Facebook")
    print("• Navigate to Messages")
    print("• Test selectors manually")
    print("=" * 60)

    async with async_playwright() as p:
        try:
            print("🔧 Setting up Playwright browser...")

            # Launch browser with anti-detection settings
            browser = await p.chromium.launch(
                headless=False,  # Show browser window
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions",
                    "--no-first-run",
                    "--disable-default-apps"
                ]
            )

            # Create context with realistic settings
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York"
            )

            # Create page
            page = await context.new_page()

            # Remove automation detection
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)

            print("✅ Browser opened successfully!")
            print("\n📋 Manual Test Instructions:")
            print("=" * 40)

            # Navigate to Facebook
            print("1. 🌐 Navigating to Facebook...")
            await page.goto("https://www.facebook.com", wait_until="domcontentloaded")

            current_url = page.url
            page_title = await page.title()

            print(f"   Current URL: {current_url}")
            print(f"   Page Title: {page_title}")

            print("\n2. 🔍 Manual Login Instructions:")
            print("   - Enter your Facebook credentials manually")
            print("   - Complete any security checks if prompted")
            print("   - Navigate to different sections to test")

            print("\n3. 🧪 Testing Available CSS Selectors:")
            print("   Email input selectors to test:")
            print("   - input[name=\"email\"]")
            print("   - input[type=\"email\"]")
            print("   - input[id=\"email\"]")

            print("\n   Password input selectors to test:")
            print("   - input[name=\"pass\"]")
            print("   - input[type=\"password\"]")
            print("   - input[id=\"pass\"]")

            print("\n   Login button selectors to test:")
            print("   - button[name=\"login\"]")
            print("   - button[type=\"submit\"]")
            print("   - button[data-testid=\"royal_login_button\"]")

            print("\n4. 📱 Browser will stay open for manual testing...")
            print("   Press Ctrl+C in terminal to close when done")

            # Keep browser open for manual testing
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Closing browser...")

        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            if 'browser' in locals():
                await browser.close()


def open_clean_browser_for_facebook_sync():
    """
    Open a clean browser for manual Facebook testing (sync version)
    """
    print("🌐 Opening Clean Browser for Facebook Test (Playwright Sync)")
    print("=" * 60)
    print("This will open a fresh browser window where you can:")
    print("• Manually log into Facebook")
    print("• Navigate to Messages")
    print("• Test selectors manually")
    print("=" * 60)

    with sync_playwright() as p:
        try:
            print("🔧 Setting up Playwright browser...")

            # Launch browser with anti-detection settings
            browser = p.chromium.launch(
                headless=False,  # Show browser window
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions",
                    "--no-first-run",
                    "--disable-default-apps"
                ]
            )

            # Create context with realistic settings
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York"
            )

            # Create page
            page = context.new_page()

            # Remove automation detection
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)

            print("✅ Browser opened successfully!")
            print("\n📋 Manual Test Instructions:")
            print("=" * 40)

            # Navigate to Facebook
            print("1. 🌐 Navigating to Facebook...")
            page.goto("https://www.facebook.com", wait_until="domcontentloaded")

            current_url = page.url
            page_title = page.title()

            print(f"   Current URL: {current_url}")
            print(f"   Page Title: {page_title}")

            print("\n2. 🔍 Manual Login Instructions:")
            print("   - Enter your Facebook credentials manually")
            print("   - Complete any security checks if prompted")
            print("   - Navigate to different sections to test")

            print("\n3. 🧪 Testing Available CSS Selectors:")
            print("   Email input selectors to test:")
            print("   - input[name=\"email\"]")
            print("   - input[type=\"email\"]")
            print("   - input[id=\"email\"]")

            print("\n   Password input selectors to test:")
            print("   - input[name=\"pass\"]")
            print("   - input[type=\"password\"]")
            print("   - input[id=\"pass\"]")

            print("\n   Login button selectors to test:")
            print("   - button[name=\"login\"]")
            print("   - button[type=\"submit\"]")
            print("   - button[data-testid=\"royal_login_button\"]")

            print("\n4. 📱 Browser will stay open for manual testing...")
            print("   Press Ctrl+C in terminal to close when done")

            # Keep browser open for manual testing
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Closing browser...")

        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            if 'browser' in locals():
                browser.close()


def main():
    """
    Main entry point - choose between async or sync version
    """
    print("🚀 Facebook Test Browser Launcher (Playwright)")
    print("Choose version:")
    print("1. Async version (recommended)")
    print("2. Sync version")

    try:
        choice = input("\nEnter choice (1 or 2): ").strip()

        if choice == "1":
            asyncio.run(open_clean_browser_for_facebook_async())
        elif choice == "2":
            open_clean_browser_for_facebook_sync()
        else:
            print("Invalid choice. Using async version...")
            asyncio.run(open_clean_browser_for_facebook_async())

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()