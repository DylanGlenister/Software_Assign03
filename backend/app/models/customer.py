from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from fastapi import status as httpStatus
from pydantic import EmailStr

from ..core.database import Database, Role, Status
from .account import Account
from .trolley import Trolley
from .order import OrderManager


class CustomerAccount(Account):
    def __init__(
        self,
        accountID: int,
        creationDate: str,
        role: Role,
        status: Status,
        email: EmailStr | None,
        password: str | None,
        firstname: str | None,
        lastname: str | None,
        db: Database,
    ):
        self.trolley: Trolley = Trolley(db, accountID)

        super().__init__(
            accountID,
            creationDate,
            role,
            status,
            email,
            password,
            firstname,
            lastname,
            db,
        )

    @classmethod
    def register(
            cls,
            db: Database,
            email: EmailStr,
            password: str,
            role: Role):
        """Create a new account with hashed password."""
        existing: dict | None = db.get_account(_email=email)
        if existing:
            raise HTTPException(
                status_code=httpStatus.HTTP_409_CONFLICT,
                detail="An account with that email already exists.",
            )

        if len(password) < 8:
            raise HTTPException(
                status_code=httpStatus.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be at least 8 characters long.",
            )

        if not any(char.isupper() for char in password):
            raise HTTPException(
                status_code=httpStatus.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must contain at least one uppercase letter.",
            )

        hashed_password: str = cls._hash_password(password)
        email = email.strip().lower()
        creation_date: datetime = datetime.now()

        accountID: int = db.create_account(
            role, email, hashed_password, _creationDate=creation_date
        )
        if accountID is None:
            raise HTTPException(
                status_code=httpStatus.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unknown issue caused account creation to fail.",
            )

        account_details = db.get_account(accountId=accountID)
        assert account_details

        return cls(db=db, **account_details)

    @classmethod
    def create_guest(cls, db: Database):
        guest_email = f"guest_{uuid4().hex[:8]}@temp.domain"

        accountID: int = db.create_account(Role.GUEST, guest_email, "")
        if accountID is None:
            raise HTTPException(
                status_code=httpStatus.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unknown issue caused guest account creation to fail.",
            )

        account_details = db.get_account(accountId=accountID)
        assert account_details

        return cls(db=db, **account_details)

    def create_order(self, address_id: int) -> int:
        order_manager = OrderManager(self.accountID, address_id, self.db)
        return order_manager.create_order()

    def add_address(self, address: str):
        return self.db.create_address(self.accountID, address.strip())

    def get_addresses(self):
        return self.db.get_addresses(self.accountID)

    def remove_address(self, address_id: int):
        addresses = self.get_addresses() or []

        has_address = False
        for address in addresses:
            if address.get("addressID") == address_id:
                has_address = True
                break

        if not has_address:
            raise HTTPException(
                status_code=httpStatus.HTTP_404_NOT_FOUND,
                detail="Address not found or you do not have permission to delete this address.",
            )

        return self.db.delete_address(address_id)
