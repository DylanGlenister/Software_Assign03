from typing import List, Optional
from .product import Product

from ..core.database import Database


class Catalogue:
    """
    Simple catalogue class for displaying, searching, filtering and sorting products.
    """

    def __init__(self, db: Database):
        """Initialize catalogue with database connection."""
        self.db = db
        self._products = []

    def get_all_products(self) -> List[Product]:
        """Get all products from database."""
        product_ids = self.db.get_all_product_ids()
        return [Product(product_id, self.db) for product_id in product_ids]

    def search_products(self, search_term: str) -> List[Product]:
        """
        Search products by name, description, or tags.
        """
        all_products = self.get_all_products()
        if not search_term:
            return all_products

        search_term = search_term.lower()
        matching_products = []

        for product in all_products:
            # Check name
            if search_term in product.name.lower():
                matching_products.append(product)
                continue

            # Check description
            if search_term in product.description.lower():
                matching_products.append(product)
                continue

            # Check tags
            for tag in product.tags:
                if search_term in tag.lower():
                    matching_products.append(product)
                    break

        return matching_products

    def search_products_by_criteria(self, **search_criteria) -> List[Product]:
        """Search products using database-level search criteria."""
        product_ids = self.db.search_products(**search_criteria)
        return [Product(product_id, self.db) for product_id in product_ids]

    # Filtering and sorting

    def filter_by_availability(
            self,
            products: List[Product] = None) -> List[Product]:
        """
        Filter products to show only those available for sale.
        """
        if products is None:
            products = self.get_all_products()

        return [product for product in products if product.available_for_sale >= 1]

    def sort_by_price(
        self, products: List[Product] = None, low_to_high: bool = True
    ) -> List[Product]:
        """
        Sort products by price.
        """
        if products is None:
            products = self.get_all_products()

        return sorted(products, key=lambda p: p.price, reverse=not low_to_high)
