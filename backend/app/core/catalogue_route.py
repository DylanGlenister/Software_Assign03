"""
Defines the API routes for managing the product catalogue.

This module creates a FastAPI router that exposes endpoints for creating,
reading, updating, and searching for products. It uses the stateless
Catalogue service for business logic and Pydantic models for data validation
and serialization.
"""

from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from ..core.database import ID, Database, get_db
from ..models.catalogue import Catalogue
from ..models.product import Product
from ..utils.settings import SETTINGS

# This router will contain all the API endpoints related to the catalogue.
catalogue_route = APIRouter(
    prefix=f"{SETTINGS.api_path}/catalogue",
    tags=["Catalogue"],
)


class SortOptions(str, Enum):
    """Defines available sorting options for catalogue endpoints."""

    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"


# This dependency provides a Catalogue service instance for each request,
# ensuring that every operation gets a fresh, isolated database session.
def get_catalogue_service(db: Annotated[Database, Depends(get_db)]) -> Catalogue:
    """
    FastAPI dependency to provide a Catalogue service instance.
    """
    return Catalogue(db)


# This helper function centralizes the common logic for filtering and sorting
# a list of products based on query parameters. This keeps the main route
# functions clean and adheres to the DRY (Don't Repeat Yourself) principle.
def _process_products(
    products: list[Product],
    available_only: bool,
    sort_by: SortOptions | None,
) -> list[Product]:
    """
    Applies filtering and sorting to a list of products.

    Args:
        products: The initial list of Product models.
        available_only: If True, filters for available products.
        sort_by: The sorting option to apply.

    Returns:
        The processed list of Product models.
    """
    if available_only:
        products = Catalogue.filter_by_availability(products)

    if sort_by is SortOptions.PRICE_ASC:
        products = Catalogue.sort_by_price(products, low_to_high=True)
    elif sort_by is SortOptions.PRICE_DESC:
        products = Catalogue.sort_by_price(products, low_to_high=False)

    return products


@catalogue_route.get(
    "/all",
    response_model=list[Product],
    summary="List All Products",
)
def list_all_products(
    catalogue: Annotated[Catalogue, Depends(get_catalogue_service)],
    available_only: Annotated[
        bool, Query(description="Filter for products with available stock.")
    ] = False,
    sort_by: Annotated[
        SortOptions | None, Query(description="Sort products by price.")
    ] = None,
):
    """
    Retrieves a list of all products.

    Allows for optional filtering by availability and sorting by price.
    """
    all_products = catalogue.get_all_products()
    return _process_products(all_products, available_only, sort_by)


@catalogue_route.get(
    "/search",
    response_model=list[Product],
    summary="Search for Products",
)
def search_products(
    catalogue: Annotated[Catalogue, Depends(get_catalogue_service)],
    query: Annotated[
        str, Query(description="Search term for product name, description, or tags.")
    ],
    available_only: Annotated[
        bool, Query(description="Filter for products with available stock.")
    ] = False,
    sort_by: Annotated[
        SortOptions | None, Query(description="Sort products by price.")
    ] = None,
):
    """
    Searches for products matching a query string.

    The search is performed across product names, descriptions, and tags.
    Results can be filtered by availability and sorted by price.
    """
    found_products = catalogue.search_products(query)
    return _process_products(found_products, available_only, sort_by)


@catalogue_route.get(
    "/tagged",
    response_model=list[Product],
    summary="Get Products by Tags",
)
def get_products_by_tags(
    catalogue: Annotated[Catalogue, Depends(get_catalogue_service)],
    tags: Annotated[
        list[str],
        Query(alias="t", description="One or more tags to filter products by."),
    ],
    available_only: Annotated[
        bool, Query(description="Filter for products with available stock.")
    ] = False,
    sort_by: Annotated[
        SortOptions | None, Query(description="Sort products by price.")
    ] = None,
):
    """
    Retrieves products that are associated with all of the specified tags.

    At least one tag must be provided. Results can be filtered by
    availability and sorted by price.
    """
    if not tags:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one tag must be provided via the 't' query parameter.",
        )
    tagged_products = catalogue.get_products_by_tag(*tags)
    return _process_products(tagged_products, available_only, sort_by)


@catalogue_route.get(
    "/{product_id}",
    response_model=Product,
    summary="Get a Specific Product",
)
def get_product(
    catalogue: Annotated[Catalogue, Depends(get_catalogue_service)],
    product_id: Annotated[ID, Path(description="The ID of the product to retrieve.")],
):
    """
    Retrieves a single product by its unique ID.
    """
    product = catalogue.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found.",
        )
    return product
