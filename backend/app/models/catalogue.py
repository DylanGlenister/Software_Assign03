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

    def get_all_products(self) -> list[Product]:
        """Get all products from database."""
        products = self.db.get_products()

        if not products:
            raise ValueError('No products found in database')

        result: list[Product] = []

        for product in products:
            product_id = product.get('productID')

            if not product_id:
                raise ValueError('Unknown error reading productID')

            result.append(Product(product_id, self.db))

        return result

    def search_products(self, search_term: str, /) -> list[Product]:
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

    def search_products_by_criteria(self, *tags) -> list[Product]:
        """
        Search products using database-level search criteria.

        Args:
                tags: A list of tags used to filter the products.

        Returns:
                A list of products.
        """
        products = self.db.get_products(*tags)

        if not products:
            raise ValueError('No products found in database')

        result: list[Product] = []

        for product in products:
            product_id = product.get('productID')

            if not product_id:
                raise ValueError('Unknown error reading productID')

            result.append(Product(product_id, self.db))

        return result

    #Filtering and sorting

    def filter_by_availability(self, products: list[Product], /) -> list[Product]:
        """
        Filter products to show only those available for sale.
        """
        if products is None:
            products = self.get_all_products()

        return [product for product in products if product.available_for_sale >= 1]

    def sort_by_price(self, products: list[Product], low_to_high: bool = True, /) -> list[Product]:
        """
        Sort products by price.
        """
        if products is None:
            products = self.get_all_products()

        return sorted(products, key=lambda p: p.price, reverse=not low_to_high)
