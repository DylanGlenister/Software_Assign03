#------to update ------
#instance per request 
#on initialisation we put in a product ID and then it will call the database and get all the stuff for the product 


from typing import List, Optional, Type
from datetime import datetime
from ..core.database import Database

class Product:
    """ get product data on intialisation"""
    def __init__(self, product_id: int, db: Database):
        """ initialise product by database fetch on product ID"""
        self.product_id = product_id
        self.db = db
        
        # product data from database
        product_data = self.db.get_product(product_id)
        if not product_data:
            raise ValueError(f"No product found with ID: {product_id}")
        
        # initialise attributes from database 
        self._load_from_db_data(product_data)
    
    def _load_from_db_data(self, data):
        """Load product attributes from database data"""
        self.name = data.get('name', '')
        self.description = data.get('description', '')
        self.price = float(data.get('price', 0))
        self.stock = int(data.get('stock', 0))
        
        tags = data.get('tags', '')
        if isinstance(tags, str):
            self.tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
        else:
            self.tags = tags or []
        
        images = data.get('images', '')
        if isinstance(images, str):
            self.images = [img.strip() for img in images.split(',') if img.strip()]
        else:
            self.images = images or []
        
        self.available_for_sale = int(data.get('available_for_sale', 0))
        
        if 'createdDate' in data and data['createdDate']:
            if isinstance(data['createdDate'], str):
                self.created_date = datetime.fromisoformat(data['createdDate'])
            else:
                self.created_date = data['createdDate']
        else:
            self.created_date = datetime.now()
    
    @classmethod
    def create_new(cls, db: Database, name: str = "", description: str = "",
                   price: float = 0.0, stock: int = 0, tags: List[str] = None,
                   images: List[str] = None, available_for_sale: int = 0):
        
        """create a new product in the database and return Product instance"""

        product_data = {
            'name': name,
            'description': description,
            'price': price,
            'stock': stock,
            'tags': ','.join(tags) if tags else '',
            'images': ','.join(images) if images else '',
            'available_for_sale': available_for_sale,
            'createdDate': datetime.now().isoformat()
        }
        
        # insert in to dsatabse and get new product ID
        product_id = db.create_product(product_data)
        if not product_id:
            raise ValueError("Failed to create product in database")
        
        return cls(product_id, db)
    
    @classmethod
    def get_all_products(cls, db: Database) -> List["Product"]:
        """get all existin products from database"""
        product_ids = db.get_all_product_ids()
        return [cls(product_id, db) for product_id in product_ids]
    
    @classmethod
    def search_products(cls, db: Database, **search_criteria) -> List["Product"]:
        """search products"""
        #passes search parameters we provide directly to the database layer 
        product_ids = db.search_products(**search_criteria)
        return [cls(product_id, db) for product_id in product_ids]

    def refresh_from_db(self):
        """refresh product datato get latest updates"""
        product_data = self.db.get_product(self.product_id)
        if product_data:
            self._load_from_db_data(product_data)
        else:
            raise ValueError(f"Product with ID {self.product_id} no longer exists")

    def save_to_db(self) -> bool:
        """save curent product state to database"""
        product_data = {
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'stock': self.stock,
            'tags': ','.join(self.tags),
            'images': ','.join(self.images),
            'available_for_sale': self.available_for_sale,
            'createdDate': self.created_date.isoformat() if self.created_date else None
        }
        
        return self.db.update_product(self.product_id, **product_data)

    def delete_from_db(self) -> bool:
        """delete product"""
        return self.db.delete_product(self.product_id)

    def to_dict(self) -> dict:
        """convert object to dict for API and DB communication - ? """

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

    def update_available_for_sale(self, quantity: int) -> bool:
        """reduce available_for_sale when items added to trolley - so that 2 people cant but the last remaining"""
        if self.available_for_sale >= quantity:
            self.available_for_sale -= quantity
            self.save_to_db()  
            return True
        return False
    
    def increase_available_for_sale(self, quantity: int):
        """increase available_for_sale when items removed from trolley without purchase"""
        self.available_for_sale += quantity
        self.save_to_db()  
    
    def is_in_stock(self) -> bool:
        """check if product is in stock and available for sale."""
        return self.stock > 0 and self.available_for_sale >= 1

    def reduce_stock(self, quantity: int) -> bool:
        """reduce stock by given quantity """
        if self.stock >= quantity:
            self.stock -= quantity
            return self.save_to_db()
        return False

    def add_stock(self, quantity: int) -> bool:
        """add stock quantity """
        self.stock += quantity
        return self.save_to_db()

    def update_price(self, new_price: float) -> bool:
        """update product price"""
        if new_price >= 0:
            self.price = new_price
            return self.save_to_db()
        return False

    def update_name(self, new_name: str) -> bool:
        """update product name"""
        if new_name and new_name.strip():
            self.name = new_name.strip()
            return self.save_to_db()
        return False

    def update_description(self, new_description: str) -> bool:
        """update product description """
        self.description = new_description
        return self.save_to_db()

    def update_stock(self, new_stock: int) -> bool:
        """update product stock"""
        if new_stock >= 0:
            self.stock = new_stock
            return self.save_to_db()
        return False

    def update_available_for_sale(self, new_available: int) -> bool:
        """update available_for_sale quantity """
        if new_available >= 0:
            self.available_for_sale = new_available
            return self.save_to_db()
        return False

    def set_images(self, images: List[str]) -> bool:
        """set product images list """
        self.images = images or []
        return self.save_to_db()

    def add_image(self, image_url: str) -> bool:
        """add image to the product"""
        if image_url and image_url not in self.images:
            self.images.append(image_url)
            return self.save_to_db()
        return False

    def remove_image(self, image_url: str) -> bool:
        """remove image from the product"""
        if image_url in self.images:
            self.images.remove(image_url)
            return self.save_to_db()
        return False

    def add_tag(self, tag: str) -> bool:
        """add a tag to the product"""
        if tag and tag not in self.tags:
            self.tags.append(tag)
            return self.save_to_db()
        return False

    def remove_tag(self, tag: str) -> bool:
        """remove a tag """
        if tag in self.tags:
            self.tags.remove(tag)
            return self.save_to_db()
        return False

    def __str__(self):
        """string rep of the product"""
        return f"Product(ID: {self.product_id}, Name: {self.name}, Price: ${self.price}, Stock: {self.stock})"