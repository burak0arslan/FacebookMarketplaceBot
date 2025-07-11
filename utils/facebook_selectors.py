"""
Facebook Selectors for Playwright
CSS selectors for various Facebook elements (more reliable than XPath)
"""

from typing import List, Tuple


class FacebookSelectors:
    """
    Collection of CSS selectors for Facebook elements
    Playwright works better with CSS selectors than XPath
    """

    # Login Page Selectors
    LOGIN_EMAIL_SELECTORS = [
        'input[name="email"]',
        'input[id="email"]',
        'input[type="email"]',
        'input[placeholder*="email" i]',
        'input[placeholder*="Email" i]',
        'input[aria-label*="email" i]'
    ]

    LOGIN_PASSWORD_SELECTORS = [
        'input[name="pass"]',
        'input[name="password"]',
        'input[id="pass"]',
        'input[id="password"]',
        'input[type="password"]',
        'input[placeholder*="password" i]',
        'input[aria-label*="password" i]'
    ]

    LOGIN_BUTTON_SELECTORS = [
        'button[name="login"]',
        'button[type="submit"]',
        'input[type="submit"]',
        'button[data-testid="royal_login_button"]',
        'button[value="Log In"]',
        'button:has-text("Log in")',
        'button:has-text("Log In")',
        'input[value="Log In"]',
        'input[value="Log in"]'
    ]

    # Navigation Selectors
    MARKETPLACE_SELECTORS = [
        'a[href*="/marketplace"]',
        'a[aria-label*="Marketplace" i]',
        'a:has-text("Marketplace")',
        '[data-testid*="marketplace"]',
        'div[role="button"]:has-text("Marketplace")'
    ]

    MESSAGES_SELECTORS = [
        'a[href*="/messages"]',
        'a[aria-label*="Messenger" i]',
        'a[aria-label*="Messages" i]',
        'a:has-text("Messages")',
        '[data-testid*="messages"]',
        '[data-testid*="messenger"]'
    ]

    # Marketplace Selectors
    MARKETPLACE_SEARCH_SELECTORS = [
        'input[placeholder*="Search Marketplace" i]',
        'input[aria-label*="Search Marketplace" i]',
        'input[name="query"]',
        '[role="searchbox"]'
    ]

    PRODUCT_LISTINGS_SELECTORS = [
        '[role="main"] a[href*="/marketplace/item/"]',
        'div[data-testid*="marketplace-item"]',
        'a[aria-label*="$"]',  # Product listings often have price in aria-label
        '.marketplace-item',
        '[data-testid="marketplace-product-item"]'
    ]

    # Messages/Chat Selectors
    MESSAGE_THREAD_SELECTORS = [
        '[role="grid"] div[role="row"]',
        '[data-testid="message-thread"]',
        '.conversation-item',
        'div[aria-label*="Conversation with"]'
    ]

    MESSAGE_INPUT_SELECTORS = [
        'div[role="textbox"]',
        'div[contenteditable="true"]',
        'textarea[placeholder*="Aa"]',
        'div[aria-label*="Message"]',
        'div[data-testid="message-input"]'
    ]

    SEND_BUTTON_SELECTORS = [
        'div[role="button"][aria-label*="Send" i]',
        'button[aria-label*="Send" i]',
        '[data-testid="send-button"]',
        'div[role="button"]:has-text("Send")'
    ]

    # CAPTCHA and Security
    CAPTCHA_SELECTORS = [
        '.captcha',
        '[data-testid="captcha"]',
        'iframe[src*="captcha"]',
        'div:has-text("Security Check")',
        'div:has-text("Please complete the security check")'
    ]

    TWO_FACTOR_SELECTORS = [
        'input[name="approvals_code"]',
        'input[placeholder*="confirmation code" i]',
        'input[aria-label*="confirmation code" i]',
        '[data-testid="two-factor-input"]'
    ]

    # Profile and Account
    PROFILE_MENU_SELECTORS = [
        '[data-testid="blue_bar_profile_link"]',
        'div[role="button"][aria-label*="Account" i]',
        'div[role="button"][aria-label*="Profile" i]',
        'img[alt*="profile" i]'
    ]

    LOGOUT_SELECTORS = [
        'div[role="menuitem"]:has-text("Log Out")',
        'a:has-text("Log Out")',
        'span:has-text("Log Out")',
        '[data-testid="logout"]'
    ]

    # Error and Status Messages
    ERROR_MESSAGE_SELECTORS = [
        '.error',
        '[role="alert"]',
        '.errorMessage',
        'div:has-text("error")',
        'div:has-text("Error")',
        '.validation-error'
    ]

    SUCCESS_MESSAGE_SELECTORS = [
        '.success',
        '.successMessage',
        'div:has-text("success")',
        'div:has-text("Success")'
    ]

    @staticmethod
    def get_login_email_selectors() -> List[str]:
        """Get multiple selector options for email input"""
        return FacebookSelectors.LOGIN_EMAIL_SELECTORS

    @staticmethod
    def get_login_password_selectors() -> List[str]:
        """Get multiple selector options for password input"""
        return FacebookSelectors.LOGIN_PASSWORD_SELECTORS

    @staticmethod
    def get_login_button_selectors() -> List[str]:
        """Get multiple selector options for login button"""
        return FacebookSelectors.LOGIN_BUTTON_SELECTORS

    @staticmethod
    def get_marketplace_selectors() -> List[str]:
        """Get multiple selector options for marketplace navigation"""
        return FacebookSelectors.MARKETPLACE_SELECTORS

    @staticmethod
    def get_messages_selectors() -> List[str]:
        """Get multiple selector options for messages navigation"""
        return FacebookSelectors.MESSAGES_SELECTORS

    @staticmethod
    def get_captcha_selectors() -> List[str]:
        """Get multiple selector options for CAPTCHA detection"""
        return FacebookSelectors.CAPTCHA_SELECTORS

    @staticmethod
    def get_error_selectors() -> List[str]:
        """Get multiple selector options for error messages"""
        return FacebookSelectors.ERROR_MESSAGE_SELECTORS


def find_element_with_fallback(page, selectors: List[str], timeout: int = 5000):
    """
    Try multiple selectors to find an element with Playwright

    Args:
        page: Playwright page object
        selectors: List of CSS selectors to try
        timeout: Timeout for each selector attempt

    Returns:
        Element if found, None otherwise
    """
    for selector in selectors:
        try:
            element = page.wait_for_selector(selector, timeout=timeout)
            if element:
                return element
        except Exception:
            continue
    return None


async def find_element_with_fallback_async(page, selectors: List[str], timeout: int = 5000):
    """
    Try multiple selectors to find an element with Playwright (async)

    Args:
        page: Playwright page object
        selectors: List of CSS selectors to try
        timeout: Timeout for each selector attempt

    Returns:
        Element if found, None otherwise
    """
    for selector in selectors:
        try:
            element = await page.wait_for_selector(selector, timeout=timeout)
            if element:
                return element
        except Exception:
            continue
    return None