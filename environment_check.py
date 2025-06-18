"""
Environment and Dependency Checker - Windows Compatible
Validates that all required dependencies are installed and working
"""

import sys
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """Check Python version compatibility"""
    print("Checking Python version...")

    version = sys.version_info
    print(f"Current Python version: {version.major}.{version.minor}.{version.micro}")

    if version.major == 3 and version.minor >= 8:
        print("✓ Python version is compatible")
        return True
    else:
        print("✗ Python 3.8+ required")
        return False

def check_virtual_environment():
    """Check if running in virtual environment"""
    print("\nChecking virtual environment...")

    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

    if in_venv:
        print("✓ Running in virtual environment")
        print(f"Virtual env path: {sys.prefix}")
        return True
    else:
        print("! Not running in virtual environment (recommended to use venv)")
        return False

def check_required_packages():
    """Check if all required packages are installed"""
    print("\nChecking required packages...")

    # Phase 1 dependencies
    phase1_packages = [
        'pandas',
        'openpyxl',
        'python-dotenv',
        'loguru'
    ]

    # Phase 2 dependencies
    phase2_packages = [
        'selenium',
        'webdriver-manager',
        'fake-useragent'
    ]

    # Additional dependencies
    other_packages = [
        'requests',
        'aiohttp',
        'Pillow',
        'validators',
        'schedule'
    ]

    all_packages = phase1_packages + phase2_packages + other_packages

    installed = []
    missing = []

    for package in all_packages:
        try:
            # Handle package name differences
            import_name = package.replace('-', '_')
            if package == 'python-dotenv':
                import_name = 'dotenv'
            elif package == 'Pillow':
                import_name = 'PIL'
            elif package == 'fake-useragent':
                import_name = 'fake_useragent'
            elif package == 'webdriver-manager':
                import_name = 'webdriver_manager'

            importlib.import_module(import_name)
            installed.append(package)
            print(f"✓ {package}")
        except ImportError:
            missing.append(package)
            print(f"✗ {package} - Not installed")

    print(f"\nPackage Status: {len(installed)}/{len(all_packages)} installed")

    if missing:
        print(f"\nTo install missing packages:")
        print(f"pip install {' '.join(missing)}")

    return len(missing) == 0

def check_chrome_installation():
    """Check if Chrome is installed and accessible"""
    print("\nChecking Chrome installation...")

    try:
        import shutil

        chrome_paths = [
            "chrome",
            "google-chrome",
            "chromium",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]

        chrome_found = False
        for path in chrome_paths:
            if shutil.which(path) or Path(path).exists():
                print(f"✓ Chrome found at: {path}")
                chrome_found = True
                break

        if not chrome_found:
            print("✗ Chrome not found in common locations")

        return chrome_found

    except Exception as e:
        print(f"✗ Error checking Chrome: {e}")
        return False

def check_chromedriver():
    """Check ChromeDriver availability"""
    print("\nChecking ChromeDriver...")

    try:
        # Try chromedriver-autoinstaller first
        try:
            import chromedriver_autoinstaller
            driver_path = chromedriver_autoinstaller.get_chrome_driver_path()
            if driver_path and Path(driver_path).exists():
                print(f"✓ ChromeDriver available: {driver_path}")
                return True
            else:
                print("! ChromeDriver not found, will be auto-installed")
                return True
        except ImportError:
            print("! chromedriver-autoinstaller not installed")

        # Try webdriver-manager as fallback
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            print("✓ webdriver-manager available for ChromeDriver")
            return True
        except ImportError:
            print("! webdriver-manager not installed")

        return False

    except Exception as e:
        print(f"! ChromeDriver check error: {e}")
        return True  # Not critical

def check_project_files():
    """Check if all project files are in place"""
    print("\nChecking project files...")

    required_files = {
        'config.py': 'Configuration system',
        'main.py': 'Main application entry point',
        'requirements.txt': 'Dependency list',
        'models/product.py': 'Product model',
        'models/account.py': 'Account model',
        'models/message.py': 'Message model',
        'services/excel_handler.py': 'Excel operations',
        'utils/logger.py': 'Logging system',
        'utils/browser_utils.py': 'Browser utilities'
    }

    missing_files = []

    for file_path, description in required_files.items():
        if Path(file_path).exists():
            print(f"✓ {file_path} - {description}")
        else:
            print(f"✗ {file_path} - {description}")
            missing_files.append(file_path)

    return len(missing_files) == 0

def check_data_directories():
    """Check if data directories exist"""
    print("\nChecking data directories...")

    try:
        from config import Config

        directories = {
            Config.DATA_DIR: 'Data directory',
            Config.LOGS_DIR: 'Logs directory',
            Config.SCREENSHOTS_DIR: 'Screenshots directory'
        }

        missing_dirs = []

        for dir_path, description in directories.items():
            if dir_path.exists():
                print(f"✓ {dir_path} - {description}")
            else:
                print(f"! {dir_path} - {description} (will be created)")
                missing_dirs.append(dir_path)

        # Create missing directories
        if missing_dirs:
            Config.ensure_directories()
            print("Created missing directories")

        return True

    except Exception as e:
        print(f"✗ Directory check error: {e}")
        return False

def check_sample_data():
    """Check if sample data files exist"""
    print("\nChecking sample data...")

    sample_files = [
        'data/sample_products.xlsx',
        'data/sample_accounts.xlsx'
    ]

    existing_files = []

    for file_path in sample_files:
        if Path(file_path).exists():
            print(f"✓ {file_path} exists")
            existing_files.append(file_path)
        else:
            print(f"! {file_path} not found (can be created)")

    return len(existing_files) > 0

def run_basic_functionality_test():
    """Run a basic test of core functionality"""
    print("\nRunning basic functionality test...")

    try:
        # Test logging
        from utils.logger import setup_logging, get_logger
        setup_logging()
        logger = get_logger("environment_check")
        logger.info("Environment check logging test")
        print("✓ Logging system working")

        # Test models
        from models.product import Product
        test_product = Product(
            title="Test Product",
            description="Test description",
            price=100.0,
            category="Test Category"
        )
        print("✓ Product model working")

        # Test configuration
        from config import Config
        Config.ensure_directories()
        print("✓ Configuration system working")

        return True

    except Exception as e:
        print(f"✗ Functionality test failed: {e}")
        return False

def generate_environment_report():
    """Generate comprehensive environment report"""
    print("=" * 60)
    print("FACEBOOK MARKETPLACE BOT - ENVIRONMENT CHECK")
    print("=" * 60)

    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_environment),
        ("Required Packages", check_required_packages),
        ("Chrome Installation", check_chrome_installation),
        ("ChromeDriver", check_chromedriver),
        ("Project Files", check_project_files),
        ("Data Directories", check_data_directories),
        ("Sample Data", check_sample_data),
        ("Basic Functionality", run_basic_functionality_test)
    ]

    results = {}
    passed = 0

    for check_name, check_func in checks:
        print(f"\n{'-' * 40}")
        result = check_func()
        results[check_name] = result
        if result:
            passed += 1

    # Summary
    print("\n" + "=" * 60)
    print("ENVIRONMENT SUMMARY")
    print("=" * 60)

    for check_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status} {check_name}")

    print(f"\nResults: {passed}/{len(checks)} checks passed")

    # Recommendations
    print("\nRECOMMENDATIONS:")

    if passed == len(checks):
        print("✓ Environment is fully ready!")
        print("✓ You can proceed with testing and development.")
    elif passed >= len(checks) - 2:
        print("✓ Environment is mostly ready.")
        print("! Fix minor issues and proceed with caution.")
    else:
        print("! Environment needs attention.")
        print("! Fix critical issues before proceeding.")

    return results

if __name__ == "__main__":
    print("Starting environment check...")
    results = generate_environment_report()
    print("\nEnvironment check completed!")