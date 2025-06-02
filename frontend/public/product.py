from typing import List, Optional
from datetime import datetime

class Product:
    """
    This is the data holder for products
    """
    def __init__(self, product_id: int = None, name: str = "", description: str = "",
             price: float = 0.0, stock: int = 0, tags: List[str] = None,
             images: List[str] = None, available_for_sale: int = 0):
        
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = price
        self.stock = stock
        self.tags = tags or []
        self.images = images or []
        # self.is_active = is_active can just check in stock
        #self.is_available = is_available
        self.available_for_sale = available_for_sale
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
        'available_for_sale': self.available_for_sale,
        'createdDate': self.created_date.isoformat() if self.created_date else None
        }

    @classmethod
    def from_dict(cls, data: dict):
        """
        dict -> obj
        when loading data from DB
        """
        try:
            # conv , str -> list for tags and imgs
            tags = data.get('tags', '')
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
            elif tags is None:
                tags = []
            
        
            images = data.get('images', '')
            if isinstance(images, str):
                images = [img.strip() for img in images.split(',') if img.strip()]
            elif images is None:
                images = []
            
            product = cls(
                product_id=data.get('productID'),
                name=data.get('name', ''),
                description=data.get('description', ''),
                price=float(data.get('price', 0)),
                stock=int(data.get('stock', 0)),
                tags=tags,
                images=images,
                available_for_sale=int(data.get('available_for_sale', 0))
            )
            
            
            if 'createdDate' in data and data['createdDate']:
                if isinstance(data['createdDate'], str):
                    product.created_date = datetime.fromisoformat(data['createdDate'])
                else:
                    product.created_date = data['createdDate']
            
            return product
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Error converting data to Product object: {str(e)}")

    def update_available_for_sale(self, quantity: int):
        """Reduce available_for_sale when items added to trolley"""
        if self.available_for_sale >= quantity:
            self.available_for_sale -= quantity
            return True
        return False
    
    def increase_available_for_sale(self, quantity: int):
        """Increase available_for_sale when items removed from trolley"""
        self.available_for_sale += quantity
    
    def is_in_stock(self) -> bool:
        """Check if product is in stock and available for sale."""
        return self.stock > 0 and self.available_for_sale >= 1

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