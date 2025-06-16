"""
Account Model for Facebook Marketplace Bot
This class represents a Facebook account used for marketplace automation
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import pandas as pd
from datetime import datetime


@dataclass
class Account:
    """
    Represents a Facebook account for marketplace automation

    Attributes:
        email: Facebook login email
        password: Facebook login password
        profile_name: Display name on the profile
        active: Whether this account should be used
        message_monitor: Whether to monitor messages for this account
        proxy: Proxy settings for this account (optional)
        user_agent: Custom user agent for this account
        last_login: Last successful login timestamp
        login_count: Number of successful logins
        listing_count: Number of products listed with this account
        message_count: Number of messages sent from this account
        account_status: Current status (active, suspended, blocked, etc.)
        notes: Additional notes about this account
    """

    # Required fields
    email: str
    password: str
    profile_name: str

    # Optional account settings
    active: bool = True
    message_monitor: bool = True
    proxy: Optional[str] = None
    user_agent: Optional[str] = None

    # Tracking fields
    last_login: Optional[str] = None
    login_count: int = 0
    listing_count: int = 0
    message_count: int = 0

    # Status and metadata
    account_status: str = "active"
    notes: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and clean data after initialization"""
        self._validate_data()
        self._clean_data()

        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def _validate_data(self):
        """Validate account data"""
        if not self.email or not self.email.strip():
            raise ValueError("Email cannot be empty")

        if not self.password or not self.password.strip():
            raise ValueError("Password cannot be empty")

        if not self.profile_name or not self.profile_name.strip():
            raise ValueError("Profile name cannot be empty")

        # Basic email validation
        if "@" not in self.email or "." not in self.email:
            raise ValueError("Invalid email format")

    def _clean_data(self):
        """Clean and format data"""
        # Clean strings
        self.email = self.email.strip().lower()
        self.password = self.password.strip()
        self.profile_name = self.profile_name.strip()
        self.account_status = self.account_status.strip().lower()
        self.notes = self.notes.strip()

        # Clean proxy if provided
        if self.proxy:
            self.proxy = self.proxy.strip()

    @classmethod
    def from_excel_row(cls, row: pd.Series) -> 'Account':
        """
        Create Account instance from Excel row

        Args:
            row: Pandas Series representing one row from Excel

        Returns:
            Account instance
        """
        # Handle boolean fields
        active = True
        if pd.notna(row.get('Active')):
            active_val = str(row.get('Active', 'TRUE')).upper()
            active = active_val in ['TRUE', '1', 'YES', 'Y']

        message_monitor = True
        if pd.notna(row.get('MessageMonitor')):
            monitor_val = str(row.get('MessageMonitor', 'TRUE')).upper()
            message_monitor = monitor_val in ['TRUE', '1', 'YES', 'Y']

        return cls(
            email=str(row.get('Email', '')),
            password=str(row.get('Password', '')),
            profile_name=str(row.get('ProfileName', row.get('Name', ''))),
            active=active,
            message_monitor=message_monitor,
            proxy=str(row.get('Proxy', '')) if pd.notna(row.get('Proxy')) else None,
            user_agent=str(row.get('UserAgent', '')) if pd.notna(row.get('UserAgent')) else None,
            account_status=str(row.get('Status', 'active')),
            notes=str(row.get('Notes', ''))
        )

    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        """
        Convert Account to dictionary

        Args:
            include_password: Whether to include password in output (default: False for security)
        """
        data = {
            'email': self.email,
            'profile_name': self.profile_name,
            'active': self.active,
            'message_monitor': self.message_monitor,
            'proxy': self.proxy,
            'user_agent': self.user_agent,
            'last_login': self.last_login,
            'login_count': self.login_count,
            'listing_count': self.listing_count,
            'message_count': self.message_count,
            'account_status': self.account_status,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metadata': self.metadata
        }

        if include_password:
            data['password'] = self.password

        return data

    def update_login_stats(self) -> None:
        """Update login statistics"""
        self.last_login = datetime.now().isoformat()
        self.login_count += 1
        self.updated_at = datetime.now().isoformat()

    def increment_listing_count(self) -> None:
        """Increment the number of listings created with this account"""
        self.listing_count += 1
        self.updated_at = datetime.now().isoformat()

    def increment_message_count(self) -> None:
        """Increment the number of messages sent from this account"""
        self.message_count += 1
        self.updated_at = datetime.now().isoformat()

    def set_status(self, status: str, notes: str = "") -> None:
        """
        Update account status

        Args:
            status: New status (active, suspended, blocked, error, etc.)
            notes: Additional notes about the status change
        """
        self.account_status = status.lower().strip()
        if notes:
            self.notes = f"{self.notes}\n{datetime.now().strftime('%Y-%m-%d %H:%M')}: {notes}".strip()
        self.updated_at = datetime.now().isoformat()

    def is_usable(self) -> bool:
        """Check if account can be used for automation"""
        return (self.active and
                self.account_status in ['active', 'good'] and
                self.email and
                self.password and
                self.profile_name)

    def is_ready_for_messaging(self) -> bool:
        """Check if account can be used for message monitoring"""
        return self.is_usable() and self.message_monitor

    def get_masked_email(self) -> str:
        """Get masked email for logging (security)"""
        if not self.email or '@' not in self.email:
            return "invalid_email"

        username, domain = self.email.split('@', 1)
        if len(username) <= 2:
            masked_username = username
        else:
            masked_username = username[0] + '*' * (len(username) - 2) + username[-1]

        return f"{masked_username}@{domain}"

    def get_days_since_last_login(self) -> Optional[int]:
        """Get number of days since last login"""
        if not self.last_login:
            return None

        try:
            last_login_dt = datetime.fromisoformat(self.last_login)
            delta = datetime.now() - last_login_dt
            return delta.days
        except:
            return None

    def add_note(self, note: str) -> None:
        """Add a timestamped note to the account"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        new_note = f"{timestamp}: {note}"

        if self.notes:
            self.notes = f"{self.notes}\n{new_note}"
        else:
            self.notes = new_note

        self.updated_at = datetime.now().isoformat()

    def __str__(self) -> str:
        """String representation of Account"""
        return f"Account('{self.get_masked_email()}', {self.profile_name}, active={self.active})"

    def __repr__(self) -> str:
        """Detailed string representation of Account"""
        return (f"Account(email='{self.get_masked_email()}', profile='{self.profile_name}', "
                f"status='{self.account_status}', logins={self.login_count}, "
                f"listings={self.listing_count}, messages={self.message_count})")


# Example usage and testing
if __name__ == "__main__":
    # Example 1: Create account manually
    account1 = Account(
        email="seller1@gmail.com",
        password="secure_password_123",
        profile_name="John Seller",
        active=True,
        message_monitor=True
    )

    print("Account 1:", account1)
    print("Masked email:", account1.get_masked_email())
    print("Is usable:", account1.is_usable())
    print("Ready for messaging:", account1.is_ready_for_messaging())

    # Test login statistics
    account1.update_login_stats()
    account1.increment_listing_count()
    print("After login and listing:", account1)

    # Example 2: Create from dictionary (simulating Excel data)
    excel_data = {
        'Email': 'seller2@yahoo.com',
        'Password': 'another_password',
        'ProfileName': 'Jane Smith',
        'Active': 'TRUE',
        'MessageMonitor': 'YES',
        'Notes': 'Test account for automation'
    }

    # Convert dict to pandas Series (simulating Excel row)
    row = pd.Series(excel_data)
    account2 = Account.from_excel_row(row)

    print("\nAccount 2:", account2)
    print("Account status:", account2.account_status)

    # Test status change
    account2.set_status("suspended", "Account flagged for review")
    print("After status change:", account2.account_status)
    print("Notes:", account2.notes)