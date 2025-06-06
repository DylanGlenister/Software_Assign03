from fastapi import APIRouter, Depends, HTTPException, status, Body, Path
from fastapi.security import HTTPBearer
from typing import Annotated


from ..models.employee import (
    EmployeeAccount,
    TagCreate,
    TagResponse,
    ImageCreate,
    ProductTagResponse,
    ProductImageResponse,
)
from ..core.database import ID, Role
from ..utils.token import get_account_data
from ..utils.settings import SETTINGS
from ..models.catalogue import Catalogue
from .catalogue_route import get_catalogue_service
from ..models.product import Product, ProductCreate, ProductUpdate

employee_route = APIRouter(
    prefix=SETTINGS.api_path +
    "/employee",
    tags=["employee"])

bearer_scheme = HTTPBearer()


def get_employee_account(
    account_data: dict = Depends(get_account_data),
) -> EmployeeAccount:
    account = EmployeeAccount(**account_data)

    if not account.verify_perms([Role.EMPLOYEE, Role.ADMIN]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You must be an employee or higher to use these routes.",
        )
    return account


@employee_route.post(
    "/products/create",
    response_model=Product,
    status_code=status.HTTP_201_CREATED,
    summary="Create a New Product",
)
def create_product_route(
    catalogue_service: Annotated[Catalogue, Depends(get_catalogue_service)],
    product_to_create: Annotated[ProductCreate, Body(...)],
    account: EmployeeAccount = Depends(get_employee_account),
):
    """
    Creates a new product in the catalogue.
    Logic is handled by the EmployeeAccount.
    """
    return account.create_product_in_catalogue(
        product_to_create, catalogue_service)


@employee_route.patch(
    "/products/update/{product_id}",
    response_model=Product,
    summary="Update a Product",
)
def update_product_route(
    catalogue_service: Annotated[Catalogue, Depends(get_catalogue_service)],
    product_id: Annotated[ID, Path(description="The ID of the product to update.")],
    product_to_update: Annotated[ProductUpdate, Body(...)],
    account: EmployeeAccount = Depends(get_employee_account),
):
    """
    Updates an existing product's details.
    Logic is handled by the EmployeeAccount.
    """
    return account.update_product_in_catalogue(
        product_id, product_to_update, catalogue_service
    )


@employee_route.get("/orders", summary="Returns all the orders in the system")
def get_all_orders_route(
        account: EmployeeAccount = Depends(get_employee_account)):
    """
    Retrieves all orders. Logic is handled by EmployeeAccount.
    """
    return account.get_all_system_orders()


@employee_route.post(
    "/tags/create",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a New Tag",
)
def create_tag_route(
    tag_data: Annotated[TagCreate, Body(...)],
    account: EmployeeAccount = Depends(get_employee_account),
):
    """Creates a new tag in the system."""
    return account.create_new_tag(tag_data.name)


@employee_route.delete("/tags/delete/{tag_id}",
                       status_code=status.HTTP_200_OK,
                       summary="Delete a Tag")
def delete_tag_route(
    tag_id: Annotated[ID, Path(description="The ID of the tag to delete.")],
    account: EmployeeAccount = Depends(get_employee_account),
):
    """Deletes a tag from the system by its ID."""
    return account.delete_system_tag(tag_id)


@employee_route.post(
    "/products/{product_id}/tags/add/{tag_id}",
    response_model=ProductTagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Tag to Product",
)
def add_tag_to_product_route(
    product_id: Annotated[ID, Path(description="The ID of the product.")],
    tag_id: Annotated[ID, Path(description="The ID of the tag to add.")],
    account: EmployeeAccount = Depends(get_employee_account),
):
    """Assigns an existing tag to an existing product."""
    return account.assign_tag_to_product(product_id, tag_id)


@employee_route.delete(
    "/products/{product_id}/tags/remove/{tag_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Tag from Product",
)
def remove_tag_from_product_route(
    product_id: Annotated[ID, Path(description="The ID of the product.")],
    tag_id: Annotated[ID, Path(description="The ID of the tag to remove.")],
    account: EmployeeAccount = Depends(get_employee_account),
):
    """Removes a tag association from a product."""
    return account.remove_tag_from_a_product(product_id, tag_id)


@employee_route.post(
    "/products/{product_id}/images/add",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Image to Product",
)
def add_image_to_product_route(
    product_id: Annotated[ID, Path(description="The ID of the product.")],
    image_data: Annotated[ImageCreate, Body(...)],
    account: EmployeeAccount = Depends(get_employee_account),
):
    """Adds an image URL and associates it with a product."""
    return account.add_image_url_to_product(product_id, image_data.url)


@employee_route.delete("/images/{image_id}",
                       status_code=status.HTTP_200_OK,
                       summary="Delete an Image")
def delete_image_route(
    image_id: Annotated[ID, Path(description="The ID of the image to delete.")],
    account: EmployeeAccount = Depends(get_employee_account),
):
    """
    Deletes an image by its ID.
    This will also remove its associations with any products due to database cascade.
    """
    return account.delete_product_image(image_id)
