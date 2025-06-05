from ..core.database import Database
from .product import Product


class Catalogue:
    """
    Simple catalogue class for displaying, searching, filtering and sorting products.
    """

    def __init__(self, db: Database):
        """Initialize catalogue with database connection."""
        self.db = db
        self._products: list[Product] = []

    def get_all_products(self) -> None:
        """
        Get all products from the database and update the internal list.

        Raises:
            ValueError: If no products are found or if a product ID is missing.
        """
        products_data = self.db.get_products()

        if not products_data:
            raise ValueError('No products found in database')

        self._products = []
        for product_item in products_data:
            product_id = product_item.get('productID')

            if not product_id:
                raise ValueError('Unknown error reading productID')

            self._products.append(Product(product_id, self.db))

    def search_products(self, search_term: str, /) -> list[Product]:
        """
        Search products by name, description, or tags.

        Args:
            search_term: The term to search for. Case-insensitive.

        Returns:
            A list of products matching the search term. If search_term
            is empty, returns all products currently in the catalogue.
        """
        if not search_term:
            return self._products

        search_term_lower = search_term.lower()
        matching_products: list[Product] = []

        for product in self._products:
            if search_term_lower in product.name.lower():
                matching_products.append(product)
                continue

            if search_term_lower in product.description.lower():
                matching_products.append(product)
                continue

            for tag in product.tags:
                if search_term_lower in tag.lower():
                    matching_products.append(product)
                    break  # Found a match in tags, move to next product

        return matching_products

    def get_products_by_tag(self, *tags) -> None:
        """
        Fetch products by tags and update the internal product list.

        This method uses a database-level search to find products matching
        the provided tags and then refreshes `self._products` with these findings.

        Args:
            *tags: One or more tags to filter products by.

        Raises:
            ValueError: If no products are found for the given tags or
                        if a product ID is missing.
        """
        products_data = self.db.get_products(*tags)

        if not products_data:
            raise ValueError(
                'No products found in database for the given tags')

        self._products = []
        for product_item in products_data:
            product_id = product_item.get('productID')

            if not product_id:
                raise ValueError('Unknown error reading productID')

            self._products.append(Product(product_id, self.db))

    # Filtering and sorting

    def filter_by_availability(self, products: list[Product], /) -> None:
        """
        Filter a given list of products for availability.

        The filtered list, containing only products with available stock
        (available_for_sale >= 1), updates the internal `self._products` list.

        Args:
            products: The list of products to filter.
        """
        self._products = [
            product for product in products
            if product.available_for_sale >= 1
        ]

    def sort_by_price(
        self, products: list[Product], low_to_high: bool = True, /
    ) -> None:
        """
        Sort a given list of products by price.

        The sorted list updates the internal `self._products` list.

        Args:
            products: The list of products to sort.
            low_to_high: If True, sort from low to high price;
                         otherwise, sort from high to low.
        """
        self._products = sorted(
            products,
            key=lambda p: p.price,
            reverse=not low_to_high
        )
