from fastapi import HTTPException, status as http_status 
from pydantic import BaseModel, Field

from ..core.database import ID, DictRow 
from .account import Account
from ..models.catalogue import Catalogue 
from ..models.product import Product, ProductCreate, ProductUpdate 

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="The name of the tag.")

class TagResponse(BaseModel):
    tagID: ID
    name: str

class ImageCreate(BaseModel):
    url: str = Field(..., description="The URL of the image.")

class ImageResponse(BaseModel):
    imageID: ID
    url: str
    productID: ID

class ProductTagResponse(BaseModel):
    productID: ID
    tagID: ID
    message: str

class ProductImageResponse(BaseModel):
    productID: ID
    imageID: ID
    url: str
    message: str


class EmployeeAccount(Account):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _any_tag_exists(self, tag_ids: list[dict]) -> bool:
        """
        Returns True if any tag in the given list exists in the database by tagID.
        """
        all_tags = self.db.get_all_tags()
        existing_tag_ids = {tag['tagID'] for tag in all_tags}

        return any(tag in existing_tag_ids for tag in tag_ids)

    def create_product_in_catalogue(self, product_data: ProductCreate, catalogue_service: Catalogue) -> Product:
        """
        Handles the business logic for creating a new product via the catalogue service.
        """
        try:
            created_product = catalogue_service.create_product(product_data)
            if not created_product:
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Product creation failed unexpectedly in catalogue service."
                )
            return created_product
        except ValueError as e:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during product creation.")

    def update_product_in_catalogue(self, product_id: ID, product_data: ProductUpdate, catalogue_service: Catalogue) -> Product:
        """
        Handles the business logic for updating an existing product via the catalogue service.
        """
        updated_product = catalogue_service.update_product(product_id, product_data)
        if not updated_product:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found for update.",
            )
        return updated_product

    def get_all_system_orders(self) -> list[DictRow]:
        """
        Retrieves all orders from the system.
        """
        orders = self.db.get_orders()
        if orders is None: 
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve orders.")
        return orders

    def create_new_tag(self, tag_name: str) -> TagResponse:
        """Creates a new tag in the system."""
        try:
            existing_tag_id = self.db.get_tag_id(tag_name)
            if existing_tag_id:
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail=f"Tag with name '{tag_name}' already exists with ID {existing_tag_id}."
                )
            tag_id = self.db.create_tag(tag_name)
            return TagResponse(tagID=tag_id, name=tag_name)
        except HTTPException:
            raise
        except Exception as e: 
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create tag: {str(e)}")

    def delete_system_tag(self, tag_id: ID) -> dict[str, str]:
        """Deletes a tag from the system by its ID."""
        try:
            affected_rows = self.db.delete_tag(tag_id)
            if affected_rows == 0:
                raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=f"Tag with ID {tag_id} not found.")
            return {"message": f"Tag with ID {tag_id} deleted successfully."}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete tag: {str(e)}")

    def assign_tag_to_product(self, product_id: ID, tag_id: ID) -> ProductTagResponse:
        """Assigns an existing tag to an existing product."""
        try:
            if not self.db.get_product(product_id):
                raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found.")

            if not self._any_tag_exists([tag_id]):
                raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=f"Tag with ID {tag_id} not found.")

            self.db.add_tag_to_product(product_id, tag_id)
            return ProductTagResponse(productID=product_id, tagID=tag_id, message="Tag added to product successfully.")
        except Exception as e:
            if "Duplicate entry" in str(e) or "already has tag" in str(e):
                 raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail=f"Product {product_id} already has tag {tag_id} or one of the IDs is invalid."
                )
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to add tag to product: {str(e)}")

    def remove_tag_from_a_product(self, product_id: ID, tag_id: ID) -> dict[str, str]:
        """Removes a tag association from a product."""
        try:
            self.db.remove_tag_from_product(product_id, tag_id)
            return {"message": f"Tag {tag_id} removed from product {product_id} successfully."}
        except ValueError as e:
             raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to remove tag from product: {str(e)}")

    def add_image_url_to_product(self, product_id: ID, image_url: str) -> ProductImageResponse:
        """Adds an image URL and associates it with a product."""
        try:
            if not self.db.get_product(product_id):
                raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found.")

            print(product_id, image_url)
            image_id = self.db.add_image_to_product(image_url, product_id)
            return ProductImageResponse(productID=product_id, imageID=image_id, url=image_url, message="Image added to product successfully.")
        except Exception as e:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to add image to product: {str(e)}")

    def delete_product_image(self, image_id: ID) -> dict[str, str]:
        """Deletes an image by its ID. This also unlinks it from any products due to cascade."""
        try:
            affected_rows = self.db.delete_image(image_id)
            if affected_rows == 0:
                raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=f"Image with ID {image_id} not found.")
            return {"message": f"Image with ID {image_id} deleted successfully."}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete image: {str(e)}")