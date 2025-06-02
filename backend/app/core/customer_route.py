from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from ..models.customer import CustomerAccount
from ..core.database import Database, get_db
from ..utils.token import get_token, get_account_data, create_token
from ..utils.settings import SETTINGS

customer_route = APIRouter(prefix=SETTINGS.api_path + "/customer", tags=["customer"])

def get_customer_account(token: Optional[str] = Depends(get_token), db: Database = Depends(get_db)) -> dict:
    if token:
        account_data: dict = get_account_data(token, db)
        return {"account": CustomerAccount(**account_data), "token": None}

    #Create guest account
    guest_account: CustomerAccount = CustomerAccount.create_guest(db).get("account")
    token_data: dict = {
        "account_ID": guest_account.account_ID,
        "email": guest_account.email,
        "role_ID": guest_account.role_ID,
        "status_ID": guest_account.status_ID
    }
    token = create_token(token_data, 60)
    return {"account": guest_account, "token": token}  

class RegisterPayload(BaseModel):
	email: EmailStr = "customer@example.com"
	password: str = "password"

@customer_route.post("/register")
def register_route(payload: RegisterPayload, db: Database = Depends(get_db)):
	account: dict = CustomerAccount.register(db, payload.email, payload.password)
	if not account:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration failed due to an unknown error.")
	
	error: str = account.get("error")
	if error:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
	
	account: CustomerAccount =  account.get("account")

	return {
		"message": "Registration successful",
		"email": account.email
	}

class TrollyItem(BaseModel):
    product_id: int
    amount: int = 1

@customer_route.get("/trolley")
def get_trolly_route(db: Database = Depends(get_db), customer_data: dict = Depends(get_customer_account)):
    customer: CustomerAccount = customer_data.get("account")
    result: dict = {"token": customer_data.get("token")}
    
    result["trolley"] = customer.get_trolly(db)
    return result


@customer_route.post("/trolley/add")
def add_to_trolly_route(item: TrollyItem, db: Database = Depends(get_db), customer_data: dict = Depends(get_customer_account)):
    customer: CustomerAccount = customer_data.get("account")
    result: dict = {"token": customer_data.get("token")}

    success: bool = customer.add_to_trolly(db, item.product_id, item.amount)
    if success:
        result["message"] = "Item has been added to the trolley"
    else:
        result["error"] = "Failed to add item to the trolley"
    return result

@customer_route.post("/trolley/remove")
def remove_from_trolly_route(item: TrollyItem, db: Database = Depends(get_db), customer_data: dict = Depends(get_customer_account)):
    customer: CustomerAccount = customer_data.get("account")
    result: dict = {"token": customer_data.get("token")}
    
    success: bool = customer.remove_from_trolly(db, item.product_id, item.amount)
    if success:
        result["message"] = "Item has been removed from the trolley"
    else:
        result["error"] = "Failed to remove item from the trolley"
    return result

@customer_route.post("/trolley/clear")
def clear_trolly_route(db: Database = Depends(get_db), customer_data: dict = Depends(get_customer_account)):
    customer: CustomerAccount = customer_data.get("account")
    result: dict = {"token": customer_data.get("token")}
    
    success: bool = customer.clear_trolly(db)
    if success:
        result["message"] = "Trolley has been cleared"
    else:
        result["error"] = "Failed to clear trolley"
    return result