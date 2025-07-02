#!/usr/bin/env python3
"""
Live Facebook Integration - Real Account Setup
This script helps you safely connect to real Facebook accounts for live monitoring
"""

import sys
import os
import time
import getpass
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.account import Account
from services.facebook_bot import FacebookBot
from services.llama_ai import LlamaAI
from utils.browser_utils import create_browser_manager
from utils.logger import setup_logging, get_logger
from config import Config


class LiveFacebookIntegration:
    """
    Safely integrate with real Facebook accounts for live monitoring

    Features:
    - Secure account validation
    - Real Facebook login testing
    - Live message monitoring setup
    - Safety checks and recommendations
    - Account health monitoring
    """

    def __init__(self):
        """Initialize live integration manager"""
        setup_logging()
        self.logger = get_logger(__name__)

        # Test accounts
        self.test_accounts: List[Account] = []
        self.validated_accounts: List[Account] = []

        # System components
        self.ai_service = LlamaAI()

        # Safety settings
        self.safety_mode = True
        self.max_test_accounts = 2
        self.login_timeout = 60  # seconds

    def create_secure_test_account(self) -> Optional[Account]:
        """
        Safely create a test account with real credentials
        """
        print("\n🔐 Setting Up Real Facebook Account")
        print("=" * 50)
        print("⚠️  IMPORTANT SECURITY NOTES:")
        print("   • Only use accounts you own or have permission to use")
        print("   • Consider using secondary/business accounts for testing")
        print("   • Never share credentials or use someone else's account")
        print("   • Start with 1-2 accounts maximum for testing")
        print()

        try:
            # Get account information securely
            email = input("📧 Facebook Email: ").strip()
            if not email or '@' not in email:
                print("❌ Invalid email format")
                return None

            # Secure password input
            password = getpass.getpass("🔒 Facebook Password: ").strip()
            if not password:
                print("❌ Password cannot be empty")
                return None

            profile_name = input("👤 Profile Name (display name): ").strip()
            if not profile_name:
                profile_name = email.split('@')[0].title()

            # Create account object
            account = Account(
                email=email,
                password=password,
                profile_name=profile_name,
                active=True,
                message_monitor=True
            )

            print(f"✅ Account created: {account.get_masked_email()}")
            return account

        except KeyboardInterrupt:
            print("\n⏹️ Account setup cancelled")
            return None
        except Exception as e:
            print(f"❌ Error creating account: {e}")
            return None

    def test_facebook_login(self, account: Account) -> bool:
        """
        Test Facebook login with real account

        Args:
            account: Account to test

        Returns:
            True if login successful, False otherwise
        """
        try:
            print(f"\n🔐 Testing login for {account.get_masked_email()}")
            print("⏳ This may take 30-60 seconds...")

            # Create browser in non-headless mode for login testing
            with create_browser_manager(headless=False) as browser:
                # Initialize Facebook bot
                bot = FacebookBot(account, headless=False)
                bot.browser = browser

                print("🌐 Opening Facebook...")

                # Navigate to Facebook
                if not browser.navigate_to("https://www.facebook.com"):
                    print("❌ Could not navigate to Facebook")
                    return False

                time.sleep(3)

                # Attempt login via session start
                print("🔑 Attempting login...")
                login_success = bot.start_session()

                if login_success:
                    print("✅ Login successful!")

                    # Test navigation to key areas
                    print("🔍 Testing navigation...")

                    # Test marketplace access
                    if bot.navigate_to_marketplace():
                        print("✅ Marketplace access confirmed")
                    else:
                        print("⚠️ Marketplace access limited")

                    # Test messages access
                    if hasattr(bot, 'navigate_to_messages'):
                        if bot.navigate_to_messages():
                            print("✅ Messages access confirmed")
                        else:
                            print("⚠️ Messages access limited")

                    # End session properly
                    bot.end_session()

                    print("🎉 Account validation successful!")
                    return True
                else:
                    print("❌ Login failed")
                    self._diagnose_login_failure(browser)
                    return False

        except Exception as e:
            print(f"❌ Login test error: {e}")
            return False

    def _diagnose_login_failure(self, browser):
        """Diagnose why login might have failed"""
        try:
            # Check for common login issues
            page_source = browser.driver.page_source.lower()

            if "captcha" in page_source:
                print("🔍 Diagnosis: CAPTCHA detected")
                print("   💡 Solution: Complete CAPTCHA manually and try again")
            elif "checkpoint" in page_source or "security" in page_source:
                print("🔍 Diagnosis: Security checkpoint detected")
                print("   💡 Solution: Complete security verification manually")
            elif "incorrect" in page_source or "wrong" in page_source:
                print("🔍 Diagnosis: Incorrect credentials")
                print("   💡 Solution: Verify email and password are correct")
            elif "locked" in page_source or "disabled" in page_source:
                print("🔍 Diagnosis: Account may be locked or disabled")
                print("   💡 Solution: Try logging in manually first")
            else:
                print("🔍 Diagnosis: Unknown login issue")
                print("   💡 Solution: Try logging in manually first")

        except Exception as e:
            print(f"Could not diagnose login failure: {e}")

    def setup_live_monitoring_session(self, validated_accounts: List[Account]) -> bool:
        """
        Set up live monitoring session with real accounts

        Args:
            validated_accounts: List of validated Facebook accounts

        Returns:
            True if setup successful, False otherwise
        """
        try:
            print(f"\n🚀 Setting Up Live Monitoring Session")
            print("=" * 50)
            print(f"👥 Accounts: {len(validated_accounts)}")

            # Test AI system
            if not self.ai_service.test_connection():
                print("❌ AI system not available - monitoring will be limited")
                return False

            print("✅ AI system ready")

            # Initialize bots for live monitoring
            active_bots = {}

            for account in validated_accounts:
                try:
                    print(f"🤖 Setting up live bot for {account.get_masked_email()}")

                    # Create bot instance
                    bot = FacebookBot(account, headless=False)  # Non-headless for live monitoring
                    active_bots[account.email] = bot

                    print(f"✅ Bot ready for {account.get_masked_email()}")

                except Exception as e:
                    print(f"❌ Error setting up bot for {account.get_masked_email()}: {e}")
                    continue

            if not active_bots:
                print("❌ No bots successfully set up")
                return False

            print(f"✅ {len(active_bots)} bots ready for live monitoring")

            # Show monitoring configuration
            print(f"\n⚙️ Live Monitoring Configuration:")
            print(f"   Check interval: {Config.MESSAGE_CHECK_INTERVAL} seconds")
            print(f"   Auto-reply: {'✅ Enabled' if Config.AUTO_REPLY_ENABLED else '❌ Disabled'}")
            print(f"   Reply delay: {Config.REPLY_DELAY_MIN}-{Config.REPLY_DELAY_MAX} seconds")
            print(f"   AI model: {Config.LLAMA_MODEL_NAME}")

            return True

        except Exception as e:
            print(f"❌ Error setting up live monitoring: {e}")
            return False

    def run_live_monitoring_demo(self, duration_minutes: int = 5) -> bool:
        """
        Run a short live monitoring demonstration

        Args:
            duration_minutes: How long to run the demo

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"\n🎬 Running Live Monitoring Demo ({duration_minutes} minutes)")
            print("=" * 60)
            print("⚠️  DEMO MODE - SAFE TESTING:")
            print("   • Will monitor for real messages")
            print("   • Will generate AI responses")
            print("   • Will NOT send responses automatically")
            print("   • You can review and approve each response")
            print()

            input("Press Enter to start live demo...")

            # This would integrate with your existing monitoring system
            from phase4_message_monitoring import MessageMonitoringManager

            # Create monitoring manager in demo mode
            manager = MessageMonitoringManager()
            manager.auto_reply_enabled = False  # Disable auto-reply for demo

            # Load validated accounts
            manager.accounts = self.validated_accounts

            if not manager.test_ai_connection():
                print("❌ AI system not available")
                return False

            if not manager.initialize_bots():
                print("❌ Could not initialize bots")
                return False

            print("🚀 Starting live demo monitoring...")

            # Run monitoring with manual approval
            def demo_message_processor(message):
                """Process messages with manual approval"""
                print(f"\n📩 NEW MESSAGE DETECTED:")
                print(f"   From: {message.sender_name}")
                print(f"   Content: {message.content}")
                print(f"   Product: {message.product_title or 'Unknown'}")

                if message.requires_human_attention:
                    print("⚠️  Message requires human attention (escalated)")
                    return True

                # Generate AI response
                response = manager.generate_ai_response(message)

                if response:
                    print(f"\n🤖 PROPOSED AI RESPONSE:")
                    print(f"   '{response}'")

                    # Ask for approval
                    choice = input("\n   Send this response? [y/N/edit]: ").strip().lower()

                    if choice == 'y':
                        print("✅ Response approved - sending...")
                        # In real implementation, would send via manager.send_response()
                        print("📤 Response sent successfully (simulated)")
                        return True
                    elif choice == 'edit':
                        custom_response = input("   Enter custom response: ").strip()
                        if custom_response:
                            print(f"✅ Custom response: '{custom_response}'")
                            print("📤 Custom response sent (simulated)")
                            return True
                    else:
                        print("⏸️ Response skipped")
                        return True
                else:
                    print("❌ Could not generate AI response")
                    return False

            # Run monitoring cycles
            import time
            from datetime import datetime, timedelta

            end_time = datetime.now() + timedelta(minutes=duration_minutes)
            cycle = 0

            while datetime.now() < end_time:
                cycle += 1
                print(f"\n🔄 Live Monitoring Cycle {cycle}")
                print("-" * 30)

                # Run monitoring cycle
                stats = manager.run_monitoring_cycle()

                if stats['messages_found'] > 0:
                    print(f"📊 Found {stats['messages_found']} new messages")
                else:
                    print("📭 No new messages this cycle")

                # Wait before next cycle
                if datetime.now() < end_time:
                    wait_time = min(Config.MESSAGE_CHECK_INTERVAL, 30)  # Cap at 30s for demo
                    print(f"⏸️ Waiting {wait_time}s before next cycle...")
                    time.sleep(wait_time)

            print("\n🏁 Live monitoring demo completed!")
            return True

        except KeyboardInterrupt:
            print("\n⏹️ Live demo stopped by user")
            return True
        except Exception as e:
            print(f"❌ Error in live demo: {e}")
            return False

    def create_live_deployment_guide(self):
        """Create a guide for full live deployment"""
        print("\n📋 LIVE DEPLOYMENT GUIDE")
        print("=" * 50)

        print("\n🎯 For Full Live Deployment:")
        print("1. ✅ Accounts Validated - Your accounts are ready")
        print("2. 🔧 Update Configuration:")
        print("   • Set AUTO_REPLY_ENABLED=True in config")
        print("   • Adjust MESSAGE_CHECK_INTERVAL as needed")
        print("   • Configure REPLY_DELAY_MIN/MAX for your use case")

        print("\n3. 🚀 Launch Live System:")
        print("   • Run: python phase4_message_monitoring.py")
        print("   • Choose longer monitoring duration (60+ minutes)")
        print("   • Monitor performance and adjust as needed")

        print("\n4. 📊 Monitor and Optimize:")
        print("   • Check logs/bot.log for detailed activity")
        print("   • Monitor AI response quality and customer satisfaction")
        print("   • Adjust AI prompts if needed")
        print("   • Scale to additional accounts as needed")

        print("\n⚠️  IMPORTANT CONSIDERATIONS:")
        print("   • Start with short monitoring sessions (30-60 minutes)")
        print("   • Monitor Facebook account health")
        print("   • Be responsive to customer escalations")
        print("   • Comply with Facebook's Terms of Service")
        print("   • Keep human oversight for complex situations")


def main():
    """Main execution function"""
    print("🔐 Facebook Marketplace Bot - Live Integration Setup")
    print("=" * 60)
    print("This will help you connect to real Facebook accounts for live monitoring.")
    print()

    integrator = LiveFacebookIntegration()

    print("🎯 SETUP PROCESS:")
    print("1. Create secure test account")
    print("2. Validate Facebook login")
    print("3. Test live monitoring")
    print("4. Deploy full system")
    print()

    # Step 1: Create test account
    test_account = integrator.create_secure_test_account()
    if not test_account:
        print("❌ Account setup failed. Cannot proceed.")
        return False

    integrator.test_accounts.append(test_account)

    # Step 2: Validate login
    print(f"\n🧪 Validating account {test_account.get_masked_email()}")
    if integrator.test_facebook_login(test_account):
        integrator.validated_accounts.append(test_account)
        print("✅ Account validation successful!")
    else:
        print("❌ Account validation failed.")
        print("\n💡 TROUBLESHOOTING TIPS:")
        print("• Try logging into Facebook manually first")
        print("• Complete any security verifications")
        print("• Ensure account is not locked or restricted")
        print("• Check for CAPTCHA requirements")
        return False

    # Step 3: Setup live monitoring
    if not integrator.setup_live_monitoring_session(integrator.validated_accounts):
        print("❌ Live monitoring setup failed.")
        return False

    # Step 4: Demo or deploy
    print(f"\n🎬 NEXT STEP:")
    choice = input("Run live monitoring demo? [Y/n]: ").strip().lower()

    if choice != 'n':
        try:
            duration = input("Demo duration in minutes [5]: ").strip()
            duration = int(duration) if duration else 5
        except:
            duration = 5

        success = integrator.run_live_monitoring_demo(duration)

        if success:
            integrator.create_live_deployment_guide()
            print("\n🎉 Live integration setup completed successfully!")
            print("Your system is ready for full live deployment!")
            return True
    else:
        integrator.create_live_deployment_guide()
        print("\n✅ Live integration setup completed!")
        return True


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🚀 Ready for live Facebook monitoring!")
        else:
            print("\n❌ Live integration setup encountered issues.")
    except KeyboardInterrupt:
        print("\n\n⏹️ Setup interrupted by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")