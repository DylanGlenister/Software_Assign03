from typing import Tuple
from pydantic import EmailStr
from datetime import datetime, timedelta

from .account import Account
from ..core.database import Database

class AdminAccount(Account):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def change_others_password(self, db: Database, new_password: str, account_ID: int):
        hashed: str = self._hash_password(new_password)
        success: bool = db.update_account(account_ID, password=hashed)
        if success:
            self.password = hashed
        return success

    def create_account(self, db: Database, role_ID: int, email: EmailStr, password: str):
        existing: Tuple = db.get_account(email=email)
        if existing:
            return {"error": "An account with that email already exists"}

        if len(password) < 8:
            return {"error": "Password must be at least 8 characters long."}

        if not any(char.isupper() for char in password):
            return {"error": "Password must contain at least one uppercase letter."}

        if not db.role_exists(role_ID):
            return {"error": "Invalid role ID."}

        hashed_password: str = self._hash_password(password)
        email = email.strip().lower()
        creation_date: datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        account_ID: int = db.create_account(email, hashed_password, creation_date, role_ID, 1)
        if account_ID is None:
            return {"error": "An unknown issue caused account creation to fail"}

        return {"success": "Account created successfully"}

    def deactivate_account(self, db: Database, account_ID: int):
        if not db.get_account(account_id=account_ID):
            return {"error": "Account not found."}
        
        success: bool = db.update_account(account_ID, statusID=2)
        if not success:
            return {"error": f"An unknown error has caused the deactivating of account {account_ID} to fail."}
        
        return {"success": success}

    def delete_account(self, db: Database, account_ID: int):
        if not db.get_account(account_id=account_ID):
            return {"error": "Account not found."}
        
        success: bool = db.delete_account(account_ID)
        if not success:
            return {"error": f"An unknown error has caused the deleting of account {account_ID} to fail."}

        return {"success": success}

    def get_all_accounts(self, db: Database, filters: dict = None) -> list[Tuple]:
        return db.get_all_accounts()
    
    def delete_old_accounts_by_role(self, db: Database, days: int, role_ID: int):
        older_than: timedelta = timedelta(days=days)

        cutoff_date: datetime = (datetime.now() - older_than).strftime("%Y-%m-%d %H:%M:%S")
        success: bool = db.delete_old_accounts_by_role(role_ID=role_ID, before_date=cutoff_date)
        
        if not success:
            return {"error": "An unknown error has caused removing old accounts to fail."}
            
        return {"success": f"Removed accounts that were older than {days} days"}
