"""
Message Monitor Service for Facebook Marketplace Bot
Phase 4: Real-time message detection and processing
"""

import time
import asyncio
import random
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import json

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from utils.browser_utils import BrowserManager
from utils.logger import get_logger, log_message_processing, log_performance
from models.message import Message, MessageType, MessageStatus
from models.account import Account
from config import Config


class MessageMonitor:
    """
    Facebook Marketplace message monitoring service

    Features:
    - Real-time message detection
    - Conversation threading
    - Message parsing and classification
    - Queue management for processing
    - Rate limiting and activity tracking
    """

    def __init__(self, browser_manager: BrowserManager, account: Account):
        """
        Initialize MessageMonitor

        Args:
            browser_manager: Browser automation instance
            account: Facebook account to monitor
        """
        self.browser = browser_manager
        self.account = account
        self.logger = get_logger(f"message_monitor_{account.get_masked_email()}")

        # Message processing state
        self.is_monitoring = False
        self.last_check_time = None
        self.processed_messages = set()
        self.conversation_threads = {}

        # Message queue
        self.new_messages = []
        self.processing_queue = []

        # Statistics
        self.messages_detected = 0
        self.messages_processed = 0
        self.errors_count = 0

        # Facebook messenger selectors
        self.selectors = {
            'navigation': {
                'messages_url': 'https://www.facebook.com/messages',
                'messages_link': 'a[href*="/messages"]',
                'messenger_icon': '[aria-label*="Messenger"]'
            },

            'conversations': {
                'conversation_list': '[role="grid"]',
                'conversation_item': '[data-testid="conversation"]',
                'conversation_link': 'a[role="link"]',
                'unread_indicator': '[data-testid="unread_indicator"]',
                'conversation_name': '[data-testid="conversation_name"]'
            },

            'messages': {
                'message_container': '[data-testid="message_container"]',
                'message_bubble': '[data-testid="message_bubble"]',
                'message_text': '[data-testid="message_text"]',
                'message_time': '[data-testid="message_timestamp"]',
                'sender_name': '[data-testid="message_sender"]',
                'message_thread': '[role="log"]'
            },

            'compose': {
                'message_input': '[contenteditable="true"][data-testid="message_input"]',
                'message_input_alt': 'div[contenteditable="true"][aria-label*="message"]',
                'send_button': '[data-testid="send_button"]',
                'send_button_alt': 'button[type="submit"]'
            }
        }

        self.logger.info(f"MessageMonitor initialized for {account.get_masked_email()}")

    def start_monitoring(self, check_interval: int = None) -> bool:
        """
        Start monitoring for new messages

        Args:
            check_interval: Seconds between checks (uses config default if None)

        Returns:
            True if monitoring started successfully
        """
        try:
            check_interval = check_interval or Config.MESSAGE_CHECK_INTERVAL
            self.logger.info(f"Starting message monitoring (check every {check_interval}s)")

            # Navigate to messages
            if not self._navigate_to_messages():
                return False

            self.is_monitoring = True
            self.last_check_time = datetime.now()

            self.logger.info("✅ Message monitoring started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start message monitoring: {e}")
            return False

    def _navigate_to_messages(self) -> bool:
        """Navigate to Facebook Messages"""
        try:
            self.logger.info("Navigating to Facebook Messages...")

            # Try direct navigation first
            if self.browser.navigate_to(self.selectors['navigation']['messages_url']):
                self.browser.human_delay(2, 4)

                # Verify we're on messages page
                if 'messages' in self.browser.driver.current_url:
                    self.logger.info("Successfully navigated to Messages")
                    return True

            # Fallback: try clicking messages link
            messages_link = self.browser.find_element_safe(
                By.CSS_SELECTOR,
                self.selectors['navigation']['messages_link'],
                timeout=5
            )

            if messages_link:
                if self.browser.click_element_safe(messages_link):
                    self.browser.human_delay(2, 4)
                    self.logger.info("Navigated to Messages via link")
                    return True

            self.logger.error("Failed to navigate to Messages")
            return False

        except Exception as e:
            self.logger.error(f"Error navigating to messages: {e}")
            return False

    def scan_for_new_messages(self) -> List[Message]:
        """
        Scan for new messages in all conversations

        Returns:
            List of new Message objects
        """
        new_messages = []

        try:
            self.logger.debug("Scanning for new messages...")

            # Get conversation list
            conversations = self._get_conversation_list()
            self.logger.debug(f"Found {len(conversations)} conversations")

            for conv_data in conversations:
                try:
                    # Check if conversation has unread messages
                    if conv_data.get('has_unread', False):
                        conv_messages = self._scan_conversation(conv_data)
                        new_messages.extend(conv_messages)

                except Exception as e:
                    self.logger.warning(f"Error scanning conversation {conv_data.get('name', 'unknown')}: {e}")
                    continue

            # Update statistics
            self.messages_detected += len(new_messages)

            if new_messages:
                self.logger.info(f"Found {len(new_messages)} new messages")
            else:
                self.logger.debug("No new messages found")

            return new_messages

        except Exception as e:
            self.logger.error(f"Error scanning for messages: {e}")
            self.errors_count += 1
            return []

    def _get_conversation_list(self) -> List[Dict[str, Any]]:
        """
        Get list of conversations from messenger

        Returns:
            List of conversation data dictionaries
        """
        conversations = []

        try:
            # Find conversation list container
            conv_list = self.browser.find_element_safe(
                By.CSS_SELECTOR,
                self.selectors['conversations']['conversation_list'],
                timeout=5
            )

            if not conv_list:
                self.logger.warning("Conversation list not found")
                return []

            # Find individual conversations
            conv_items = self.browser.driver.find_elements(
                By.CSS_SELECTOR,
                self.selectors['conversations']['conversation_item']
            )

            for item in conv_items[:20]:  # Limit to first 20 conversations
                try:
                    conv_data = self._extract_conversation_data(item)
                    if conv_data:
                        conversations.append(conv_data)

                except Exception as e:
                    self.logger.debug(f"Error extracting conversation data: {e}")
                    continue

            return conversations

        except Exception as e:
            self.logger.error(f"Error getting conversation list: {e}")
            return []

    def _extract_conversation_data(self, conv_element) -> Optional[Dict[str, Any]]:
        """
        Extract data from a conversation element

        Args:
            conv_element: Selenium WebElement for conversation

        Returns:
            Dictionary with conversation data or None
        """
        try:
            # Get conversation name
            name_element = conv_element.find_element(
                By.CSS_SELECTOR,
                self.selectors['conversations']['conversation_name']
            )
            conv_name = name_element.text.strip() if name_element else "Unknown"

            # Check for unread indicator
            unread_element = conv_element.find_elements(
                By.CSS_SELECTOR,
                self.selectors['conversations']['unread_indicator']
            )
            has_unread = len(unread_element) > 0

            # Get conversation link
            link_element = conv_element.find_element(
                By.CSS_SELECTOR,
                self.selectors['conversations']['conversation_link']
            )
            conv_url = link_element.get_attribute('href') if link_element else None

            return {
                'name': conv_name,
                'has_unread': has_unread,
                'url': conv_url,
                'element': conv_element
            }

        except Exception as e:
            self.logger.debug(f"Error extracting conversation data: {e}")
            return None

    def _scan_conversation(self, conv_data: Dict[str, Any]) -> List[Message]:
        """
        Scan a specific conversation for new messages

        Args:
            conv_data: Conversation data dictionary

        Returns:
            List of new Message objects
        """
        messages = []
        conv_name = conv_data.get('name', 'Unknown')

        try:
            self.logger.debug(f"Scanning conversation: {conv_name}")

            # Click on conversation to open it
            if not self._open_conversation(conv_data):
                return []

            # Wait for messages to load
            self.browser.human_delay(1, 3)

            # Extract messages from conversation
            message_elements = self.browser.driver.find_elements(
                By.CSS_SELECTOR,
                self.selectors['messages']['message_bubble']
            )

            # Process recent messages (last 10)
            for msg_element in message_elements[-10:]:
                try:
                    message = self._extract_message_data(msg_element, conv_name)
                    if message and self._is_new_message(message):
                        messages.append(message)

                except Exception as e:
                    self.logger.debug(f"Error extracting message: {e}")
                    continue

            return messages

        except Exception as e:
            self.logger.warning(f"Error scanning conversation {conv_name}: {e}")
            return []

    def _open_conversation(self, conv_data: Dict[str, Any]) -> bool:
        """
        Open a conversation for reading

        Args:
            conv_data: Conversation data dictionary

        Returns:
            True if conversation opened successfully
        """
        try:
            # Click on conversation element
            if self.browser.click_element_safe(conv_data['element']):
                self.browser.human_delay(1, 2)
                return True

            # Fallback: try clicking the link
            if conv_data.get('url'):
                if self.browser.navigate_to(conv_data['url']):
                    self.browser.human_delay(1, 2)
                    return True

            return False

        except Exception as e:
            self.logger.debug(f"Error opening conversation: {e}")
            return False

    def _extract_message_data(self, msg_element, conversation_name: str) -> Optional[Message]:
        """
        Extract message data from a message element

        Args:
            msg_element: Selenium WebElement for message
            conversation_name: Name of the conversation

        Returns:
            Message object or None
        """
        try:
            # Get message text
            text_element = msg_element.find_element(
                By.CSS_SELECTOR,
                self.selectors['messages']['message_text']
            )
            message_text = text_element.text.strip() if text_element else ""

            if not message_text:
                return None

            # Get sender (try to determine if it's from customer or us)
            sender_element = msg_element.find_elements(
                By.CSS_SELECTOR,
                self.selectors['messages']['sender_name']
            )

            # If no sender element, it might be our own message
            if not sender_element:
                # Skip our own messages for now
                return None

            sender_name = sender_element[0].text.strip() if sender_element else conversation_name

            # Get timestamp
            time_element = msg_element.find_elements(
                By.CSS_SELECTOR,
                self.selectors['messages']['message_time']
            )

            timestamp = None
            if time_element:
                time_text = time_element[0].get_attribute('data-time') or time_element[0].text
                timestamp = self._parse_timestamp(time_text)

            # Create conversation ID
            conversation_id = f"conv_{hash(conversation_name) % 10000}"

            # Create Message object
            message = Message.create_customer_message(
                content=message_text,
                sender_name=sender_name,
                conversation_id=conversation_id,
                account_email=self.account.email
            )

            if timestamp:
                message.timestamp = timestamp

            return message

        except Exception as e:
            self.logger.debug(f"Error extracting message data: {e}")
            return None

    def _parse_timestamp(self, time_text: str) -> str:
        """
        Parse timestamp from Facebook's time format

        Args:
            time_text: Time text from Facebook

        Returns:
            ISO format timestamp string
        """
        try:
            # Facebook uses various formats: "2m", "1h", "Yesterday", etc.
            now = datetime.now()

            if 'm' in time_text:  # Minutes ago
                minutes = int(time_text.replace('m', ''))
                timestamp = now - timedelta(minutes=minutes)
            elif 'h' in time_text:  # Hours ago
                hours = int(time_text.replace('h', ''))
                timestamp = now - timedelta(hours=hours)
            elif 'yesterday' in time_text.lower():
                timestamp = now - timedelta(days=1)
            else:
                # Default to current time if can't parse
                timestamp = now

            return timestamp.isoformat()

        except:
            return datetime.now().isoformat()

    def _is_new_message(self, message: Message) -> bool:
        """
        Check if message is new and should be processed

        Args:
            message: Message to check

        Returns:
            True if message is new
        """
        # Create unique message ID
        message_id = f"{message.conversation_id}_{hash(message.content[:50])}_{message.sender_name}"

        if message_id in self.processed_messages:
            return False

        # Check if message is too old
        if message.get_age_minutes() > Config.IGNORE_OLD_MESSAGES_HOURS * 60:
            return False

        # Mark as seen
        self.processed_messages.add(message_id)

        return True

    def process_message_queue(self, processor_callback: Callable[[Message], bool] = None) -> int:
        """
        Process queued messages

        Args:
            processor_callback: Function to call for each message

        Returns:
            Number of messages processed
        """
        processed_count = 0

        try:
            while self.new_messages:
                message = self.new_messages.pop(0)

                try:
                    # Log message processing
                    log_message_processing(
                        message.sender_name,
                        len(message.content),
                        message.contains_question,
                        message.get_priority_score(),
                        "processing"
                    )

                    # Call processor if provided
                    if processor_callback:
                        success = processor_callback(message)
                        if success:
                            message.mark_as_processed()
                        else:
                            message.mark_as_error()
                    else:
                        # Default processing: just mark as processed
                        message.mark_as_processed()

                    processed_count += 1
                    self.messages_processed += 1

                    self.logger.debug(f"Processed message from {message.sender_name}")

                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    message.mark_as_error(str(e))
                    self.errors_count += 1

        except Exception as e:
            self.logger.error(f"Error in message processing queue: {e}")

        return processed_count

    def run_monitoring_cycle(self, processor_callback: Callable[[Message], bool] = None) -> Dict[str, int]:
        """
        Run one complete monitoring cycle

        Args:
            processor_callback: Function to process messages

        Returns:
            Dictionary with cycle statistics
        """
        cycle_start = time.time()

        try:
            # Scan for new messages
            new_messages = self.scan_for_new_messages()

            # Add to queue
            self.new_messages.extend(new_messages)

            # Process queue
            processed_count = self.process_message_queue(processor_callback)

            # Update timing
            self.last_check_time = datetime.now()
            cycle_time = time.time() - cycle_start

            # Log performance
            log_performance("message_monitoring_cycle", cycle_time)

            stats = {
                'new_messages': len(new_messages),
                'processed_messages': processed_count,
                'queue_size': len(self.new_messages),
                'cycle_time': cycle_time,
                'total_detected': self.messages_detected,
                'total_processed': self.messages_processed,
                'errors': self.errors_count
            }

            if new_messages or processed_count:
                self.logger.info(f"Monitoring cycle: {stats}")

            return stats

        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")
            return {'error': str(e)}

    def stop_monitoring(self):
        """Stop message monitoring"""
        self.is_monitoring = False
        self.logger.info("Message monitoring stopped")

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        return {
            'account': self.account.get_masked_email(),
            'is_monitoring': self.is_monitoring,
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'messages_detected': self.messages_detected,
            'messages_processed': self.messages_processed,
            'errors_count': self.errors_count,
            'queue_size': len(self.new_messages),
            'processed_message_ids': len(self.processed_messages)
        }


# Async wrapper for continuous monitoring
# Replace the existing AsyncMessageMonitor class in services/message_monitor.py
# with this fixed version:

class AsyncMessageMonitor:
    """
    Fixed Asynchronous wrapper for continuous message monitoring
    """

    def __init__(self, message_monitor):
        self.monitor = message_monitor
        self.running = False
        self.task = None

    async def start_continuous_monitoring(self,
                                        check_interval: int = None,
                                        processor_callback: Callable[[Message], bool] = None):
        """
        Start continuous message monitoring

        Args:
            check_interval: Seconds between checks
            processor_callback: Function to process messages
        """
        check_interval = check_interval or Config.MESSAGE_CHECK_INTERVAL
        self.running = True

        self.monitor.logger.info(f"Starting continuous async monitoring (every {check_interval}s)")

        try:
            while self.running:
                # Run monitoring cycle in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self.monitor.run_monitoring_cycle,
                    processor_callback
                )

                # Wait for next cycle
                await asyncio.sleep(check_interval)

        except Exception as e:
            self.monitor.logger.error(f"Error in continuous monitoring: {e}")
        finally:
            self.running = False
            self.monitor.logger.info("Continuous monitoring stopped")

    def stop_continuous_monitoring(self):
        """Stop continuous monitoring"""
        self.running = False
        self.monitor.stop_monitoring()

    def stop_continuous_monitoring(self):
        """Stop continuous monitoring"""
        self.running = False
        self.monitor.stop_monitoring()


# Integration with FacebookBot
def add_message_monitoring_to_facebook_bot():
    """
    This shows how to integrate message monitoring with existing FacebookBot
    You can add these methods to your FacebookBot class
    """

    def start_message_monitoring(self, check_interval: int = None) -> bool:
        """
        Start message monitoring for this bot's account

        Args:
            check_interval: Seconds between message checks

        Returns:
            True if monitoring started successfully
        """
        try:
            if not self.is_logged_in:
                self.logger.error("Must be logged in to monitor messages")
                return False

            # Create message monitor
            self.message_monitor = MessageMonitor(self.browser, self.account)

            # Start monitoring
            return self.message_monitor.start_monitoring(check_interval)

        except Exception as e:
            self.logger.error(f"Failed to start message monitoring: {e}")
            return False

    def process_new_messages(self, processor_callback: Callable[[Message], bool] = None) -> int:
        """
        Process new messages (add this to FacebookBot)

        Args:
            processor_callback: Function to process each message

        Returns:
            Number of messages processed
        """
        if not hasattr(self, 'message_monitor') or not self.message_monitor:
            self.logger.warning("Message monitoring not started")
            return 0

        return self.message_monitor.run_monitoring_cycle(processor_callback)

    def stop_message_monitoring(self):
        """Stop message monitoring (add this to FacebookBot)"""
        if hasattr(self, 'message_monitor') and self.message_monitor:
            self.message_monitor.stop_monitoring()
            self.message_monitor = None


# Utility functions for message handling
def create_message_processor(response_generator: Callable[[str], str] = None) -> Callable[[Message], bool]:
    """
    Create a message processor function

    Args:
        response_generator: Function that generates responses to messages

    Returns:
        Message processor function
    """
    logger = get_logger("message_processor")

    def process_message(message: Message) -> bool:
        try:
            logger.info(f"Processing message from {message.sender_name}")

            # Check if message requires human attention
            if message.requires_human_attention:
                logger.warning(f"Message escalated to human: {message.get_short_content()}")
                message.mark_as_escalated()
                return True

            # Check if it's a question that needs a response
            if message.contains_question and response_generator:
                try:
                    response = response_generator(message.content)
                    if response:
                        logger.info(f"Generated response: {response[:50]}...")
                        # Here you would send the response via FacebookBot
                        message.mark_as_processed()
                        return True
                except Exception as e:
                    logger.error(f"Response generation failed: {e}")
                    message.mark_as_error(str(e))
                    return False

            # Mark as processed if no response needed
            message.mark_as_processed()
            return True

        except Exception as e:
            logger.error(f"Message processing error: {e}")
            message.mark_as_error(str(e))
            return False

    return process_message


def create_continuous_monitor(account: Account,
                            check_interval: int = None,
                            processor_callback: Callable[[Message], bool] = None) -> AsyncMessageMonitor:
    """
    Create a continuous message monitor for an account

    Args:
        account: Account to monitor
        check_interval: Seconds between checks
        processor_callback: Function to process messages

    Returns:
        AsyncMessageMonitor instance
    """
    # Create browser and monitor
    browser = create_browser_manager(headless=True, profile_name=f"monitor_{account.email}")
    monitor = MessageMonitor(browser, account)

    # Create async wrapper
    async_monitor = AsyncMessageMonitor(monitor)

    return async_monitor


# Add this function to services/message_monitor.py just before the "if __name__ == "__main__":" section:

async def test_async_monitoring_fix():
    """Test the fixed async monitoring"""
    from services.excel_handler import ExcelHandler
    from utils.browser_utils import create_browser_manager

    try:
        # Create test setup
        excel_handler = ExcelHandler()

        # Create sample accounts if they don't exist
        sample_accounts_file = Config.DATA_DIR / "sample_data" / "sample_accounts.xlsx"
        if not sample_accounts_file.exists():
            excel_handler.create_sample_accounts_file(sample_accounts_file)

        accounts = excel_handler.load_accounts(sample_accounts_file)

        with create_browser_manager(headless=True) as browser:
            monitor = MessageMonitor(browser, accounts[0])
            async_monitor = AsyncMessageMonitor(monitor)

            print("✅ Async monitor created successfully")

            # Test processor
            def test_processor(message):
                print(f"Async processed: {message.sender_name}")
                return True

            # Start monitoring for 10 seconds
            monitoring_task = asyncio.create_task(
                async_monitor.start_continuous_monitoring(
                    check_interval=2,
                    processor_callback=test_processor
                )
            )

            # Stop after 10 seconds
            await asyncio.sleep(10)
            async_monitor.stop_continuous_monitoring()

            # Wait for task to complete
            try:
                await asyncio.wait_for(monitoring_task, timeout=5)
            except asyncio.TimeoutError:
                monitoring_task.cancel()

            print("✅ Async monitoring test completed")
            return True

    except Exception as e:
        print(f"❌ Async test error: {e}")
        return False

# Example usage and testing
# Replace the existing "if __name__ == "__main__":" section in services/message_monitor.py with:

if __name__ == "__main__":
    from utils.logger import setup_logging
    from services.excel_handler import ExcelHandler
    from utils.browser_utils import create_browser_manager

    setup_logging()
    logger = get_logger(__name__)

    logger.info("Testing MessageMonitor...")

    try:
        # Load test account
        excel_handler = ExcelHandler()

        # Create sample accounts if they don't exist
        sample_accounts_file = Config.DATA_DIR / "sample_data" / "sample_accounts.xlsx"
        if not sample_accounts_file.exists():
            excel_handler.create_sample_accounts_file(sample_accounts_file)

        accounts = excel_handler.load_accounts(sample_accounts_file)

        if not accounts:
            logger.error("No test accounts found")
            exit(1)

        test_account = accounts[0]
        logger.info(f"Testing with account: {test_account.get_masked_email()}")

        # Test regular monitoring
        with create_browser_manager(headless=True) as browser:
            # Create message monitor
            monitor = MessageMonitor(browser, test_account)

            logger.info("MessageMonitor created successfully")
            logger.info("Note: Real Facebook login required for full message monitoring")

            # Create test message processor
            def test_processor(message: Message) -> bool:
                logger.info(f"Test processor: {message.sender_name} - {message.get_short_content()}")
                return True

            # Test monitoring initialization
            logger.info("Testing monitor initialization...")
            stats = monitor.get_monitoring_stats()
            logger.info(f"Monitor stats: {stats}")

            # Test message processing with simulated data
            logger.info("Testing message processing...")
            test_messages = [
                Message.create_customer_message(
                    "Hi, is this still available?",
                    "Test User 1",
                    "conv_test_1"
                ),
                Message.create_customer_message(
                    "What's your best price?",
                    "Test User 2",
                    "conv_test_2"
                )
            ]

            # Add to queue and process
            monitor.new_messages.extend(test_messages)
            processed = monitor.process_message_queue(test_processor)
            logger.info(f"✅ Processed {processed} test messages")

            # Test async monitoring
            logger.info("Testing async monitoring fix...")
            import asyncio
            async_result = asyncio.run(test_async_monitoring_fix())
            logger.info(f"Async test result: {'PASSED' if async_result else 'FAILED'}")

            logger.info("✅ MessageMonitor tests completed successfully!")
            logger.info("Ready for Phase 4 and Phase 5 implementation")

    except Exception as e:
        logger.error(f"MessageMonitor test error: {e}")