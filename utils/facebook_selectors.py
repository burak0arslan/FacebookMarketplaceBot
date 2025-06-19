"""
Robust Facebook Element Selectors
Updated selectors that work with current Facebook layout
"""

from selenium.webdriver.common.by import By
from typing import List, Tuple


class FacebookSelectors:
    """
    Robust Facebook element selectors with fallback options
    """

    @staticmethod
    def get_email_selectors() -> List[Tuple[str, str]]:
        """Get multiple selector options for email field"""
        return [
            (By.CSS_SELECTOR, 'input[name="email"]'),
            (By.CSS_SELECTOR, 'input[type="email"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="email"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="Email"]'),
            (By.CSS_SELECTOR, 'input[aria-label*="email"]'),
            (By.CSS_SELECTOR, 'input[aria-label*="Email"]'),
            (By.CSS_SELECTOR, 'input[data-testid*="email"]'),
            (By.ID, 'email'),
            (By.XPATH, '//input[@name="email"]'),
            (By.XPATH, '//input[@type="email"]'),
            (By.XPATH, '//input[contains(@placeholder, "email") or contains(@placeholder, "Email")]')
        ]

    @staticmethod
    def get_password_selectors() -> List[Tuple[str, str]]:
        """Get multiple selector options for password field"""
        return [
            (By.CSS_SELECTOR, 'input[name="pass"]'),
            (By.CSS_SELECTOR, 'input[name="password"]'),
            (By.CSS_SELECTOR, 'input[type="password"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="password"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="Password"]'),
            (By.CSS_SELECTOR, 'input[aria-label*="password"]'),
            (By.CSS_SELECTOR, 'input[aria-label*="Password"]'),
            (By.ID, 'pass'),
            (By.ID, 'password'),
            (By.XPATH, '//input[@name="pass"]'),
            (By.XPATH, '//input[@type="password"]')
        ]

    @staticmethod
    def get_login_button_selectors() -> List[Tuple[str, str]]:
        """Get multiple selector options for login button"""
        return [
            (By.CSS_SELECTOR, 'button[name="login"]'),
            (By.CSS_SELECTOR, 'button[type="submit"]'),
            (By.CSS_SELECTOR, 'input[type="submit"]'),
            (By.CSS_SELECTOR, 'button[data-testid="royal_login_button"]'),
            (By.CSS_SELECTOR, 'button[value="Log In"]'),
            (By.XPATH, '//button[@name="login"]'),
            (By.XPATH, '//button[@type="submit"]'),
            (By.XPATH, '//input[@type="submit"]'),
            (By.XPATH, '//button[contains(text(), "Log in") or contains(text(), "Log In")]'),
            (By.XPATH, '//input[@value="Log In" or @value="Log in"]')
        ]


def find_element_robust(driver, selectors: List[Tuple[str, str]], timeout: int = 5):
    """
    Try multiple selectors to find an element

    Args:
        driver: WebDriver instance
        selectors: List of (By.TYPE, selector_string) tuples
        timeout: Timeout for each selector attempt

    Returns:
        WebElement if found, None otherwise
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException

    for by_type, selector in selectors:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by_type, selector))
            )
            if element:
                return element
        except TimeoutException:
            continue
        except Exception:
            continue

    return None


# Updated browser utilities function
def find_element_safe_robust(browser_manager, element_type: str, timeout: int = 5):
    """
    Find Facebook elements using robust selectors

    Args:
        browser_manager: BrowserManager instance
        element_type: 'email', 'password', or 'login_button'
        timeout: Timeout for search

    Returns:
        WebElement if found, None otherwise
    """
    selectors_map = {
        'email': FacebookSelectors.get_email_selectors(),
        'password': FacebookSelectors.get_password_selectors(),
        'login_button': FacebookSelectors.get_login_button_selectors()
    }

    if element_type not in selectors_map:
        return None

    selectors = selectors_map[element_type]
    return find_element_robust(browser_manager.driver, selectors, timeout)


# Test function to verify selectors work
def test_facebook_selectors(browser_manager):
    """
    Test Facebook selectors on current page

    Args:
        browser_manager: BrowserManager instance

    Returns:
        Dict with test results
    """
    results = {
        'email_field': False,
        'password_field': False,
        'login_button': False,
        'page_loaded': False
    }

    try:
        # Check if we're on Facebook
        current_url = browser_manager.driver.current_url
        results['page_loaded'] = 'facebook.com' in current_url

        # Test email field
        email_element = find_element_safe_robust(browser_manager, 'email', timeout=3)
        results['email_field'] = email_element is not None

        # Test password field
        password_element = find_element_safe_robust(browser_manager, 'password', timeout=3)
        results['password_field'] = password_element is not None

        # Test login button
        login_element = find_element_safe_robust(browser_manager, 'login_button', timeout=3)
        results['login_button'] = login_element is not None

    except Exception as e:
        results['error'] = str(e)

    return results


# Example usage
if __name__ == "__main__":
    from utils.browser_utils import create_browser_manager
    from utils.logger import setup_logging, get_logger

    setup_logging()
    logger = get_logger(__name__)

    logger.info("Testing robust Facebook selectors...")

    try:
        with create_browser_manager(headless=False) as browser:
            # Navigate to Facebook
            if browser.navigate_to("https://www.facebook.com"):
                logger.info("Navigated to Facebook")

                # Test selectors
                results = test_facebook_selectors(browser)

                logger.info("Selector test results:")
                for element_type, found in results.items():
                    status = "✅" if found else "❌"
                    logger.info(f"  {element_type}: {status}")

                # Try to find email field with robust method
                email_field = find_element_safe_robust(browser, 'email')
                if email_field:
                    logger.info("✅ Successfully found email field with robust selectors")
                else:
                    logger.warning("⚠️ Email field not found - Facebook may have changed layout")

    except Exception as e:
        logger.error(f"Test error: {e}")