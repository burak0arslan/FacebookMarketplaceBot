"""
Simple Visual Debug AI Bot - No Complex Profile Management
Watch your AI bot work in real-time with full visibility
"""

import time
from selenium.webdriver.common.by import By
from services.facebook_bot import FacebookBot
from services.excel_handler import ExcelHandler
from utils.logger import setup_logging, get_logger

def run_simple_visual_debug():
    """Run AI bot with simple visual debugging - see everything on screen"""

    setup_logging()
    logger = get_logger(__name__)

    print("🖥️ SIMPLE VISUAL DEBUG MODE - AI-Powered Facebook Bot")
    print("=" * 60)
    print("🔧 Using simple approach to avoid conflicts")
    print("You'll see EVERYTHING on screen:")
    print("✅ Browser window (non-headless)")
    print("✅ Real Facebook interface")
    print("✅ Step-by-step navigation")
    print("✅ Message detection process")
    print("✅ AI response generation")
    print("=" * 60)

    try:
        # Load data
        excel_handler = ExcelHandler()

        # Load products for AI context
        products = excel_handler.load_products("data/sample_data/sample_products.xlsx")
        print(f"📦 Loaded {len(products)} products for AI context")

        # Load accounts
        accounts = excel_handler.load_accounts("data/sample_data/sample_accounts.xlsx")
        usable_accounts = [acc for acc in accounts if acc.is_usable()]

        if not usable_accounts:
            print("❌ No usable accounts found!")
            print("💡 Update data/sample_data/sample_accounts.xlsx with real credentials")
            return

        account = usable_accounts[0]
        print(f"👤 Using account: {account.get_masked_email()}")

        # Create bot with simple approach (headless=False for visual)
        print(f"\n🖥️ Creating visual bot...")
        bot = FacebookBot(account, headless=False)  # Visual mode

        print("🐌 Running in slow mode for better visibility...")

        print("\n🌐 Step 1: Starting Facebook session...")
        if bot.start_session():
            print("✅ Successfully logged into Facebook!")
            print("👀 Check the browser window - you should see Facebook loaded")

            input("Press Enter to continue to Messages (skip Marketplace for now)...")

            print("\n📨 Step 2: Navigating to Messages...")
            # Navigate directly to messages for debugging
            result = navigate_to_messages_simple(bot)
            if result:
                print("✅ Navigated to Messages!")
                print("👀 Browser should now show Messages interface")

                input("Press Enter to start message detection...")

                print("\n" + "=" * 60)
                print("🔍 VISUAL MESSAGE DETECTION MODE")
                print("=" * 60)
                print("Watch the browser as we:")
                print("1. 🔍 Analyze the current page")
                print("2. 📨 Search for conversation elements")
                print("3. 🎯 Look specifically for your vanity message")
                print("4. 🤖 Test AI integration")
                print("=" * 60)

                # Visual debugging cycles
                for cycle in range(1, 4):  # 3 cycles for debugging
                    print(f"\n🔄 === VISUAL ANALYSIS CYCLE #{cycle} ===")

                    # Step-by-step visual debugging
                    print("👀 Step 1: Analyzing current page...")
                    analyze_facebook_page(bot)

                    input("Press Enter to continue to conversation detection...")

                    print("👀 Step 2: Looking for conversation elements...")
                    debug_conversations_simple(bot)

                    input("Press Enter to search for vanity message...")

                    print("👀 Step 3: Searching for your vanity message...")
                    vanity_found = search_vanity_simple(bot)

                    if vanity_found:
                        print("🎉 VANITY MESSAGE FOUND! Let's try AI processing...")

                        input("Press Enter to test AI processing...")

                        print("👀 Step 4: Testing AI message processing...")
                        test_ai_processing_simple(bot, products)

                        break
                    else:
                        print("❌ Vanity message not found on current view")
                        print("💡 Let's try navigating to different message views...")

                        try_different_message_views(bot)

                    if cycle < 3:
                        input(f"Press Enter for cycle #{cycle + 1} or Ctrl+C to stop...")

                print("\n✅ Visual debugging completed!")

            else:
                print("❌ Failed to navigate to messages")
                debug_navigation_issues(bot)
        else:
            print("❌ Failed to log into Facebook")
            debug_login_issues(bot)

        print("\n🧹 Cleaning up...")
        input("Press Enter to close browser and finish...")
        bot.end_session()

    except KeyboardInterrupt:
        print("\n🛑 Visual debugging stopped by user")
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()


def navigate_to_messages_simple(bot):
    """Simple navigation to messages with visual feedback"""
    print("   🌐 Navigating to Facebook Messages...")

    try:
        # Direct URL navigation
        messages_url = "https://www.facebook.com/messages"
        print(f"   📍 Going to: {messages_url}")

        if bot.browser.navigate_to(messages_url):
            print("   ✅ Navigation command successful")
            time.sleep(5)  # Wait for load

            current_url = bot.browser.driver.current_url
            print(f"   📍 Current URL: {current_url}")

            return True
        else:
            print("   ❌ Navigation failed")
            return False

    except Exception as e:
        print(f"   ❌ Navigation error: {e}")
        return False


def analyze_facebook_page(bot):
    """Analyze what's currently on the Facebook page"""
    try:
        print("   🔍 Analyzing current Facebook page...")

        analysis_script = """
        return {
            url: window.location.href,
            title: document.title,
            bodyTextSample: document.body.textContent.substring(0, 500),
            keywords: {
                hasMessenger: document.body.textContent.toLowerCase().includes('messenger'),
                hasMessages: document.body.textContent.toLowerCase().includes('message'),
                hasVanity: document.body.textContent.toLowerCase().includes('vanity'),
                hasMarketplace: document.body.textContent.toLowerCase().includes('marketplace'),
                hasConversation: document.body.textContent.toLowerCase().includes('conversation')
            },
            elementCounts: {
                totalDivs: document.querySelectorAll('div').length,
                totalLinks: document.querySelectorAll('a').length,
                totalButtons: document.querySelectorAll('button').length,
                inputFields: document.querySelectorAll('input').length
            }
        };
        """

        analysis = bot.browser.driver.execute_script(analysis_script)

        print(f"   📍 URL: {analysis['url']}")
        print(f"   📄 Title: {analysis['title']}")
        print(f"   📊 Elements: {analysis['elementCounts']['totalDivs']} divs, {analysis['elementCounts']['totalLinks']} links")

        print("   🔍 Page Content Analysis:")
        for keyword, found in analysis['keywords'].items():
            status = "✅" if found else "❌"
            print(f"     {status} {keyword}: {found}")

        if analysis['keywords']['hasVanity']:
            print("   🎉 🎉 VANITY KEYWORD DETECTED ON PAGE! 🎉 🎉")

        print(f"   📝 Page text sample: {analysis['bodyTextSample'][:150]}...")

        return analysis

    except Exception as e:
        print(f"   ❌ Page analysis error: {e}")
        return None


def debug_conversations_simple(bot):
    """Simple conversation detection with visual highlighting"""
    try:
        print("   🔍 Searching for conversation elements...")

        # Test various selectors and highlight results
        conversation_script = """
        var selectors = [
            '[role="grid"]',
            '[data-testid*="conversation"]',
            'div[role="link"]',
            'a[href*="/t/"]',
            '[aria-label*="conversation"]',
            '[data-testid*="message"]',
            'div[data-testid*="chat"]'
        ];
        
        var results = [];
        var colors = ['red', 'blue', 'green', 'purple', 'orange', 'cyan', 'magenta'];
        
        selectors.forEach(function(selector, index) {
            var elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                results.push({
                    selector: selector,
                    count: elements.length,
                    samples: Array.from(elements).slice(0, 3).map(el => ({
                        text: el.textContent.substring(0, 80),
                        tag: el.tagName,
                        hasVanity: el.textContent.toLowerCase().includes('vanity')
                    }))
                });
                
                // Highlight with different colors
                var color = colors[index % colors.length];
                for (var i = 0; i < Math.min(5, elements.length); i++) {
                    elements[i].style.border = '2px solid ' + color;
                    elements[i].style.outline = '1px solid ' + color;
                }
            }
        });
        
        return results;
        """

        results = bot.browser.driver.execute_script(conversation_script)

        if results:
            print("   ✅ Found conversation-related elements:")
            vanity_found_in_conversations = False

            for result in results:
                print(f"     🎯 {result['selector']}: {result['count']} elements")

                for i, sample in enumerate(result['samples']):
                    if sample['text'].strip():
                        vanity_indicator = "🎯 VANITY! " if sample['hasVanity'] else ""
                        print(f"       {vanity_indicator}Sample {i+1}: {sample['text'][:50]}...")
                        if sample['hasVanity']:
                            vanity_found_in_conversations = True

            if vanity_found_in_conversations:
                print("   🎉 🎉 VANITY FOUND IN CONVERSATION ELEMENTS! 🎉 🎉")

            print("   👀 Check browser - elements highlighted in different colors")
            time.sleep(3)

            return results
        else:
            print("   ❌ No conversation elements found")
            return []

    except Exception as e:
        print(f"   ❌ Conversation detection error: {e}")
        return []


def search_vanity_simple(bot):
    """Simple search for vanity message with bright highlighting"""
    try:
        print("   🎯 Searching specifically for 'vanity' message...")

        vanity_script = """
        var vanityElements = [];
        var allElements = document.querySelectorAll('*');
        var vanityCount = 0;
        
        // Search through all elements
        for (var i = 0; i < allElements.length; i++) {
            var element = allElements[i];
            var text = element.textContent || '';
            
            if (text.toLowerCase().includes('vanity') && text.length > 5 && text.length < 500) {
                vanityCount++;
                vanityElements.push({
                    tagName: element.tagName,
                    text: text.substring(0, 150),
                    className: element.className,
                    parentText: element.parentElement ? element.parentElement.textContent.substring(0, 100) : ''
                });
                
                // Highlight vanity elements with bright colors
                element.style.border = '5px solid lime';
                element.style.backgroundColor = 'yellow';
                element.style.color = 'black';
                element.style.fontWeight = 'bold';
                element.style.zIndex = '9999';
                element.style.position = 'relative';
                
                // Add a label
                var label = document.createElement('div');
                label.textContent = 'VANITY MESSAGE #' + vanityCount;
                label.style.backgroundColor = 'red';
                label.style.color = 'white';
                label.style.padding = '2px 5px';
                label.style.fontSize = '12px';
                label.style.position = 'absolute';
                label.style.top = '-20px';
                label.style.left = '0';
                label.style.zIndex = '10000';
                element.style.position = 'relative';
                element.appendChild(label);
            }
        }
        
        return {
            found: vanityElements.length > 0,
            count: vanityElements.length,
            elements: vanityElements.slice(0, 5)  // First 5 for display
        };
        """

        vanity_results = bot.browser.driver.execute_script(vanity_script)

        if vanity_results['found']:
            print(f"   🎉 🎉 FOUND {vanity_results['count']} VANITY REFERENCES! 🎉 🎉")
            print("   👀 Check browser - vanity elements highlighted in BRIGHT YELLOW with RED labels")

            for i, element in enumerate(vanity_results['elements']):
                print(f"     🎯 Vanity #{i+1} ({element['tagName']}): {element['text'][:100]}...")
                if element['parentText'] and element['parentText'] != element['text']:
                    print(f"       Context: {element['parentText'][:60]}...")

            print("   ⏳ Pausing 8 seconds to show highlights...")
            time.sleep(8)  # Longer pause for vanity highlights

            return True
        else:
            print("   ❌ No 'vanity' text found on current page")
            return False

    except Exception as e:
        print(f"   ❌ Vanity search error: {e}")
        return False


def test_ai_processing_simple(bot, products):
    """Simple test of AI processing capabilities"""
    try:
        print("   🤖 Testing AI processing...")

        # Check if AI methods are available
        if hasattr(bot, 'start_ai_powered_monitoring'):
            print("   ✅ AI methods available on bot")

            try:
                # Try to start AI monitoring
                if not hasattr(bot, 'ai_processor'):
                    print("   🤖 Starting AI processor...")
                    bot.start_ai_powered_monitoring(products)
                    print("   ✅ AI processor started")
                else:
                    print("   ✅ AI processor already running")

                # Try processing
                print("   🔄 Attempting AI message processing...")
                results = bot.process_messages_with_ai()

                if 'error' in results:
                    print(f"   ❌ AI Error: {results['error']}")
                else:
                    monitoring = results.get('monitoring_stats', {})
                    ai_stats = results.get('ai_stats', {})

                    new_messages = monitoring.get('new_messages', 0)
                    if new_messages > 0:
                        print(f"   🎉 AI FOUND {new_messages} NEW MESSAGES!")
                        print(f"   🤖 AI responses: {ai_stats.get('ai_responses_sent', 0)}")
                        print(f"   ⚠️ Escalations: {ai_stats.get('escalations', 0)}")
                    else:
                        print("   📭 AI system: No new messages detected")
                        print("   💡 This might be because the selectors need updating")

                print(f"   📊 Total AI processed: {ai_stats.get('messages_processed', 0)}")

            except Exception as e:
                print(f"   ❌ AI processing error: {e}")

        else:
            print("   ⚠️ AI methods not available - testing basic detection")

            # Create a simulated message for AI testing
            try:
                from models.message import Message
                test_message = Message.create_customer_message(
                    "Hi! Is the vanity still available? How much?",
                    "Test Customer",
                    "test_conv_123"
                )

                print(f"   🧪 Created test message: {test_message.content}")
                print(f"   📊 Priority: {test_message.get_priority_score()}")
                print(f"   ❓ Contains question: {test_message.contains_question}")
                print(f"   💰 Price inquiry: {test_message.contains_price_inquiry}")

            except Exception as e:
                print(f"   ❌ Test message creation error: {e}")

    except Exception as e:
        print(f"   ❌ AI testing error: {e}")


def try_different_message_views(bot):
    """Try navigating to different message views"""
    print("   🔄 Trying different message views...")

    message_urls = [
        "https://www.facebook.com/messages/t/",
        "https://www.facebook.com/messages?folder=inbox",
        "https://www.facebook.com/messages?folder=other"
    ]

    for url in message_urls:
        try:
            print(f"   📍 Trying: {url}")
            bot.browser.navigate_to(url)
            time.sleep(3)

            # Quick vanity check
            vanity_check = bot.browser.driver.execute_script(
                "return document.body.textContent.toLowerCase().includes('vanity');"
            )

            if vanity_check:
                print(f"   🎉 Found vanity at: {url}")
                return True

        except Exception as e:
            print(f"   ❌ Error with {url}: {e}")

    return False


def debug_navigation_issues(bot):
    """Debug navigation issues"""
    print("   🔧 Debugging navigation issues...")

    try:
        current_url = bot.browser.driver.current_url
        print(f"   📍 Current URL: {current_url}")

        # Check page type
        page_check = bot.browser.driver.execute_script("""
        return {
            title: document.title,
            hasNav: document.querySelector('nav') !== null,
            hasHeader: document.querySelector('header') !== null,
            bodyText: document.body.textContent.substring(0, 200)
        };
        """)

        print(f"   📄 Page: {page_check['title']}")
        print(f"   🧭 Has navigation: {page_check['hasNav']}")
        print(f"   📝 Sample text: {page_check['bodyText']}")

    except Exception as e:
        print(f"   ❌ Debug error: {e}")


def debug_login_issues(bot):
    """Debug login issues"""
    print("   🔧 Debugging login issues...")

    try:
        if bot.browser and bot.browser.driver:
            current_url = bot.browser.driver.current_url
            print(f"   📍 Current URL: {current_url}")

            login_check = bot.browser.driver.execute_script("""
            return {
                hasEmailField: document.querySelector('input[type="email"]') !== null,
                hasPasswordField: document.querySelector('input[type="password"]') !== null,
                hasUserMenu: document.querySelector('[data-testid="user_menu"]') !== null,
                pageTitle: document.title
            };
            """)

            print(f"   📧 Email field: {login_check['hasEmailField']}")
            print(f"   🔒 Password field: {login_check['hasPasswordField']}")
            print(f"   👤 User menu: {login_check['hasUserMenu']}")
            print(f"   📄 Title: {login_check['pageTitle']}")

        else:
            print("   ❌ Browser not available")

    except Exception as e:
        print(f"   ❌ Login debug error: {e}")


if __name__ == "__main__":
    print("🖥️ Starting SIMPLE Visual Debug Mode...")
    print("🔧 No complex profile management - just pure visual debugging")
    print("Make sure you can see the browser window!")

    input("Press Enter to start simple visual debugging...")
    run_simple_visual_debug()