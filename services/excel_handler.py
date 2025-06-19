"""
Excel Handler Service for Facebook Marketplace Bot
This service handles reading and writing Excel files for products and accounts
"""

import pandas as pd
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from datetime import datetime

from models.product import Product
from models.account import Account


class ExcelHandler:
    """
    Handles Excel file operations for the Facebook Marketplace Bot

    This class provides methods to:
    - Read products from Excel files
    - Read accounts from Excel files
    - Write data back to Excel files
    - Validate Excel file formats
    - Create sample Excel files
    """

    def __init__(self, data_folder: str = "data"):
        """
        Initialize ExcelHandler

        Args:
            data_folder: Path to the data folder containing Excel files
        """
        self.data_folder = Path(data_folder)
        self.products_file = self.data_folder / "products.xlsx"
        self.accounts_file = self.data_folder / "accounts.xlsx"

        # Ensure data folder exists
        self.data_folder.mkdir(exist_ok=True)

        # Set up logging
        self.logger = logging.getLogger(__name__)

    def load_products(self, file_path: Optional[str] = None) -> List[Product]:
        """
        Load products from Excel file

        Args:
            file_path: Optional custom path to products Excel file

        Returns:
            List of Product objects

        Raises:
            FileNotFoundError: If Excel file doesn't exist
            ValueError: If Excel file format is invalid
        """
        excel_path = Path(file_path) if file_path else self.products_file

        if not excel_path.exists():
            self.logger.error(f"Products file not found: {excel_path}")
            raise FileNotFoundError(f"Products file not found: {excel_path}")

        try:
            # Read Excel file
            df = pd.read_excel(excel_path, engine='openpyxl')
            self.logger.info(f"Loaded products Excel file: {excel_path}")
            self.logger.info(f"Found {len(df)} rows in products file")

            # Validate required columns
            self._validate_products_format(df)

            # Convert rows to Product objects
            products = []
            for index, row in df.iterrows():
                try:
                    product = Product.from_excel_row(row)
                    products.append(product)
                    self.logger.debug(f"Created product: {product.title}")
                except Exception as e:
                    self.logger.warning(f"Failed to create product from row {index}: {e}")
                    continue

            self.logger.info(f"Successfully loaded {len(products)} products")
            return products

        except Exception as e:
            self.logger.error(f"Error loading products from {excel_path}: {e}")
            raise ValueError(f"Error loading products from {excel_path}: {e}")

    def load_accounts(self, file_path: Optional[str] = None) -> List[Account]:
        """
        Load accounts from Excel file

        Args:
            file_path: Optional custom path to accounts Excel file

        Returns:
            List of Account objects

        Raises:
            FileNotFoundError: If Excel file doesn't exist
            ValueError: If Excel file format is invalid
        """
        excel_path = Path(file_path) if file_path else self.accounts_file

        if not excel_path.exists():
            self.logger.error(f"Accounts file not found: {excel_path}")
            raise FileNotFoundError(f"Accounts file not found: {excel_path}")

        try:
            # Read Excel file
            df = pd.read_excel(excel_path, engine='openpyxl')
            self.logger.info(f"Loaded accounts Excel file: {excel_path}")
            self.logger.info(f"Found {len(df)} rows in accounts file")

            # Validate required columns
            self._validate_accounts_format(df)

            # Convert rows to Account objects
            accounts = []
            for index, row in df.iterrows():
                try:
                    account = Account.from_excel_row(row)
                    accounts.append(account)
                    self.logger.debug(f"Created account: {account.get_masked_email()}")
                except Exception as e:
                    self.logger.warning(f"Failed to create account from row {index}: {e}")
                    continue

            self.logger.info(f"Successfully loaded {len(accounts)} accounts")
            return accounts

        except Exception as e:
            self.logger.error(f"Error loading accounts from {excel_path}: {e}")
            raise ValueError(f"Error loading accounts from {excel_path}: {e}")

    def save_products(self, products: List[Product], file_path: Optional[str] = None) -> bool:
        """
        Save products to Excel file

        Args:
            products: List of Product objects to save
            file_path: Optional custom path for output file

        Returns:
            True if successful, False otherwise
        """
        excel_path = Path(file_path) if file_path else self.products_file

        try:
            # Convert products to DataFrame
            products_data = []
            for product in products:
                product_dict = product.to_dict()
                # Convert lists to comma-separated strings for Excel
                product_dict['images'] = ','.join(product_dict['images'])
                product_dict['keywords'] = ','.join(product_dict['keywords'])
                products_data.append(product_dict)

            df = pd.DataFrame(products_data)

            # Reorder columns for better readability
            column_order = ['title', 'description', 'price', 'category', 'images',
                          'location', 'keywords', 'condition', 'availability',
                          'contact_info', 'listing_id', 'created_at', 'updated_at']

            # Only include columns that exist
            df = df.reindex(columns=[col for col in column_order if col in df.columns])

            # Save to Excel
            df.to_excel(excel_path, index=False)
            self.logger.info(f"Saved {len(products)} products to {excel_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving products to {excel_path}: {e}")
            return False

    def save_accounts(self, accounts: List[Account], file_path: Optional[str] = None,
                     include_passwords: bool = True) -> bool:
        """
        Save accounts to Excel file

        Args:
            accounts: List of Account objects to save
            file_path: Optional custom path for output file
            include_passwords: Whether to include passwords in the file

        Returns:
            True if successful, False otherwise
        """
        excel_path = Path(file_path) if file_path else self.accounts_file

        try:
            # Convert accounts to DataFrame
            accounts_data = []
            for account in accounts:
                account_dict = account.to_dict(include_password=include_passwords)
                accounts_data.append(account_dict)

            df = pd.DataFrame(accounts_data)

            # Reorder columns for better readability
            column_order = ['email', 'password', 'profile_name', 'active', 'message_monitor',
                          'proxy', 'user_agent', 'account_status', 'login_count',
                          'listing_count', 'message_count', 'last_login', 'notes']

            # Only include columns that exist
            df = df.reindex(columns=[col for col in column_order if col in df.columns])

            # Save to Excel
            df.to_excel(excel_path, index=False)
            self.logger.info(f"Saved {len(accounts)} accounts to {excel_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving accounts to {excel_path}: {e}")
            return False

    def create_sample_products_file(self, file_path: Optional[str] = None) -> bool:
        """
        Create a sample products Excel file with example data

        Args:
            file_path: Optional path for the sample file

        Returns:
            True if successful, False otherwise
        """
        excel_path = Path(file_path) if file_path else (self.data_folder / "sample_products.xlsx")

        try:
            sample_data = [
                {
                    'Title': 'iPhone 13 Pro - Excellent Condition',
                    'Description': 'Barely used iPhone 13 Pro in excellent condition. No scratches, all original accessories included. Battery health 98%.',
                    'Price': 650.00,
                    'Category': 'Electronics',
                    'Images': 'iphone1.jpg,iphone2.jpg,iphone3.jpg',
                    'Location': 'New York, NY',
                    'Keywords': 'iphone,apple,smartphone,mobile,13pro',
                    'Condition': 'Used - Like New',
                    'ContactInfo': 'Text for fastest response'
                },
                {
                    'Title': 'MacBook Air M1 - 256GB',
                    'Description': 'Apple MacBook Air with M1 chip, 8GB RAM, 256GB SSD. Perfect for students and professionals.',
                    'Price': 800.00,
                    'Category': 'Electronics',
                    'Images': 'macbook1.jpg,macbook2.jpg',
                    'Location': 'Los Angeles, CA',
                    'Keywords': 'macbook,apple,laptop,m1,computer',
                    'Condition': 'Used - Good',
                    'ContactInfo': 'Available for pickup or shipping'
                },
                {
                    'Title': 'Nike Air Jordan 1 - Size 10',
                    'Description': 'Classic Nike Air Jordan 1 sneakers in size 10. Great condition, minimal wear.',
                    'Price': 150.00,
                    'Category': 'Clothing & Accessories',
                    'Images': 'jordan1.jpg,jordan2.jpg,jordan3.jpg',
                    'Location': 'Chicago, IL',
                    'Keywords': 'nike,jordan,sneakers,shoes,basketball',
                    'Condition': 'Used - Good',
                    'ContactInfo': 'Cash or Venmo accepted'
                }
            ]

            df = pd.DataFrame(sample_data)
            df.to_excel(excel_path, index=False)
            self.logger.info(f"Created sample products file: {excel_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error creating sample products file: {e}")
            return False

    def create_sample_accounts_file(self, file_path: Optional[str] = None) -> bool:
        """
        Create a sample accounts Excel file with example data

        Args:
            file_path: Optional path for the sample file

        Returns:
            True if successful, False otherwise
        """
        excel_path = Path(file_path) if file_path else (self.data_folder / "sample_accounts.xlsx")

        try:
            sample_data = [
                {
                    'Email': 'seller1@gmail.com',
                    'Password': 'your_password_here',
                    'ProfileName': 'John Seller',
                    'Active': True,
                    'MessageMonitor': True,
                    'Proxy': '',
                    'UserAgent': '',
                    'Status': 'active',
                    'Notes': 'Main selling account'
                },
                {
                    'Email': 'seller2@yahoo.com',
                    'Password': 'your_password_here',
                    'ProfileName': 'Jane Smith',
                    'Active': True,
                    'MessageMonitor': False,
                    'Proxy': '',
                    'UserAgent': '',
                    'Status': 'active',
                    'Notes': 'Secondary account - listing only'
                },
                {
                    'Email': 'backup@outlook.com',
                    'Password': 'your_password_here',
                    'ProfileName': 'Mike Johnson',
                    'Active': False,
                    'MessageMonitor': False,
                    'Proxy': '',
                    'UserAgent': '',
                    'Status': 'inactive',
                    'Notes': 'Backup account - not currently used'
                }
            ]

            df = pd.DataFrame(sample_data)
            df.to_excel(excel_path, index=False)
            self.logger.info(f"Created sample accounts file: {excel_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error creating sample accounts file: {e}")
            return False

    def _validate_products_format(self, df: pd.DataFrame) -> None:
        """
        Validate that the products DataFrame has required columns

        Args:
            df: Products DataFrame to validate

        Raises:
            ValueError: If required columns are missing
        """
        required_columns = ['Title', 'Description', 'Price', 'Category']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(f"Products file missing required columns: {missing_columns}")

        # Check for empty required fields
        for col in required_columns:
            if df[col].isna().any():
                self.logger.warning(f"Products file has empty values in required column: {col}")

    def _validate_accounts_format(self, df: pd.DataFrame) -> None:
        """
        Validate that the accounts DataFrame has required columns

        Args:
            df: Accounts DataFrame to validate

        Raises:
            ValueError: If required columns are missing
        """
        required_columns = ['Email', 'Password', 'ProfileName']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(f"Accounts file missing required columns: {missing_columns}")

        # Check for empty required fields
        for col in required_columns:
            if df[col].isna().any():
                self.logger.warning(f"Accounts file has empty values in required column: {col}")

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about an Excel file

        Args:
            file_path: Path to the Excel file

        Returns:
            Dictionary with file information
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return {'exists': False, 'error': 'File not found'}

        try:
            df = pd.read_excel(file_path)
            return {
                'exists': True,
                'rows': len(df),
                'columns': list(df.columns),
                'file_size': file_path.stat().st_size,
                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }
        except Exception as e:
            return {'exists': True, 'error': str(e)}


# Example usage and testing
if __name__ == "__main__":
    # Set up logging for testing
    logging.basicConfig(level=logging.INFO)

    # Create ExcelHandler instance
    excel_handler = ExcelHandler()

    # Create sample files
    print("Creating sample files...")
    excel_handler.create_sample_products_file()
    excel_handler.create_sample_accounts_file()

    # Test loading sample files
    try:
        print("\nTesting products loading...")
        products = excel_handler.load_products("data/sample_products.xlsx")
        print(f"Loaded {len(products)} products")
        for product in products:
            print(f"  - {product.title}: {product.get_formatted_price()}")

        print("\nTesting accounts loading...")
        accounts = excel_handler.load_accounts("data/sample_accounts.xlsx")
        print(f"Loaded {len(accounts)} accounts")
        for account in accounts:
            print(f"  - {account.get_masked_email()}: {account.profile_name}")

        # Test file info
        print("\nFile information:")
        products_info = excel_handler.get_file_info("data/sample_products.xlsx")
        print(f"Products file: {products_info}")

    except Exception as e:
        print(f"Error during testing: {e}")