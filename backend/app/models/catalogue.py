"""
Defines the stateless Catalogue service for product-related operations.

This module provides a service layer that abstracts the database interactions
for products. It is responsible for fetching, creating, updating, and deleting
product data, and converting that data into the Pydantic models defined in
the `product` module.
"""

from ..core.database import ID, Database, DictRow
from .product import Product, ProductCreate, ProductUpdate


class Catalogue:
    """
    A stateless service for querying and managing product information.

    This class orchestrates database operations and ensures that data is
    transformed into the appropriate Pydantic models for use in the API.
    It does not hold any state itself; each method call performs a discrete
    set of database operations.
    """

    def __init__(self, db: Database):
        """
        Initializes the catalogue service with a database connection.

        Args:
            db: An active database session dependency.
        """
        self.db = db

    # This helper method centralizes the logic for constructing a complete
    # Product model. It fetches the core data, then enriches it with related
    # data like tags and images, which are stored in separate tables.
    def _build_product_from_data(self, product_data: DictRow) -> Product:
        """
        Constructs a full Product model from a database row.

        This helper fetches related data (tags, images) for a given product
        and combines it with the core product data to create a complete
        Product Pydantic model.

        Args:
            product_data: A dictionary representing a row from the Product table.

        Returns:
            A fully populated Product Pydantic model.

        Raises:
            ValueError: If the product_data dictionary is missing the 'productID'.
        """
        product_id = product_data.get("productID")
        if not product_id:
            raise ValueError("Product data is missing 'productID'.")

        images = self.db.get_product_images(product_id) or []
        tags_data = self.db.get_tags_for_product(product_id) or []
        tags = [tag["name"] for tag in tags_data]

        # Combine all data and validate against the Pydantic model.
        full_product_data = {
            **product_data,
            "tags": tags,
            "images": images,
        }
        return Product.model_validate(full_product_data)

    def get_product_by_id(self, product_id: ID) -> Product | None:
        """
        Retrieves a single product by its ID.

        Args:
            product_id: The unique identifier of the product.

        Returns:
            A Product model instance if found, otherwise None.
        """
        product_data = self.db.get_product(product_id)
        if not product_data:
            return None
        return self._build_product_from_data(product_data)

    def get_all_products(self) -> list[Product]:
        """
        Retrieves all products from the database.

        Returns:
            A list of Product model instances.
        """
        products_data = self.db.get_all_products()
        if not products_data:
            return []
        return [self._build_product_from_data(item) for item in products_data]

    def get_products_by_tag(self, *tags: str) -> list[Product]:
        """
        Fetches products that are associated with all of the given tags.

        Args:
            *tags: One or more tag names to filter by.

        Returns:
            A list of matching Product model instances.
        """
        products_data = self.db.get_products_by_tags(list(tags))
        if not products_data:
            return []
        return [self._build_product_from_data(item) for item in products_data]

    def search_products(self, search_term: str) -> list[Product]:
        """
        Searches products by name, description, or tags in Python.

        Note:
            This implementation fetches all products and then filters them in
            application memory. For large datasets, this approach is inefficient
            and should be replaced with a database-level full-text search.

        Args:
            search_term: The term to search for (case-insensitive).

        Returns:
            A list of products matching the search term.
        """
        all_products = self.get_all_products()
        if not search_term:
            return all_products

        search_term_lower = search_term.lower()
        matching_products: list[Product] = []

        for product in all_products:
            if (
                search_term_lower in product.name.lower()
                or search_term_lower in product.description.lower()
                or any(search_term_lower in tag.lower() for tag in product.tags)
            ):
                matching_products.append(product)

        return matching_products

    def create_product(self, product_create: ProductCreate) -> Product:
        """
        Creates a new product in the database.

        Args:
            product_create: A Pydantic model with the data for the new product.

        Returns:
            The newly created Product model instance, including its database ID.

        Raises:
            ValueError: If the product creation fails in the database.
        """
        product_id = self.db.add_product(
            product_create.name,
            product_create.description,
            product_create.price,
            stock=product_create.stock,
            available=product_create.available_for_sale,
        )
        if not product_id:
            raise ValueError("Failed to create product in the database.")

        new_product = self.get_product_by_id(product_id)
        if not new_product:
            raise ValueError(
                f"Failed to retrieve newly created product with ID: {product_id}")

        return new_product

    def update_product(
        self, product_id: ID, product_update: ProductUpdate
    ) -> Product | None:
        """
        Updates an existing product with new data.

        Only the fields provided in the `product_update` model are changed.

        Args:
            product_id: The ID of the product to update.
            product_update: A Pydantic model containing the fields to update.

        Returns:
            The updated Product model instance, or None if the product was not found.
        """
        update_data = product_update.model_dump(
            exclude_unset=True, by_alias=True)

        if not update_data:
            return self.get_product_by_id(product_id)

        rows_affected = self.db.update_product(product_id, **update_data)

        if rows_affected == 0 and self.db.get_product(product_id) is None:
            return None

        return self.get_product_by_id(product_id)

    @staticmethod
    def filter_by_availability(products: list[Product]) -> list[Product]:
        """
        Filters a list of products, returning only those available for sale.

        Args:
            products: The list of Product models to filter.

        Returns:
            A new list containing only available products.
        """
        return [p for p in products if p.available_for_sale >= 1]

    @staticmethod
    def sort_by_price(
        products: list[Product], low_to_high: bool = True
    ) -> list[Product]:
        """
        Sorts a list of products by their price.

        Args:
            products: The list of Product models to sort.
            low_to_high: The direction for sorting. True for ascending.

        Returns:
            A new list of sorted products.
        """
        return sorted(products, key=lambda p: p.price, reverse=not low_to_high)
