from typing import List, Optional
from datetime import datetime

class Product:
    """
    This is the data holder for products
    """
    def __init__(self, product_id: int = None, name: str = "", description: str = "",
                 price: float = 0.0, stock: int = 0, tags: List[str] = None,
                 images: List[str] = None, is_available: bool = True):
        
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = price
        self.stock = stock
        self.tags = tags or []
        self.images = images or []
        # self.is_active = is_active can just check in stock
        self.is_available = is_available
        self.created_date = datetime.now()

    def to_dict(self) -> dict:
        """
        conv obj -> dict for API and DB comm
        """
        return {
            'productID': self.product_id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'stock': self.stock,
            'tags': self.tags,
            'images': self.images,
            'is_available': self.is_available,  
            # 'isActive': self.is_active,
            'createdDate': self.created_date.isoformat() if self.created_date else None
        }

    @classmethod
    def from_dict(cls, data: dict):
        """
        dict -> obj
        when loading data from DB
        """
        product = cls(
            product_id=data.get('productID'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            price=float(data.get('price', 0)),
            stock=int(data.get('stock', 0)),
            tags=data.get('tags', []),
            images=data.get('images', []),
            is_available=data.get('is_available', True)  
        )
        return product

    def update_available(self, quantity: int):
        """Use this as a storage count between in trolley vs actually ordered
        is_available would be reduced once a user adds a product to the trolley
        but stock would only be updated when the order is confirmed"""
        if self.is_available >= quantity:
            self.is_available -= quantity
            return True
        return False

    def is_in_stock(self) -> bool:
        """Check if product is in stock."""
        return self.stock > 0 and self.is_available  

    def reduce_stock(self, quantity: int) -> bool:
        """
        Reduce stock by given quantity.
        Returns True if successful, False if not enough stock.
        """
        if self.stock >= quantity:
            self.stock -= quantity
            return True
        return False

    def add_stock(self, quantity: int):
        """Add stock quantity."""
        self.stock += quantity

    def update_price(self, new_price: float):
        """Update product price."""
        if new_price >= 0:
            self.price = new_price

    def add_tag(self, tag: str):
        """Add a tag to the product."""
        if tag and tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str):
        """Remove a tag from the product."""
        if tag in self.tags:
            self.tags.remove(tag)

    def __str__(self):
        """String representation of the product."""
        return f"Product(ID: {self.product_id}, Name: {self.name}, Price: ${self.price}, Stock: {self.stock})"