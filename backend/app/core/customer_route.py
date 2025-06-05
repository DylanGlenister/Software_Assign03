from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from ..models.customer import CustomerAccount
from ..core.database import Database, get_db, Role
from ..utils.token import get_token, get_account_data, create_token
from ..utils.settings import SETTINGS

customer_route = APIRouter(
    prefix=SETTINGS.api_path +
    "/customer",
    tags=["customer"])


def get_customer_account(token: Optional[str] = Depends(get_token),
                         db: Database = Depends(get_db)) -> dict[str, CustomerAccount | str | None]:
    if token:
        account_data: dict = get_account_data(token, db)
        # NOTE Dom is this correct? I feel like this should return the token right?
        # NOTE Yea, i know what im doing :)
        return {"account": CustomerAccount(db=db, **account_data), "token": None}

    # Create guest account
    guest_account: CustomerAccount = CustomerAccount.create_guest(db)
    token_data: dict = {
        "accountID": guest_account.accountID,
        "email": guest_account.email,
        "role": guest_account.role,
        "status": guest_account.status
    }
    token = create_token(token_data, 60)
    return {"account": guest_account, "token": token}


class RegisterPayload(BaseModel):
    email: EmailStr = "customer@example.com"
    password: str = "password"


class TrollyItem(BaseModel):
    product_id: int
    amount: int = 1

class AddressID(BaseModel):
    address_id: int

class Address(BaseModel):
    address: str

@customer_route.post("/register")
def register_route(
    payload: RegisterPayload,
    db: Database = Depends(get_db)
):

    account: CustomerAccount = CustomerAccount.register(
        db,
        payload.email,
        payload.password,
        Role.CUSTOMER
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed due to an unknown error.")

    return {
        "message": "Registration successful",
        "email": account.email
    }


@customer_route.get("/trolley")
def get_trolley_route(
    customer_data: dict[str, CustomerAccount | str | None] = Depends(get_customer_account)
):
    customer: CustomerAccount | str | None = customer_data.get("account")

    if not isinstance(customer, CustomerAccount):
        raise ValueError('Unknown error retrieving customer data')

    result: dict = {"token": customer_data.get("token")}

    result["trolley"] = customer.trolley.lineItems
    return result


@customer_route.post("/trolley/add")
def add_to_trolley_route(
    item: TrollyItem, db: Database = Depends(get_db),
    customer_data: dict = Depends(get_customer_account)
):

    customer: CustomerAccount | str | None = customer_data.get("account")

    if not isinstance(customer, CustomerAccount):
        raise ValueError('Unknown error retrieving customer data')

    result: dict = {"token": customer_data.get("token")}

    success: bool = bool(
        customer.trolley.add_line_item(item.product_id, item.amount))
    if success:
        result["message"] = "Item has been added to the trolley"
    else:
        result["error"] = "Failed to add item to the trolley"
    return result


@customer_route.post("/trolley/modify")
def modify_number_in_trolley(
        item: TrollyItem,
        db: Database = Depends(get_db),
        customer_data: dict = Depends(get_customer_account)):
    customer: CustomerAccount | str | None = customer_data.get("account")

    if not isinstance(customer, CustomerAccount):
        raise ValueError('Unknown error retrieving customer data')

    result: dict = {"token": customer_data.get("token")}

    success: bool = bool(
        customer.trolley.update_quantity(item.product_id, item.amount))
    if success:
        result["message"] = "Item quantity has been modified in the trolley"
    else:
        result["error"] = "Failed to modify item quantity from the trolley"
    return result


@customer_route.post("/trolley/remove")
def remove_from_trolley_route(
        item: TrollyItem,
        db: Database = Depends(get_db),
        customer_data: dict = Depends(get_customer_account)):
    customer: CustomerAccount | str | None = customer_data.get("account")

    if not isinstance(customer, CustomerAccount):
        raise ValueError('Unknown error retrieving customer data')

    result: dict = {"token": customer_data.get("token")}

    success: bool = bool(
        customer.trolley.remove_from_trolley(item.product_id))
    if success:
        result["message"] = "Item has been removed from the trolley"
    else:
        result["error"] = "Failed to remove item from the trolley"
    return result


@customer_route.post("/trolley/clear")
def clear_trolley_route(db: Database = Depends(get_db),
                        customer_data: dict = Depends(get_customer_account)):
    customer: CustomerAccount | None = customer_data.get("account")

    if not isinstance(customer, CustomerAccount):
        raise ValueError('Unknown error retrieving customer data')

    result: dict = {"token": customer_data.get("token")}

    success: bool = bool(customer.trolley.clear_trolley())
    if success:
        result["message"] = "Trolley has been cleared"
    else:
        result["error"] = "Failed to clear trolley"
    return result


@customer_route.get("/orders")
def customer_get_orders(db: Database = Depends(get_db),
                        customer_data: dict = Depends(get_customer_account)):
    customer: CustomerAccount | None = customer_data.get("account")

    if not isinstance(customer, CustomerAccount):
        raise ValueError('Unknown error retrieving customer data')
    
    result: dict = {"token": customer_data.get("token")}
    result["orders"] = db.get_orders_from_account(customer.accountID) # an array of orders

    return result

@customer_route.post("/order/create")
def customer_create_order(payload: AddressID, customer_data: dict = Depends(get_customer_account)):
    customer: CustomerAccount | None = customer_data.get("account")

    if not isinstance(customer, CustomerAccount):
        raise ValueError('Unknown error retrieving customer data')
    
    result: dict = {"token": customer_data.get("token")}
    
    result["order_id"] = customer.create_order(payload.address_id)
    return result


@customer_route.get("/address")
def customer_get_address(customer_data: dict = Depends(get_customer_account)):
    customer: CustomerAccount | None = customer_data.get("account")

    if not isinstance(customer, CustomerAccount):
        raise ValueError('Unknown error retrieving customer data')
    
    result: dict = {"token": customer_data.get("token")}
    result["addresses"] = customer.get_addresses() #array of addresses
    return result


@customer_route.get("/address/add")
def customer_add_address(payload: Address,
                         customer_data: dict = Depends(get_customer_account)):
    customer: CustomerAccount | None = customer_data.get("account")

    if not isinstance(customer, CustomerAccount):
        raise ValueError('Unknown error retrieving customer data')
    
    result: dict = {"token": customer_data.get("token")}
    
    if customer.add_address(payload.address):
        return result
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Adding an address failed due to an unknown error.")


@customer_route.get("/address/remove")
def customer_remove_address(payload: AddressID, customer_data: dict = Depends(get_customer_account)):
    customer: CustomerAccount | None = customer_data.get("account")

    if not isinstance(customer, CustomerAccount):
        raise ValueError('Unknown error retrieving customer data')
    
    result: dict = {"token": customer_data.get("token")}
    if customer.remove_address(payload.address_id):
        return result
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Removing an address failed due to an unknown error.")
