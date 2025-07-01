"""
Configuration System for Facebook Marketplace Bot
Centralized configuration management for all bot settings
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Centralized configuration class for the Facebook Marketplace Bot

    This class manages all configuration settings including:
    - File paths
    - Facebook settings
    - Browser automation settings
    - AI/Llama settings
    - Message monitoring settings
    - Logging settings
    """

    # ==================== PROJECT PATHS ====================
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    SCREENSHOTS_DIR = BASE_DIR / "screenshots"
    DRIVERS_DIR = BASE_DIR / "drivers"

    # Excel file paths
    PRODUCTS_FILE = DATA_DIR / "products.xlsx"
    ACCOUNTS_FILE = DATA_DIR / "accounts.xlsx"
    TEMPLATES_FILE = DATA_DIR / "templates.json"

    # Sample files
    SAMPLE_PRODUCTS_FILE = DATA_DIR / "sample_data" / "sample_products.xlsx"
    SAMPLE_ACCOUNTS_FILE = DATA_DIR / "sample_data" / "sample_accounts.xlsx"

    # ==================== FACEBOOK SETTINGS ====================
    FB_BASE_URL = "https://www.facebook.com"
    FB_LOGIN_URL = "https://www.facebook.com/login"
    FB_MARKETPLACE_URL = "https://www.facebook.com/marketplace"
    FB_MARKETPLACE_CREATE_URL = "https://www.facebook.com/marketplace/create"
    FB_MESSENGER_URL = "https://www.facebook.com/messages"

    # ==================== BROWSER AUTOMATION SETTINGS ====================
    # Browser settings
    HEADLESS_MODE = os.getenv("HEADLESS_MODE", "False").lower() == "true"
    BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "10"))
    PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "30"))

    # Delays (in seconds) - for human-like behavior
    MIN_DELAY = float(os.getenv("MIN_DELAY", "2.0"))
    MAX_DELAY = float(os.getenv("MAX_DELAY", "5.0"))
    TYPING_DELAY_MIN = float(os.getenv("TYPING_DELAY_MIN", "0.1"))
    TYPING_DELAY_MAX = float(os.getenv("TYPING_DELAY_MAX", "0.3"))

    # Anti-detection settings
    USE_RANDOM_USER_AGENTS = os.getenv("USE_RANDOM_USER_AGENTS", "True").lower() == "true"
    ENABLE_STEALTH_MODE = os.getenv("ENABLE_STEALTH_MODE", "True").lower() == "true"

    # Screenshot settings
    TAKE_SCREENSHOTS = os.getenv("TAKE_SCREENSHOTS", "True").lower() == "true"
    SCREENSHOT_ON_ERROR = os.getenv("SCREENSHOT_ON_ERROR", "True").lower() == "true"

    # ==================== LLAMA AI SETTINGS ====================
    # Llama server configuration
    LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://localhost:11434")
    LLAMA_MODEL_NAME = os.getenv("LLAMA_MODEL_NAME", "llama3.2")
    LLAMA_API_TIMEOUT = int(os.getenv("LLAMA_API_TIMEOUT", "30"))

    # AI generation parameters
    LLAMA_TEMPERATURE = float(os.getenv("LLAMA_TEMPERATURE", "0.7"))
    LLAMA_MAX_TOKENS = int(os.getenv("LLAMA_MAX_TOKENS", "150"))
    LLAMA_TOP_P = float(os.getenv("LLAMA_TOP_P", "0.9"))

    # AI response settings
    AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.7"))
    AI_MAX_RESPONSE_TIME = int(os.getenv("AI_MAX_RESPONSE_TIME", "10"))
    USE_FALLBACK_RESPONSES = os.getenv("USE_FALLBACK_RESPONSES", "True").lower() == "true"

    # ==================== MESSAGE MONITORING SETTINGS ====================
    # Monitoring intervals
    MESSAGE_CHECK_INTERVAL = int(os.getenv("MESSAGE_CHECK_INTERVAL", "30"))  # seconds
    CONVERSATION_REFRESH_INTERVAL = int(os.getenv("CONVERSATION_REFRESH_INTERVAL", "300"))  # 5 minutes

    # Auto-reply settings
    AUTO_REPLY_ENABLED = os.getenv("AUTO_REPLY_ENABLED", "True").lower() == "true"
    REPLY_DELAY_MIN = int(os.getenv("REPLY_DELAY_MIN", "10"))  # seconds
    REPLY_DELAY_MAX = int(os.getenv("REPLY_DELAY_MAX", "30"))  # seconds

    # Message filtering
    IGNORE_OLD_MESSAGES_HOURS = int(os.getenv("IGNORE_OLD_MESSAGES_HOURS", "24"))
    MAX_MESSAGES_PER_CONVERSATION = int(os.getenv("MAX_MESSAGES_PER_CONVERSATION", "10"))

    # Human escalation settings
    ESCALATE_TO_HUMAN_KEYWORDS = [
        "complaint", "refund", "problem", "issue", "broken", "damaged",
        "scam", "police", "lawyer", "court", "sue", "report"
    ]
    ESCALATE_AFTER_FAILED_RESPONSES = int(os.getenv("ESCALATE_AFTER_FAILED_RESPONSES", "3"))

    # ==================== LISTING SETTINGS ====================
    # Listing limits
    MAX_LISTINGS_PER_ACCOUNT_PER_DAY = int(os.getenv("MAX_LISTINGS_PER_ACCOUNT_PER_DAY", "10"))
    MAX_LISTINGS_PER_HOUR = int(os.getenv("MAX_LISTINGS_PER_HOUR", "3"))

    # Image settings
    MAX_IMAGES_PER_LISTING = int(os.getenv("MAX_IMAGES_PER_LISTING", "10"))
    SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png", ".webp"]
    MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))

    # Listing validation
    MIN_TITLE_LENGTH = int(os.getenv("MIN_TITLE_LENGTH", "10"))
    MAX_TITLE_LENGTH = int(os.getenv("MAX_TITLE_LENGTH", "100"))
    MIN_DESCRIPTION_LENGTH = int(os.getenv("MIN_DESCRIPTION_LENGTH", "20"))
    MAX_DESCRIPTION_LENGTH = int(os.getenv("MAX_DESCRIPTION_LENGTH", "2000"))

    # ==================== LOGGING SETTINGS ====================
    # Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_TO_FILE = os.getenv("LOG_TO_FILE", "True").lower() == "true"
    LOG_TO_CONSOLE = os.getenv("LOG_TO_CONSOLE", "True").lower() == "true"

    # Log file settings
    LOG_FILE = LOGS_DIR / "bot.log"
    ERROR_LOG_FILE = LOGS_DIR / "error.log"
    SUCCESS_LOG_FILE = LOGS_DIR / "success.log"
    MAX_LOG_SIZE_MB = int(os.getenv("MAX_LOG_SIZE_MB", "10"))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    # ==================== SAFETY SETTINGS ====================
    # Rate limiting
    ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "True").lower() == "true"
    MAX_ACTIONS_PER_MINUTE = int(os.getenv("MAX_ACTIONS_PER_MINUTE", "10"))
    MAX_ACTIONS_PER_HOUR = int(os.getenv("MAX_ACTIONS_PER_HOUR", "100"))

    # Error handling
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))  # seconds

    # Account safety
    ACCOUNT_COOLDOWN_HOURS = int(os.getenv("ACCOUNT_COOLDOWN_HOURS", "1"))
    MAX_FAILED_LOGINS = int(os.getenv("MAX_FAILED_LOGINS", "3"))

    # ==================== DEVELOPMENT SETTINGS ====================
    DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
    TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"
    MOCK_FACEBOOK = os.getenv("MOCK_FACEBOOK", "False").lower() == "true"

    # ==================== METHODS ====================

    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist"""
        directories = [
            cls.DATA_DIR,
            cls.LOGS_DIR,
            cls.SCREENSHOTS_DIR,
            cls.DRIVERS_DIR,
            cls.DATA_DIR / "sample_data"
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_all_settings(cls) -> Dict[str, Any]:
        """Get all configuration settings as a dictionary"""
        settings = {}

        for attr_name in dir(cls):
            if not attr_name.startswith('_') and not callable(getattr(cls, attr_name)):
                attr_value = getattr(cls, attr_name)
                # Convert Path objects to strings for JSON serialization
                if isinstance(attr_value, Path):
                    attr_value = str(attr_value)
                settings[attr_name] = attr_value

        return settings

    @classmethod
    def validate_settings(cls) -> List[str]:
        """
        Validate configuration settings and return list of issues

        Returns:
            List of validation error messages (empty if all valid)
        """
        issues = []

        # Check required directories
        try:
            cls.ensure_directories()
        except Exception as e:
            issues.append(f"Cannot create directories: {e}")

        # Validate numeric ranges
        if not 0 <= cls.LLAMA_TEMPERATURE <= 2:
            issues.append("LLAMA_TEMPERATURE must be between 0 and 2")

        if not 0 <= cls.LLAMA_TOP_P <= 1:
            issues.append("LLAMA_TOP_P must be between 0 and 1")

        if cls.MIN_DELAY >= cls.MAX_DELAY:
            issues.append("MIN_DELAY must be less than MAX_DELAY")

        if cls.REPLY_DELAY_MIN >= cls.REPLY_DELAY_MAX:
            issues.append("REPLY_DELAY_MIN must be less than REPLY_DELAY_MAX")

        # Check file permissions
        try:
            cls.LOGS_DIR.mkdir(exist_ok=True)
            test_file = cls.LOGS_DIR / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            issues.append(f"Cannot write to logs directory: {e}")

        return issues

    @classmethod
    def get_delay_range(cls) -> tuple:
        """Get the delay range for random delays"""
        return (cls.MIN_DELAY, cls.MAX_DELAY)

    @classmethod
    def get_typing_delay_range(cls) -> tuple:
        """Get the typing delay range for human-like typing"""
        return (cls.TYPING_DELAY_MIN, cls.TYPING_DELAY_MAX)

    @classmethod
    def get_reply_delay_range(cls) -> tuple:
        """Get the reply delay range for message responses"""
        return (cls.REPLY_DELAY_MIN, cls.REPLY_DELAY_MAX)

    @classmethod
    def is_production_mode(cls) -> bool:
        """Check if running in production mode (not debug/test)"""
        return not (cls.DEBUG_MODE or cls.TEST_MODE)


# Example usage and testing
if __name__ == "__main__":
    # Ensure directories exist
    Config.ensure_directories()

    # Validate settings
    issues = Config.validate_settings()
    if issues:
        print("Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ Configuration is valid")

    # Display key settings
    print(f"\n📁 Data directory: {Config.DATA_DIR}")
    print(f"📁 Logs directory: {Config.LOGS_DIR}")
    print(f"🌐 Facebook URL: {Config.FB_MARKETPLACE_URL}")
    print(f"🤖 Llama server: {Config.LLAMA_SERVER_URL}")
    print(f"📝 Log level: {Config.LOG_LEVEL}")
    print(f"🔧 Debug mode: {Config.DEBUG_MODE}")
    print(f"⏱️ Message check interval: {Config.MESSAGE_CHECK_INTERVAL}s")
    print(f"🎯 Auto-reply enabled: {Config.AUTO_REPLY_ENABLED}")

    # AI Settings (add to your existing config.py)
    LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://localhost:11434")
    LLAMA_MODEL_NAME = os.getenv("LLAMA_MODEL_NAME", "llama3.2")
    LLAMA_API_TIMEOUT = int(os.getenv("LLAMA_API_TIMEOUT", "30"))

    # AI generation parameters
    LLAMA_TEMPERATURE = float(os.getenv("LLAMA_TEMPERATURE", "0.7"))
    LLAMA_MAX_TOKENS = int(os.getenv("LLAMA_MAX_TOKENS", "150"))
    LLAMA_TOP_P = float(os.getenv("LLAMA_TOP_P", "0.9"))

    # AI response settings
    AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.7"))
    AI_MAX_RESPONSE_TIME = int(os.getenv("AI_MAX_RESPONSE_TIME", "10"))
    USE_FALLBACK_RESPONSES = os.getenv("USE_FALLBACK_RESPONSES", "True").lower() == "true"