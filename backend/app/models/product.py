# ------to update ------
# instance per request
# on initialisation we put in a product ID and then it will call the
# database and get all the stuff for the product
from datetime import datetime
from ..core.database import Database


class Product:
    """get product data on intialisation"""

    def __init__(self, product_id: int, db: Database):
        """initialise product by database fetch on product ID"""
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
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.price = float(data.get("price", 0))
        self.stock = int(data.get("stock", 0))

        tags = data.get("tags", "")
        if isinstance(tags, str):
            self.tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        else:
            self.tags = tags or []

        images = data.get("images", "")
        if isinstance(images, str):
            self.images = [img.strip()
                           for img in images.split(",") if img.strip()]
        else:
            self.images = images or []

        self.available_for_sale = int(data.get("available_for_sale", 0))

        if "createdDate" in data and data["createdDate"]:
            if isinstance(data["createdDate"], str):
                self.created_date = datetime.fromisoformat(data["createdDate"])
            else:
                self.created_date = data["createdDate"]
        else:
            self.created_date = datetime.now()

    @classmethod
    def create_new(
        cls,
        db: Database,
        name: str = "",
        description: str = "",
        price: float = 0.0,
        stock: int = 0,
        tags: list[str] = None,
        images: list[str] = None,
        available_for_sale: int = 0,
    ):
        """create a new product in the database and return Product instance"""

        product_data = {
            "name": name,
            "description": description,
            "price": price,
            "stock": stock,
            "tags": ",".join(tags) if tags else "",
            "images": ",".join(images) if images else "",
            "available_for_sale": available_for_sale,
            "createdDate": datetime.now().isoformat(),
        }

        # insert in to dsatabse and get new product ID
        product_id = db.create_product(product_data)
        if not product_id:
            raise ValueError("Failed to create product in database")

        return cls(product_id, db)

    def refresh_from_db(self):
        """refresh product datato get latest updates"""
        product_data = self.db.get_product(self.product_id)
        if product_data:
            self._load_from_db_data(product_data)
        else:
            raise ValueError(
                f"Product with ID {
                    self.product_id} no longer exists")

    def save_to_db(self) -> bool:
        """save curent product state to database"""
        product_data = {
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "stock": self.stock,
            "tags": ",".join(self.tags),
            "images": ",".join(self.images),
            "available_for_sale": self.available_for_sale,
            "createdDate": self.created_date.isoformat() if self.created_date else None,
        }

        return self.db.update_product(self.product_id, **product_data)

    def delete_from_db(self) -> bool:
        """delete product"""
        return self.db.delete_product(self.product_id)

    def to_dict(self) -> dict:
        """convert object to dict for API and DB communication - ?"""

        return {
            "productID": self.product_id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "stock": self.stock,
            "tags": self.tags,
            "images": self.images,
            "available_for_sale": self.available_for_sale,
            "createdDate": self.created_date.isoformat() if self.created_date else None,
        }

    # combined increase and decrease availble for sale
    def update_available_for_sale(self, quantity: int) -> bool:
        """reduce available_for_sale when items added to trolley - so that 2 people cant but the last remaining"""
        if quantity > 0:
            # when dding to trolley - reduce available
            if self.available_for_sale >= quantity:
                self.available_for_sale -= quantity
                self.save_to_db()
                return True
            return False
        elif quantity < 0:
            # wjen removing from trolley - increase available
            self.available_for_sale += abs(quantity)
            self.save_to_db()
            return True
        else:
            return True

    # combine attribute update methods
    # take product fields that need to be updated and updates them  and save changes to the database
    # product.update_product(name="newname", price=10)
    def update_product(self, **kwargs) -> bool:
        """update product attributes with validation"""

        # validation
        for field, value in kwargs.items():
            if not hasattr(self, field):
                # checks updatre field
                raise ValueError(f"invalid field: {field}")

            if field == "price" and value < 0:
                # check updaate price
                raise ValueError("price cannot be negative")

            if (
                field in ["stock", "available_for_sale"] and value < 0
            ):  # available fdor sale cant be negartuve
                raise ValueError(f"{field} cannot be negative")

        # Update attributes
        for field, value in kwargs.items():
            setattr(self, field, value)

        return self.save_to_db()

    def is_in_stock(self) -> bool:
        """check if product is in stock and available for sale."""
        return self.stock > 0 and self.available_for_sale >= 1

    # combine add and reduce stock
    # product.adjust_stock(-10), product.adjust_stock(10)
    def adjust_stock(self, quantity: int) -> bool:
        """adjust sotck qty. positibe adds stock negative reduces stock"""
        if quantity < 0 and self.stock < abs(quantity):
            return False  # cant reduce when that much stock is not available

        self.stock += quantity
        return self.save_to_db()

    def __str__(self):
        """string rep of the product"""
        return f"Product(ID: {
            self.product_id}, Name: {
            self.name}, Price: ${
            self.price}, Stock: {
                self.stock})"
