"""
Product Model for Facebook Marketplace Bot
This class represents a product that will be listed on Facebook Marketplace
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import pandas as pd
from pathlib import Path


@dataclass
class Product:
    """
    Represents a product to be listed on Facebook Marketplace

    Attributes:
        title: Product title/name
        description: Full product description
        price: Selling price in USD
        category: Facebook Marketplace category
        images: List of image file paths
        location: Pickup/delivery location
        keywords: Search keywords for the product
        condition: Product condition (New, Used - Like New, Used - Good, etc.)
        availability: Whether product is still available
        contact_info: Additional contact information
        listing_id: Facebook listing ID (set after successful listing)
        created_at: When this product record was created
        updated_at: When this product record was last updated
    """

    # Required fields
    title: str
    description: str
    price: float
    category: str

    # Optional fields with defaults
    images: List[str] = field(default_factory=list)
    location: str = ""
    keywords: List[str] = field(default_factory=list)
    condition: str = "Used - Good"
    availability: bool = True
    contact_info: str = ""

    # System fields
    listing_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and clean data after initialization"""
        self._validate_data()
        self._clean_data()

    def _validate_data(self):
        """Validate product data"""
        if not self.title or not self.title.strip():
            raise ValueError("Product title cannot be empty")

        if not self.description or not self.description.strip():
            raise ValueError("Product description cannot be empty")

        if self.price <= 0:
            raise ValueError("Product price must be greater than 0")

        if not self.category or not self.category.strip():
            raise ValueError("Product category cannot be empty")

        # Validate image paths exist
        for image_path in self.images:
            if not Path(image_path).exists():
                print(f"Warning: Image file not found: {image_path}")

    def _clean_data(self):
        """Clean and format data"""
        # Clean strings
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.category = self.category.strip()
        self.location = self.location.strip()
        self.condition = self.condition.strip()

        # Clean keywords - remove empty strings and duplicates
        self.keywords = list(set([kw.strip().lower() for kw in self.keywords if kw.strip()]))

        # Ensure price is float
        self.price = float(self.price)

    @classmethod
    def from_excel_row(cls, row: pd.Series) -> 'Product':
        """
        Create Product instance from Excel row

        Args:
            row: Pandas Series representing one row from Excel

        Returns:
            Product instance
        """
        # Handle images - split comma-separated string into list
        images = []
        if pd.notna(row.get('Images', '')) and row.get('Images', '').strip():
            images = [img.strip() for img in str(row['Images']).split(',') if img.strip()]

        # Handle keywords - split comma-separated string into list
        keywords = []
        if pd.notna(row.get('Keywords', '')) and row.get('Keywords', '').strip():
            keywords = [kw.strip() for kw in str(row['Keywords']).split(',') if kw.strip()]

        return cls(
            title=str(row.get('Title', '')),
            description=str(row.get('Description', '')),
            price=float(row.get('Price', 0)),
            category=str(row.get('Category', '')),
            images=images,
            location=str(row.get('Location', '')),
            keywords=keywords,
            condition=str(row.get('Condition', 'Used - Good')),
            contact_info=str(row.get('ContactInfo', ''))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Product to dictionary"""
        return {
            'title': self.title,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'images': self.images,
            'location': self.location,
            'keywords': self.keywords,
            'condition': self.condition,
            'availability': self.availability,
            'contact_info': self.contact_info,
            'listing_id': self.listing_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metadata': self.metadata
        }

    def get_image_count(self) -> int:
        """Get number of images for this product"""
        return len(self.images)

    def add_image(self, image_path: str) -> None:
        """Add an image to the product"""
        if image_path and image_path not in self.images:
            self.images.append(image_path)

    def remove_image(self, image_path: str) -> None:
        """Remove an image from the product"""
        if image_path in self.images:
            self.images.remove(image_path)

    def add_keyword(self, keyword: str) -> None:
        """Add a keyword to the product"""
        cleaned_keyword = keyword.strip().lower()
        if cleaned_keyword and cleaned_keyword not in self.keywords:
            self.keywords.append(cleaned_keyword)

    def get_formatted_price(self) -> str:
        """Get formatted price string for display"""
        return f"${self.price:,.2f}"

    def get_short_description(self, max_length: int = 100) -> str:
        """Get truncated description for previews"""
        if len(self.description) <= max_length:
            return self.description
        return self.description[:max_length - 3] + "..."

    def is_ready_for_listing(self) -> bool:
        """Check if product has all required data for listing"""
        required_fields = [self.title, self.description, self.category]
        return all(field.strip() for field in required_fields) and self.price > 0

    def __str__(self) -> str:
        """String representation of Product"""
        return f"Product('{self.title}', ${self.price}, {self.category})"

    def __repr__(self) -> str:
        """Detailed string representation of Product"""
        return (f"Product(title='{self.title}', price={self.price}, "
                f"category='{self.category}', images={len(self.images)}, "
                f"available={self.availability})")


# Example usage and testing
if __name__ == "__main__":
    # Example 1: Create product manually
    product1 = Product(
        title="iPhone 13 Pro - Excellent Condition",
        description="Barely used iPhone 13 Pro in excellent condition. No scratches, all original accessories included.",
        price=650.00,
        category="Electronics",
        images=["iphone1.jpg", "iphone2.jpg", "iphone3.jpg"],
        location="New York, NY",
        keywords=["iphone", "apple", "smartphone", "mobile"],
        condition="Used - Like New"
    )

    print("Product 1:", product1)
    print("Formatted price:", product1.get_formatted_price())
    print("Ready for listing:", product1.is_ready_for_listing())
    print("Image count:", product1.get_image_count())

    # Example 2: Create from dictionary (simulating Excel data)
    excel_data = {
        'Title': 'MacBook Air M1',
        'Description': 'Apple MacBook Air with M1 chip, 8GB RAM, 256GB SSD',
        'Price': 800,
        'Category': 'Electronics',
        'Images': 'macbook1.jpg,macbook2.jpg',
        'Location': 'Los Angeles, CA',
        'Keywords': 'macbook,apple,laptop,m1',
        'Condition': 'Used - Good'
    }

    # Convert dict to pandas Series (simulating Excel row)
    row = pd.Series(excel_data)
    product2 = Product.from_excel_row(row)

    print("\nProduct 2:", product2)
    print("Keywords:", product2.keywords)
    print("Images:", product2.images)