"""
Logging System for Facebook Marketplace Bot
Centralized logging configuration with multiple handlers and formatters
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from config import Config


class BotLogger:
    """
    Custom logger setup for the Facebook Marketplace Bot

    Features:
    - File logging with rotation
    - Console logging with colors
    - Separate error log file
    - Structured log formatting
    - Performance logging
    """

    def __init__(self):
        self.loggers = {}
        self._setup_base_logging()

    def _setup_base_logging(self):
        """Set up the base logging configuration"""
        # Ensure log directory exists
        Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, Config.LOG_LEVEL))

        # Clear any existing handlers
        root_logger.handlers.clear()

        # Set up formatters
        self.detailed_formatter = logging.Formatter(
            '%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        self.simple_formatter = logging.Formatter(
            '%(levelname)-8s | %(message)s'
        )

        self.error_formatter = logging.Formatter(
            '%(asctime)s | %(name)-20s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Set up handlers
        if Config.LOG_TO_FILE:
            self._setup_file_handlers()

        if Config.LOG_TO_CONSOLE:
            self._setup_console_handler()

    def _setup_file_handlers(self):
        """Set up file logging handlers"""
        # Main log file with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=Config.MAX_LOG_SIZE_MB * 1024 * 1024,
            backupCount=Config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(self.detailed_formatter)

        # Error log file
        error_handler = logging.handlers.RotatingFileHandler(
            Config.ERROR_LOG_FILE,
            maxBytes=Config.MAX_LOG_SIZE_MB * 1024 * 1024,
            backupCount=Config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.error_formatter)

        # Success log file
        success_handler = logging.handlers.RotatingFileHandler(
            Config.SUCCESS_LOG_FILE,
            maxBytes=Config.MAX_LOG_SIZE_MB * 1024 * 1024,
            backupCount=Config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        success_handler.setLevel(logging.INFO)
        success_handler.setFormatter(self.detailed_formatter)

        # Add custom filter for success log
        success_handler.addFilter(self._success_filter)

        # Add handlers to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(success_handler)

    def _setup_console_handler(self):
        """Set up console logging handler with colors"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, Config.LOG_LEVEL))

        # Use colored formatter if available
        if Config.DEBUG_MODE:
            console_handler.setFormatter(self.detailed_formatter)
        else:
            console_handler.setFormatter(self.simple_formatter)

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(console_handler)

    def _success_filter(self, record):
        """Filter to capture success-related log messages"""
        success_keywords = [
            'success', 'successful', 'completed', 'created', 'loaded',
            'logged in', 'sent message', 'listing created'
        ]
        return any(keyword in record.getMessage().lower() for keyword in success_keywords)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance for a specific module

        Args:
            name: Logger name (usually __name__)

        Returns:
            Configured logger instance
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger

        return self.loggers[name]

    def log_performance(self, operation: str, duration: float, logger_name: str = "performance"):
        """
        Log performance metrics

        Args:
            operation: Name of the operation
            duration: Duration in seconds
            logger_name: Name of the logger to use
        """
        logger = self.get_logger(logger_name)
        logger.info(f"PERFORMANCE | {operation} | {duration:.2f}s")

    def log_facebook_action(self, action: str, account_email: str, success: bool,
                            details: str = "", logger_name: str = "facebook"):
        """
        Log Facebook-related actions

        Args:
            action: Action performed (login, create_listing, send_message, etc.)
            account_email: Masked email of the account
            success: Whether the action was successful
            details: Additional details about the action
            logger_name: Name of the logger to use
        """
        logger = self.get_logger(logger_name)
        status = "SUCCESS" if success else "FAILED"

        message = f"FB_ACTION | {action} | {account_email} | {status}"
        if details:
            message += f" | {details}"

        if success:
            logger.info(message)
        else:
            logger.error(message)

    def log_ai_interaction(self, prompt_length: int, response_length: int,
                           confidence: float, response_time: float,
                           logger_name: str = "ai"):
        """
        Log AI interaction metrics

        Args:
            prompt_length: Length of the prompt sent to AI
            response_length: Length of the AI response
            confidence: AI confidence score
            response_time: Time taken for response
            logger_name: Name of the logger to use
        """
        logger = self.get_logger(logger_name)
        logger.info(f"AI_INTERACTION | prompt:{prompt_length}chars | "
                    f"response:{response_length}chars | confidence:{confidence:.2f} | "
                    f"time:{response_time:.2f}s")

    def log_message_processing(self, sender: str, message_length: int,
                               contains_question: bool, priority_score: int,
                               action_taken: str, logger_name: str = "messages"):
        """
        Log message processing details

        Args:
            sender: Name of the message sender
            message_length: Length of the message
            contains_question: Whether message contains a question
            priority_score: Calculated priority score
            action_taken: Action taken (responded, escalated, ignored)
            logger_name: Name of the logger to use
        """
        logger = self.get_logger(logger_name)
        logger.info(f"MESSAGE_PROCESSED | {sender} | {message_length}chars | "
                    f"question:{contains_question} | priority:{priority_score} | "
                    f"action:{action_taken}")


# Global logger instance
_bot_logger = None


def setup_logging() -> BotLogger:
    """
    Set up the global logging system

    Returns:
        BotLogger instance
    """
    global _bot_logger
    if _bot_logger is None:
        _bot_logger = BotLogger()
    return _bot_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    if _bot_logger is None:
        setup_logging()
    return _bot_logger.get_logger(name)


def log_performance(operation: str, duration: float):
    """
    Convenience function to log performance metrics

    Args:
        operation: Name of the operation
        duration: Duration in seconds
    """
    if _bot_logger is None:
        setup_logging()
    _bot_logger.log_performance(operation, duration)


def log_facebook_action(action: str, account_email: str, success: bool, details: str = ""):
    """
    Convenience function to log Facebook actions

    Args:
        action: Action performed
        account_email: Masked email of the account
        success: Whether the action was successful
        details: Additional details
    """
    if _bot_logger is None:
        setup_logging()
    _bot_logger.log_facebook_action(action, account_email, success, details)


def log_ai_interaction(prompt_length: int, response_length: int,
                       confidence: float, response_time: float):
    """
    Convenience function to log AI interactions

    Args:
        prompt_length: Length of the prompt
        response_length: Length of the response
        confidence: AI confidence score
        response_time: Response time in seconds
    """
    if _bot_logger is None:
        setup_logging()
    _bot_logger.log_ai_interaction(prompt_length, response_length, confidence, response_time)


def log_message_processing(sender: str, message_length: int, contains_question: bool,
                           priority_score: int, action_taken: str):
    """
    Convenience function to log message processing

    Args:
        sender: Message sender
        message_length: Length of message
        contains_question: Whether contains question
        priority_score: Priority score
        action_taken: Action taken
    """
    if _bot_logger is None:
        setup_logging()
    _bot_logger.log_message_processing(sender, message_length, contains_question,
                                       priority_score, action_taken)


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    bot_logger = setup_logging()

    # Test different loggers
    main_logger = get_logger(__name__)
    facebook_logger = get_logger("facebook")
    ai_logger = get_logger("ai")

    # Test logging at different levels
    main_logger.debug("This is a debug message")
    main_logger.info("Application started successfully")
    main_logger.warning("This is a warning")
    main_logger.error("This is an error message")

    # Test performance logging
    log_performance("test_operation", 2.5)

    # Test Facebook action logging
    log_facebook_action("login", "t**t@example.com", True, "Login successful")
    log_facebook_action("create_listing", "t**t@example.com", False, "Title too long")

    # Test AI interaction logging
    log_ai_interaction(100, 50, 0.85, 1.2)

    # Test message processing logging
    log_message_processing("John Doe", 25, True, 15, "responded")

    print("✅ Logging system test completed")
    print(f"📁 Log files created in: {Config.LOGS_DIR}")
    print(f"📄 Main log: {Config.LOG_FILE}")
    print(f"📄 Error log: {Config.ERROR_LOG_FILE}")
    print(f"📄 Success log: {Config.SUCCESS_LOG_FILE}")