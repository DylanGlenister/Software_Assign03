from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from fastapi import status as httpStatus
from pydantic import EmailStr

from ..core.database import Database, Role, Status
from .account import Account


class CustomerAccount(Account):
	def __init__(self,
		accountID: int,
		creationDate: str,
		role: Role,
		status: Status,
		email: str | None,
		password: str | None,
		firstname: str | None,
		lastname: str | None,
	):
		super().__init__(
			accountID,
			creationDate,
			role,
			status,
			email,
			password,
			firstname,
			lastname
		)

	@classmethod
	def register(cls, db: Database, email: EmailStr, password: str, role: Role):
		"""Create a new account with hashed password."""
		existing: dict | None = db.get_account(_email=email)
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
		creation_date: datetime = datetime.now()

		accountID: int = db.create_account(role, email, hashed_password, _creationDate=creation_date)
		if accountID is None:
			raise HTTPException(
				status_code=httpStatus.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="An unknown issue caused account creation to fail."
			)

		account_details = db.get_account(_accountId=accountID)
		assert(account_details)

		return cls(**account_details)

	@classmethod
	def create_guest(cls, db: Database):
		guest_email = f"guest_{uuid4().hex[:8]}@temp.domain"

		accountID: int = db.create_account(Role.GUEST, guest_email, "")
		if accountID is None:
			raise HTTPException(
				status_code=httpStatus.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="An unknown issue caused guest account creation to fail."
			)

		account_details = db.get_account(_accountId=accountID)
		assert(account_details)

		return cls(**account_details)

	def get_trolley(self, db: Database):
		return db.get_trolley(self.accountID)

	def add_to_trolley(self, db: Database, product_id: int, amount: int):
		return db.add_to_trolley(self.accountID, product_id, amount)

	def remove_from_trolley(self, db: Database, product_id: int):
		return db.remove_from_trolley(self.accountID, product_id)

	def set_amount_in_trolley(self, db: Database, product_id: int, amount: int):
		return db.change_quantity_of_product_in_trolley(self.accountID, product_id, amount)

	def clear_trolly(self, db: Database):
		return db.clear_trolley(self.accountID)

	def create_order(self, db: Database, addressID: int, order_manager):
		orderID = db.create_order(self.accountID, addressID)

		#logic when order manager is done
