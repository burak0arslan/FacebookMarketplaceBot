"""
Complete AI-Powered Facebook Marketplace Bot
Your bot is now fully intelligent and ready for production!
"""

import time
from services.facebook_bot import FacebookBot
from services.excel_handler import ExcelHandler
from utils.logger import setup_logging, get_logger


def run_intelligent_bot():
    """Run your complete AI-powered marketplace bot"""

    # Setup
    setup_logging()
    logger = get_logger(__name__)

    logger.info("🚀 Starting AI-Powered Facebook Marketplace Bot")
    logger.info("=" * 60)

    try:
        # Load data
        excel_handler = ExcelHandler()

        # Load products for AI context
        products = excel_handler.load_products("data/sample_data/sample_products.xlsx")
        logger.info(f"📦 Loaded {len(products)} products for AI context")

        # Load accounts
        accounts = excel_handler.load_accounts("data/sample_data/sample_accounts.xlsx")
        usable_accounts = [acc for acc in accounts if acc.is_usable()]
        logger.info(f"👤 Found {len(usable_accounts)} usable accounts")

        if not usable_accounts:
            logger.error("❌ No usable accounts found!")
            logger.info("💡 Update data/sample_data/sample_accounts.xlsx with real credentials")
            return

        # Create AI-powered bot
        account = usable_accounts[0]
        logger.info(f"🤖 Creating AI bot for {account.get_masked_email()}")

        bot = FacebookBot(account, headless=False)  # Set to True for production

        # Start Facebook session
        logger.info("🌐 Starting Facebook session...")
        if bot.start_session():
            logger.info("✅ Successfully logged into Facebook!")

            # Navigate to marketplace
            if bot.navigate_to_marketplace():
                logger.info("✅ Navigated to Facebook Marketplace!")

                # Start AI-powered monitoring
                logger.info("🤖 Starting AI-powered message monitoring...")
                if bot.start_ai_powered_monitoring(products):
                    logger.info("🎉 AI-POWERED BOT IS NOW RUNNING!")
                    logger.info("=" * 60)
                    logger.info("Your bot will now:")
                    logger.info("🤖 Generate intelligent responses to customer questions")
                    logger.info("🛡️ Escalate problematic messages to humans")
                    logger.info("💬 Remember conversation context")
                    logger.info("📦 Use product knowledge in responses")
                    logger.info("=" * 60)

                    # Main bot loop
                    cycle_count = 0
                    while True:
                        try:
                            cycle_count += 1
                            logger.info(f"\n🔄 Monitoring Cycle #{cycle_count}")

                            # Process messages with AI
                            results = bot.process_messages_with_ai()

                            if 'error' in results:
                                logger.error(f"Processing error: {results['error']}")
                            else:
                                # Display results
                                monitoring = results.get('monitoring_stats', {})
                                ai = results.get('ai_stats', {})

                                new_messages = monitoring.get('new_messages', 0)
                                if new_messages > 0:
                                    logger.info(f"📨 {new_messages} new messages processed")
                                    logger.info(f"🤖 AI responses: {ai.get('ai_responses_sent', 0)}")
                                    logger.info(f"⚠️ Escalations: {ai.get('escalations', 0)}")
                                    logger.info(f"💬 Fallbacks: {ai.get('fallback_responses', 0)}")
                                else:
                                    logger.info("📭 No new messages")

                                # Show overall stats
                                logger.info(f"📊 Total processed: {ai.get('messages_processed', 0)}")

                            # Wait before next cycle
                            logger.info("⏳ Waiting 30 seconds for next cycle...")
                            time.sleep(30)

                        except KeyboardInterrupt:
                            logger.info("\n🛑 Stopping bot (Ctrl+C pressed)")
                            break
                        except Exception as e:
                            logger.error(f"Cycle error: {e}")
                            logger.info("Continuing...")
                            time.sleep(30)

                else:
                    logger.error("❌ Failed to start AI monitoring")
            else:
                logger.error("❌ Failed to navigate to marketplace")
        else:
            logger.error("❌ Failed to log into Facebook")
            logger.info("💡 Make sure your account credentials are correct")

        # Cleanup
        logger.info("🧹 Cleaning up...")
        bot.end_session()
        logger.info("✅ Bot session ended cleanly")

    except Exception as e:
        logger.error(f"💥 Bot error: {e}")

    logger.info("🏁 AI-Powered Bot finished")


def demo_ai_responses():
    """Demo the AI response capabilities without Facebook"""

    setup_logging()
    logger = get_logger(__name__)

    logger.info("🎬 DEMO: AI Response Capabilities")
    logger.info("=" * 50)

    try:
        from services.llama_ai import create_llama_ai
        from services.ai_message_processor import AIMessageProcessor
        from models.message import Message
        from models.product import Product

        # Create AI service
        ai = create_llama_ai()

        # Create sample product
        product = Product(
            title="iPhone 13 Pro - Excellent Condition",
            description="Barely used iPhone 13 Pro in excellent condition. Deep Purple color, 256GB storage.",
            price=650.0,
            category="Electronics",
            condition="Used - Like New"
        )

        # Create processor
        processor = AIMessageProcessor(ai, [product])

        # Demo conversations
        demo_messages = [
            "Hi! Is this iPhone still available?",
            "What's your best price on this?",
            "Can I see it today?",
            "What condition is it in?",
            "This is a scam! I want my money back!",  # Should escalate
            "Does it come with a charger?"
        ]

        logger.info("🤖 Demonstrating AI responses:")
        logger.info("=" * 50)

        for i, msg_content in enumerate(demo_messages, 1):
            logger.info(f"\n💬 Demo {i}: Customer says: '{msg_content}'")

            # Create message
            message = Message.create_customer_message(
                msg_content,
                f"Demo Customer {i}",
                f"demo_conv_{i}"
            )

            # Process with AI
            result = processor.process_message(message)

            # Show result
            action = result.get('action_taken', 'none')
            response = result.get('response_generated', 'No response')

            if action == 'escalated':
                logger.warning(f"🚨 ESCALATED: {response}")
            elif action == 'ai_response':
                logger.info(f"🤖 AI Response: {response}")
            elif action == 'fallback_response':
                logger.info(f"💬 Fallback: {response}")
            else:
                logger.info(f"📭 Ignored message")

        # Show statistics
        stats = processor.get_statistics()
        logger.info(f"\n📊 Demo Statistics:")
        logger.info(f"Messages processed: {stats['messages_processed']}")
        logger.info(f"AI responses: {stats['ai_responses_sent']}")
        logger.info(f"Escalations: {stats['escalations']}")
        logger.info(f"Fallbacks: {stats['fallback_responses']}")

        logger.info("\n🎉 Demo completed! Your AI is working perfectly!")

    except Exception as e:
        logger.error(f"Demo error: {e}")


if __name__ == "__main__":
    import sys

    print("🤖 AI-Powered Facebook Marketplace Bot")
    print("=" * 50)
    print("Choose an option:")
    print("1. 🎬 Demo AI responses (safe, no Facebook)")
    print("2. 🚀 Run full AI-powered bot (requires Facebook login)")
    print("3. 🧪 Exit")

    choice = input("\nEnter choice (1/2/3): ").strip()

    if choice == "1":
        demo_ai_responses()
    elif choice == "2":
        print("\n⚠️ WARNING: This will connect to real Facebook!")
        print("Make sure you have valid credentials in sample_accounts.xlsx")
        confirm = input("Continue? (y/n): ")
        if confirm.lower() == 'y':
            run_intelligent_bot()
        else:
            print("Cancelled.")
    elif choice == "3":
        print("👋 Goodbye!")
    else:
        print("Invalid choice!")