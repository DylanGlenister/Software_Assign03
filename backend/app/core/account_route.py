from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Optional
from pydantic import BaseModel, EmailStr, constr
from datetime import datetime, timezone

from ..models.account import Account
from ..models.customer import CustomerAccount
from .database import Database, get_db
from ..utils.settings import SETTINGS
from ..utils.token import create_access_token, decode_access_token, get_current_account, get_token_from_header

account_route = APIRouter(prefix=SETTINGS.api_path + "/accounts", tags=["accounts"])

class LoginPayload(BaseModel):
	email: EmailStr = "customer@example.com"
	password: str = "password"

@account_route.post("/login")
def login_route(payload: LoginPayload, db: Database = Depends(get_db)):
	account: Account = Account.login(db, payload.email, payload.password)

	if not account:
		return {"message": "Invalid credentials"}
	
	if account.status_ID != 1:
		return {"message": "This account is inactive"}

	if account:
		token: str = create_access_token({"email": account.email, "role_ID": account.role_ID, "account_ID": account.account_ID})
		return {
			"message": "Login successful", 
			"email": account.email,
			"token":{
				"access_token": token, 
				"token_type": "bearer"
				}
			}

@account_route.post("/tokenInfo")
def token_info(token: str = Depends(get_token_from_header)):
    token_data: dict = decode_access_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    exp_timestamp: float = token_data.get("exp")
    if not exp_timestamp:
        raise HTTPException(status_code=400, detail="Token does not contain expiration")

    expire_time: datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    now: datetime = datetime.now(timezone.utc)
    time_remaining: datetime = expire_time - now

    return {
        "expires_at": expire_time.isoformat(),
        "time_remaining": str(time_remaining),
		"data": token_data
    }

class UpdateAccountPayload(BaseModel):
    email: Optional[EmailStr]
    status_ID: Optional[int] = 1

@account_route.put("/update")
def update_account(payload: UpdateAccountPayload, account: Account = Depends(get_current_account), db: Database = Depends(get_db)):
    result = account.update_info(db, **payload.model_dump(exclude_unset=True))
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": "Account updated successfully"}

class ChangePasswordPayload(BaseModel):
    new_password: constr(min_length=8)

@account_route.put("/change-password")
def change_password(payload: ChangePasswordPayload, account: Account = Depends(get_current_account), db: Database = Depends(get_db)):
    result = account.change_password(db, payload.new_password)
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    if not result:
        raise HTTPException(status_code=500, detail="Failed to change password")
    return {"message": "Password changed successfully"}