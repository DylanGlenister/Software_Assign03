from typing import Tuple
from pydantic import EmailStr
from datetime import datetime

from .account import Account
from ..core.database import Database

class CustomerAccount(Account):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def register(cls, db: Database, email: EmailStr, password: str, role_ID: int = 1, status_ID: int = 1) -> dict:
        """Create a new account with hashed password."""
        existing: Tuple = db.get_account_by_email(email)
        if existing:
            return {"error": "An account with that email already exists"}
        
        if len(password) < 8:
            return {"error": "Password must be at least 8 characters long."}
        
        if not any(char.isupper() for char in password):
            return {"error": "Password must contain at least one uppercase letter."}
        
        if not db.role_exists(role_ID):
            return {"error": "Invalid role ID."}

        if not db.status_exists(status_ID):
            return {"error": "Invalid status ID."}

        hashed_password: str = cls._hash_password(password)
        email = email.strip().lower()
        creation_date: datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        account_ID: int = db.create_account(email, hashed_password, creation_date, role_ID, status_ID)
        if account_ID is None:
            return {"error": "An unknown issue caused account creation to fail"}

        return {"account": cls(account_ID, email, hashed_password, creation_date, role_ID=role_ID, status_ID=status_ID)}

    def get_trolly(self, db: Database):
        return db.get_trolly(self.account_ID)

    def add_to_trolly(self, db: Database, product_id: int, amount: int):
        return db.add_to_trolly(self.account_ID, product_id, amount)

    def remove_from_trolly(self, db: Database, product_id: int, amount: int):
        return db.remove_from_trolly(self.account_ID, product_id, amount)

    def clear_trolly(self, db: Database):
        return db.clear_trolly(self.account_ID)
    
    def create_order(self, db: Database, order_manager):
        trolly: list[tuple] = self.get_trolly(db)

        #logic when order manager is done