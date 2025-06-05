from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, ValidationError, constr

from ..models.account import Account
from ..utils.settings import SETTINGS
from ..utils.token import create_token, get_account_data
from .database import Database, Role, Status, get_db

account_route = APIRouter(prefix=SETTINGS.api_path + "/accounts", tags=["accounts"])

class LoginPayload(BaseModel):
	email: EmailStr = "customer@example.com"
	password: str = "password"

class UpdateAccountPayload(BaseModel):
	email: Optional[EmailStr]
	status: Optional[Status]
	firstname: Optional[str]
	lastname: Optional[str]

class ChangePasswordPayload(BaseModel):
	new_password: constr(min_length=8)  # type: ignore

def get_account(account_data: dict = Depends(get_account_data)) -> Account:
	return Account(**account_data)

@account_route.post("/login")
def login_route(payload: LoginPayload, db: Database = Depends(get_db)):
	account: Account | None = Account.login(db, payload.email, payload.password)

	if not account:
		return {"message": "Invalid credentials"}

	if account.status in ["inactive", "condemned"]:
		return {"message": "This account is inactive"}

	if account:
		token: str = create_token({"email": account.email, "role": account.role, "accountID": account.accountID, "status": account.status})
		return {
			"message": "Login successful",
			"email": account.email,
			"token":{
				"access_token": token,
				"token_type": "bearer"
				}
			}

@account_route.put("/update")
def update_account(payload: UpdateAccountPayload, account: Account = Depends(get_account), db: Database = Depends(get_db)):
	# TODO This never gets reached somehow
	print('Ping')
	if not account.verify_perms([Role.GUEST], True):  # Dont allow guests to update their account
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Guests cannot update their accounts. Please log in")
	result = account.update_info(db, **payload.model_dump(exclude_unset=True))
	if isinstance(result, dict) and result.get("error"):
		raise HTTPException(status_code=400, detail=result["error"])
	return {"message": "Account updated successfully"}

@account_route.put("/changePassword")
def change_password(payload: ChangePasswordPayload, account: Account = Depends(get_account), db: Database = Depends(get_db)):
	if account.verify_perms([Role.GUEST], True):  # Dont allow guests to update their account
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Guests cannot update their accounts. Please log in")

	try:
		result = account.change_password(db, payload.new_password)
	except ValueError as e:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

	if not result:
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to change password")

	return {"message": "Password changed successfully"}
