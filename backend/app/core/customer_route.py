from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import EmailStr
from pydantic import BaseModel

from ..models.customer import CustomerAccount
from ..core.database import Database, get_db
from ..utils.token import get_customer_from_token
from ..utils.settings import SETTINGS

customer_route = APIRouter(prefix=SETTINGS.api_path + "/customer", tags=["customer"])

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

@customer_route.get("/trolly")
def get_trolly_route(db: Database = Depends(get_db), customer: CustomerAccount = Depends(get_customer_from_token)):
    return customer.get_trolly(db)

@customer_route.post("/trolly/add")
def add_to_trolly_route(
    item: TrollyItem,
    db: Database = Depends(get_db),
    customer: CustomerAccount = Depends(get_customer_from_token)
):
    result: bool = customer.add_to_trolly(db, item.product_id, item.amount)
    if result:
        return {"message": "Item has been added to the trolly"}
    return {"error": "Failed to add item to trolly"}

@customer_route.post("/trolly/remove")
def remove_from_trolly_route(
    item: TrollyItem,
    db: Database = Depends(get_db),
    customer: CustomerAccount = Depends(get_customer_from_token)
):
    return customer.remove_from_trolly(db, item.product_id, item.amount)

@customer_route.post("/trolly/clear")
def clear_trolly_route(
    db: Database = Depends(get_db),
    customer: CustomerAccount = Depends(get_customer_from_token)
):
    return customer.clear_trolly(db)
