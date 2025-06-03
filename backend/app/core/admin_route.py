from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from ..models.admin import AdminAccount
from ..core.database import Database, get_db, Role, Status
from ..utils.token import get_account_data
from ..utils.settings import SETTINGS

admin_route = APIRouter(prefix=SETTINGS.api_path + "/admin", tags=["admin"])

def get_admin_account(account_data: dict = Depends(get_account_data)) -> AdminAccount:
    account = AdminAccount(**account_data)
    if not account.verify_perms([Role.ADMIN]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You must be an admin to use these routes."
        )
    return account

class AdminCreateAccountPayload(BaseModel):
    email: EmailStr
    password: str
    role: Role

class ChangeOthersPasswordPayload(BaseModel):
    newPassword: str
    accountID: int

class DeactivateAccountPayload(BaseModel):
    accountID: int

class DeleteAccountPayload(BaseModel):
    accountID: int

class DeleteOldAccountsPayload(BaseModel):
    role: Optional[Role] = None
    status: Optional[Status] = None
    daysOld: Optional[int] = None

@admin_route.post("/createAccount")
def create_account_route(payload: AdminCreateAccountPayload, db: Database = Depends(get_db), admin: AdminAccount = Depends(get_admin_account)):
    try:
        admin.create_account(db, payload.role, payload.email, payload.password)
    except HTTPException:
        raise

    return {"message": "Account was created successfully"}

@admin_route.put("/changeOthersPassword")
def change_others_password_route(payload: ChangeOthersPasswordPayload, db: Database = Depends(get_db), admin: AdminAccount = Depends(get_admin_account)):
    try:
        admin.change_others_password(db, payload.newPassword, payload.accountID)
    except HTTPException:
        raise

    return {"message": "Password changed successfully"}

@admin_route.put("/deactivateAccount")
def deactivate_account_route(payload: DeactivateAccountPayload, db: Database = Depends(get_db), admin: AdminAccount = Depends(get_admin_account)):
    try:
        admin.deactivate_account(db, payload.accountID)
    except HTTPException:
        raise
 
    return {"message": f"Account {payload.accountID} was deactivated"}

@admin_route.delete("/deleteAccount")
def delete_account_route(payload: DeleteAccountPayload, db: Database = Depends(get_db), admin: AdminAccount = Depends(get_admin_account)):
    try:
        targetAccount = admin.get_account(db, payload.accountID)
        admin.delete_accounts(db, [targetAccount.get("accountID")])
    except HTTPException:
        raise

    return {"message": f"Account {payload.accountID} was deleted"}

@admin_route.get("/accounts")
def get_all_accounts_route(db: Database = Depends(get_db), admin: AdminAccount = Depends(get_admin_account)):
    try:
        accounts = admin.get_all_accounts(db)
    except HTTPException:
        raise

    return {"message": "Accounts were successfully retrieved", "accounts": accounts}

@admin_route.delete("/deleteAccounts")
def delete_old_accounts_route(payload: DeleteOldAccountsPayload, db: Database = Depends(get_db), admin: AdminAccount = Depends(get_admin_account)):
    try:
        accounts = admin.get_all_accounts(db, {
            "olderThan": payload.daysOld,
            "role": payload.role,
            "status": payload.status
        })
        
        if not accounts:
            return {"message": "No accounts found matching the criteria"}
        
        # Delete accounts
        ids: list = []
        for account in accounts:
            ids.append(account.get("accountID"))
        
        admin.delete_accounts(db, ids)
        
        return {
            "message": f"Successfully deleted {len(ids)} accounts",
            "deletedAccounts": accounts
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
