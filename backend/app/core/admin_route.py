from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel, EmailStr, constr

from ..models.admin import AdminAccount
from ..models.account import Account
from ..core.database import Database, get_db
from ..utils.token import get_account_data
from ..utils.settings import SETTINGS

admin_route = APIRouter(prefix=SETTINGS.api_path + "/admin", tags=["admin"])

def get_admin_account(account_data: dict = Depends(get_account_data)) -> AdminAccount:
    account = AdminAccount(**account_data)
    if account.role_ID != 1:
        raise HTTPException(status_code=403, detail="Admin access required")
    return account

class AdminCreateAccountPayload(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    role_ID: int

class ChangeOthersPasswordPayload(BaseModel):
    new_password: constr(min_length=8)
    account_ID: int

class DeactivateAccountPayload(BaseModel):
    account_ID: int

class DeleteAccountPayload(BaseModel):
    account_ID: int

class DeleteOldAccountsPayload(BaseModel):
    role_ID: int = 4
    days_old: int = 30

@admin_route.post("/createAccount")
def create_account_route(payload: AdminCreateAccountPayload, db: Database = Depends(get_db), admin: AdminAccount = Depends(get_admin_account)):
    result = admin.create_account(db, payload.role_ID, payload.email, payload.password)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@admin_route.put("/changeOthersPassword")
def change_others_password_route(payload: ChangeOthersPasswordPayload, db: Database = Depends(get_db), admin: AdminAccount = Depends(get_admin_account)):
    success = admin.change_others_password(db, payload.new_password, payload.account_ID)
    if not success:
        raise HTTPException(status_code=500, detail="Password change failed")
    return {"message": "Password changed successfully"}

@admin_route.put("/deactivateAccount")
def deactivate_account_route(payload: DeactivateAccountPayload, db: Database = Depends(get_db), admin: AdminAccount = Depends(get_admin_account)):
    result = admin.deactivate_account(db, payload.account_ID)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@admin_route.delete("/deleteAccount")
def delete_account_route(payload: DeleteAccountPayload, db: Database = Depends(get_db), admin: AdminAccount = Depends(get_admin_account)):
    result = admin.delete_account(db, payload.account_ID)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@admin_route.get("/accounts")
def get_all_accounts_route(db: Database = Depends(get_db), admin: AdminAccount = Depends(get_admin_account)):
    return {"accounts": admin.get_all_accounts(db)}

@admin_route.delete("/deleteOldAccounts")
def delete_old_accounts_route(payload: DeleteOldAccountsPayload, db: Database = Depends(get_db), admin: AdminAccount = Depends(get_admin_account)):
    return admin.delete_old_accounts_by_role(db, payload.days_old, payload.role_ID)
