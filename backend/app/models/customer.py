from pydantic import EmailStr
from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException, status as httpStatus

from .account import Account
from ..core.database import Database, Role, Status

class CustomerAccount(Account):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def register(cls, db: Database, email: EmailStr, password: str, role: Role, status: Status) -> dict:
        """Create a new account with hashed password."""
        existing: dict = db.get_account(email=email)
        if existing:
            raise HTTPException(
                status_code=httpStatus.HTTP_409_CONFLICT,
                detail="An account with that email already exists."
            )

        if len(password) < 8:
            raise HTTPException(
                status_code=httpStatus.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be at least 8 characters long."
            )

        if not any(char.isupper() for char in password):
            raise HTTPException(
                status_code=httpStatus.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must contain at least one uppercase letter."
            )

        hashed_password: str = cls._hash_password(password)
        email = email.strip().lower()
        creation_date: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        accountID: int = db.create_account(email, hashed_password, creation_date, role, status)
        if accountID is None:
            raise HTTPException(
                status_code=httpStatus.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unknown issue caused account creation to fail."
            )

        return {"account": cls(accountID, email, hashed_password, creation_date, role=role, status=status)}
    
    @classmethod
    def create_guest(cls, db: Database) -> dict:
        guest_email = f"guest_{uuid4().hex[:8]}@temp.domain"
        creation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        accountID: int = db.create_account(guest_email, "", creation_date, role=Role.GUEST, status=Status.ACTIVE)
        if accountID is None:
            raise HTTPException(
                status_code=httpStatus.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unknown issue caused guest account creation to fail."
            )

        return {"account": cls(accountID, guest_email, "", creation_date, role=Role.GUEST, status=Status.ACTIVE)}

    def get_trolly(self, db: Database):
        return db.get_trolley(self.accountID)

    def add_to_trolly(self, db: Database, product_id: int, amount: int):
        return db.add_to_trolley(self.accountID, product_id, amount)

    def remove_from_trolly(self, db: Database, product_id: int, amount: int):
        return db.remove_from_trolley(self.accountID, product_id, amount)

    def clear_trolly(self, db: Database):
        return db.clear_trolley(self.accountID)

    def create_order(self, db: Database, order_manager):
        trolly: list[tuple] = self.get_trolly(db)

        #logic when order manager is done
