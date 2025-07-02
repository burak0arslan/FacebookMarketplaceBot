#!/usr/bin/env python3
"""
Account Health Monitor and Safety Checker
Monitors Facebook account health and provides safety recommendations
"""

import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.account import Account
from services.facebook_bot import FacebookBot
from utils.browser_utils import create_browser_manager
from utils.logger import setup_logging, get_logger
from config import Config


class AccountHealthMonitor:
    """
    Monitor Facebook account health and safety for automation

    Features:
    - Account restriction detection
    - Activity level monitoring
    - Safety compliance checking
    - Performance analytics
    - Health recommendations
    """

    def __init__(self):
        """Initialize account health monitor"""
        setup_logging()
        self.logger = get_logger(__name__)

        self.accounts: List[Account] = []
        self.health_reports: Dict[str, Dict] = {}

    def load_accounts_for_monitoring(self, accounts_file: str = None) -> bool:
        """Load accounts for health monitoring"""
        try:
            if not accounts_file:
                accounts_file = Config.DATA_DIR / "sample_data" / "sample_accounts.xlsx"

            from services.excel_handler import ExcelHandler
            handler = ExcelHandler()

            self.accounts = handler.load_accounts(str(accounts_file))
            active_accounts = [acc for acc in self.accounts if acc.is_usable()]

            self.logger.info(f"✅ Loaded {len(active_accounts)} accounts for monitoring")
            return len(active_accounts) > 0

        except Exception as e:
            self.logger.error(f"❌ Error loading accounts: {e}")
            return False

    def check_account_health(self, account: Account) -> Dict[str, Any]:
        """
        Check health status of a single account

        Args:
            account: Account to check

        Returns:
            Health report dictionary
        """
        health_report = {
            'account': account.get_masked_email(),
            'timestamp': datetime.now(),
            'status': 'unknown',
            'login_success': False,
            'marketplace_access': False,
            'messages_access': False,
            'restrictions_detected': False,
            'warnings': [],
            'recommendations': [],
            'overall_score': 0
        }

        try:
            self.logger.info(f"🔍 Checking health for {account.get_masked_email()}")

            with create_browser_manager(headless=True) as browser:
                bot = FacebookBot(account, headless=True)
                bot.browser = browser

                # Test login - use the correct FacebookBot method
                if browser.navigate_to("https://www.facebook.com"):
                    time.sleep(2)

                    # Try to start a session which includes login
                    if bot.start_session():
                        health_report['login_success'] = True
                        health_report['overall_score'] += 40
                        self.logger.info("✅ Login successful")

                        # Check for account restrictions
                        restrictions = self._check_for_restrictions(browser)
                        if restrictions:
                            health_report['restrictions_detected'] = True
                            health_report['warnings'].extend(restrictions)
                            health_report['overall_score'] -= 30

                        # Test marketplace access
                        if bot.navigate_to_marketplace():
                            health_report['marketplace_access'] = True
                            health_report['overall_score'] += 30
                            self.logger.info("✅ Marketplace access confirmed")
                        else:
                            health_report['warnings'].append("Limited marketplace access")
                            self.logger.warning("⚠️ Marketplace access limited")

                        # Test messages access
                        if hasattr(bot, 'navigate_to_messages'):
                            try:
                                if bot.navigate_to_messages():
                                    health_report['messages_access'] = True
                                    health_report['overall_score'] += 30
                                    self.logger.info("✅ Messages access confirmed")
                                else:
                                    health_report['warnings'].append("Limited messages access")
                            except:
                                health_report['warnings'].append("Messages access test failed")

                        # Determine overall status
                        if health_report['overall_score'] >= 80:
                            health_report['status'] = 'excellent'
                        elif health_report['overall_score'] >= 60:
                            health_report['status'] = 'good'
                        elif health_report['overall_score'] >= 40:
                            health_report['status'] = 'fair'
                        else:
                            health_report['status'] = 'poor'

                        # End the session properly
                        bot.end_session()

                    else:
                        health_report['status'] = 'login_failed'
                        health_report['warnings'].append("Login failed - check credentials")
                        self.logger.error("❌ Login failed")
                else:
                    health_report['warnings'].append("Could not navigate to Facebook")

            # Generate recommendations
            health_report['recommendations'] = self._generate_recommendations(health_report)

            return health_report

        except Exception as e:
            health_report['status'] = 'error'
            health_report['warnings'].append(f"Health check error: {str(e)}")
            self.logger.error(f"❌ Health check error: {e}")
            return health_report

    def _check_for_restrictions(self, browser) -> List[str]:
        """Check for account restrictions or warnings"""
        restrictions = []

        try:
            page_source = browser.driver.page_source.lower()

            # Common restriction indicators
            restriction_keywords = [
                ("account restricted", "Account has active restrictions"),
                ("temporarily blocked", "Account temporarily blocked"),
                ("verify your identity", "Identity verification required"),
                ("unusual activity", "Unusual activity detected"),
                ("community standards", "Community standards violation"),
                ("suspended", "Account suspended"),
                ("checkpoint", "Security checkpoint required"),
                ("captcha", "CAPTCHA verification needed")
            ]

            for keyword, message in restriction_keywords:
                if keyword in page_source:
                    restrictions.append(message)

            return restrictions

        except Exception as e:
            return [f"Could not check restrictions: {e}"]

    def _generate_recommendations(self, health_report: Dict) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []

        if not health_report['login_success']:
            recommendations.append("🔐 Verify account credentials and try manual login first")
            recommendations.append("🔒 Check if 2FA is enabled and causing login issues")

        if health_report['restrictions_detected']:
            recommendations.append("⚠️ Complete any required account verifications")
            recommendations.append("⏸️ Temporarily pause automation until restrictions are resolved")
            recommendations.append("📞 Contact Facebook support if restrictions persist")

        if not health_report['marketplace_access']:
            recommendations.append("🏪 Verify marketplace access by visiting manually")
            recommendations.append("📍 Ensure account location settings allow marketplace")

        if not health_report['messages_access']:
            recommendations.append("💬 Check messages privacy settings")
            recommendations.append("📱 Verify messenger access permissions")

        if health_report['overall_score'] < 60:
            recommendations.append("🚨 Account needs attention before automation")
            recommendations.append("⏳ Wait 24-48 hours and recheck account health")

        if health_report['status'] == 'excellent':
            recommendations.append("✅ Account ready for automation")
            recommendations.append("📊 Monitor regularly to maintain health")

        return recommendations

    def run_full_health_check(self) -> Dict[str, Any]:
        """Run health check on all accounts"""
        try:
            self.logger.info("🏥 Starting full account health check...")

            summary = {
                'timestamp': datetime.now(),
                'total_accounts': len(self.accounts),
                'accounts_checked': 0,
                'excellent': 0,
                'good': 0,
                'fair': 0,
                'poor': 0,
                'errors': 0,
                'recommendations': []
            }

            for account in self.accounts:
                if account.is_usable():
                    health_report = self.check_account_health(account)
                    self.health_reports[account.email] = health_report
                    summary['accounts_checked'] += 1

                    # Count by status
                    status = health_report['status']
                    if status == 'excellent':
                        summary['excellent'] += 1
                    elif status == 'good':
                        summary['good'] += 1
                    elif status == 'fair':
                        summary['fair'] += 1
                    elif status in ['poor', 'login_failed']:
                        summary['poor'] += 1
                    else:
                        summary['errors'] += 1

                    # Small delay between checks
                    time.sleep(5)

            # Generate overall recommendations
            if summary['poor'] > 0 or summary['errors'] > 0:
                summary['recommendations'].append("⚠️ Some accounts need attention before automation")

            if summary['excellent'] + summary['good'] >= summary['accounts_checked'] * 0.8:
                summary['recommendations'].append("✅ Most accounts ready for automation")

            if summary['accounts_checked'] == 0:
                summary['recommendations'].append("❌ No accounts available for health check")

            return summary

        except Exception as e:
            self.logger.error(f"❌ Full health check error: {e}")
            return {'error': str(e)}

    def display_health_report(self, summary: Dict):
        """Display comprehensive health report"""
        print("\n🏥 ACCOUNT HEALTH REPORT")
        print("=" * 50)
        print(f"📅 Report Date: {summary['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"👥 Accounts Checked: {summary['accounts_checked']}/{summary['total_accounts']}")
        print()

        # Status breakdown
        print("📊 Account Status Breakdown:")
        print(f"   ✅ Excellent: {summary['excellent']} accounts")
        print(f"   👍 Good: {summary['good']} accounts")
        print(f"   ⚠️ Fair: {summary['fair']} accounts")
        print(f"   ❌ Poor: {summary['poor']} accounts")
        print(f"   🚨 Errors: {summary['errors']} accounts")
        print()

        # Individual account details
        print("📋 Individual Account Reports:")
        for email, report in self.health_reports.items():
            status_emoji = {
                'excellent': '✅',
                'good': '👍',
                'fair': '⚠️',
                'poor': '❌',
                'login_failed': '🔐',
                'error': '🚨'
            }.get(report['status'], '❓')

            print(f"\n   {status_emoji} {report['account']} - {report['status'].upper()}")
            print(f"      Score: {report['overall_score']}/100")
            print(f"      Login: {'✅' if report['login_success'] else '❌'}")
            print(f"      Marketplace: {'✅' if report['marketplace_access'] else '❌'}")
            print(f"      Messages: {'✅' if report['messages_access'] else '❌'}")

            if report['warnings']:
                print(f"      Warnings: {len(report['warnings'])}")
                for warning in report['warnings'][:2]:  # Show first 2 warnings
                    print(f"        • {warning}")

        # Overall recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in summary['recommendations']:
            print(f"   {rec}")

        # Detailed account recommendations
        print(f"\n🎯 ACCOUNT-SPECIFIC ACTIONS:")
        for email, report in self.health_reports.items():
            if report['recommendations']:
                print(f"\n   📧 {report['account']}:")
                for rec in report['recommendations'][:3]:  # Show top 3 recommendations
                    print(f"      {rec}")

    def export_health_report(self, filename: str = None):
        """Export health report to file"""
        try:
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"account_health_report_{timestamp}.json"

            report_data = {
                'timestamp': datetime.now().isoformat(),
                'accounts': self.health_reports,
                'summary': self.run_full_health_check()
            }

            # Convert datetime objects to strings for JSON serialization
            for account_data in report_data['accounts'].values():
                account_data['timestamp'] = account_data['timestamp'].isoformat()

            import json
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2)

            print(f"📄 Health report exported to: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Error exporting report: {e}")
            return None

    def get_safety_checklist(self) -> List[str]:
        """Get safety checklist for live deployment"""
        return [
            "🔐 Verified all account credentials are correct",
            "✅ Completed Facebook security verifications",
            "📋 Reviewed Facebook Terms of Service compliance",
            "⚠️ Set conservative rate limits for initial testing",
            "👥 Designated human operator for escalations",
            "📊 Set up monitoring and logging systems",
            "🚨 Prepared emergency stop procedures",
            "📱 Tested manual Facebook access for all accounts",
            "🤖 Verified AI response quality and appropriateness",
            "⏰ Planned regular health check schedule"
        ]


def main():
    """Main execution function"""
    print("🏥 Facebook Account Health Monitor")
    print("=" * 50)
    print("This tool checks your Facebook accounts for automation readiness.")
    print()

    monitor = AccountHealthMonitor()

    # Load accounts
    if not monitor.load_accounts_for_monitoring():
        print("❌ Could not load accounts for monitoring")
        return False

    print(f"📋 Loaded {len(monitor.accounts)} accounts")
    print("🔍 Starting comprehensive health check...")
    print("   (This may take 2-3 minutes per account)")
    print()

    # Run health check
    summary = monitor.run_full_health_check()

    if 'error' in summary:
        print(f"❌ Health check failed: {summary['error']}")
        return False

    # Display results
    monitor.display_health_report(summary)

    # Export report
    export_choice = input("\n💾 Export detailed report to file? [y/N]: ").strip().lower()
    if export_choice == 'y':
        monitor.export_health_report()

    # Safety checklist
    print(f"\n✅ SAFETY CHECKLIST FOR LIVE DEPLOYMENT:")
    checklist = monitor.get_safety_checklist()
    for item in checklist:
        print(f"   {item}")

    # Final recommendation
    healthy_accounts = summary['excellent'] + summary['good']
    total_checked = summary['accounts_checked']

    if healthy_accounts >= total_checked * 0.8 and total_checked > 0:
        print(f"\n🎉 READY FOR LIVE DEPLOYMENT!")
        print(f"   {healthy_accounts}/{total_checked} accounts are in good health")
        print(f"   Proceed with live Facebook integration")
    elif healthy_accounts > 0:
        print(f"\n⚠️ PARTIAL READINESS")
        print(f"   {healthy_accounts}/{total_checked} accounts are healthy")
        print(f"   Consider starting with healthy accounts only")
    else:
        print(f"\n🚨 NOT READY FOR LIVE DEPLOYMENT")
        print(f"   Address account issues before proceeding")
        print(f"   Review recommendations above")

    return True


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Account health check completed!")
        else:
            print("\n❌ Account health check failed.")
    except KeyboardInterrupt:
        print("\n\n⏹️ Health check interrupted by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")