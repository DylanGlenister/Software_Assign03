from typing import Tuple
from pydantic import EmailStr
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from .account import Account
from ..core.database import Database, Role, Status

class AdminAccount(Account):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def change_others_password(self, db: Database, new_password: str, accountID: int) -> None:
        errors = self.verify_password(new_password)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=errors
            )

        hashed: str = self._hash_password(new_password)
        success: bool = db.update_account(accountID, password=hashed)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update password for account ID {accountID}"
            )

        self.password = hashed

    def create_account(self, db: Database, role: Role, email: EmailStr, password: str) -> None:
        existing: dict = db.get_account(_email=email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with that email already exists."
            )

        errors = self.verify_password(password)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=errors
            )

        hashed_password: str = self._hash_password(password)
        email = email.strip().lower()

        accountID: int = db.create_account(email, hashed_password, role)
        if accountID is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unknown error occurred while creating the account."
            )
    
    def get_account(self, db: Database, accountID: int) -> dict:
        account: dict = db.get_account(_accountId=accountID)
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found."
            )
        
        return account
    
    def deactivate_account(self, db: Database, accountID: int) -> None:
        self.get_account(db, accountID)

        success: bool = db.update_account(accountID, status=Status.INACTIVE.value)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to deactivate account ID {accountID}."
            )

    def delete_accounts(self, db: Database, accountIDs: list[int]) -> None:
        success: bool = db.delete_accounts(accountIDs)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete account ID {accountIDs}."
            )

    def get_all_accounts(self, db: Database, filters: dict = None) -> list[dict]:
        try:
            return db.get_accounts(**(filters or {}))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve accounts: {str(e)}"
            )

    def delete_old_accounts_by_role(self, db: Database, days: int, role: Role) -> str:
        try:
            cutoff_date: str = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            success: bool = db.delete_old_accounts_by_role(role=role, before_date=cutoff_date)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting old accounts: {str(e)}"
            )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unknown error occurred while deleting old accounts."
            )

        return f"Removed accounts older than {days} days"
