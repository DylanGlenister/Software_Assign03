from typing import Optional, Type, Tuple
from pydantic import EmailStr, ValidationError
from bcrypt import checkpw, gensalt, hashpw
from datetime import datetime

from ..core.database import Database

class Account:
	def __init__(self, account_ID, email, password, creation_date, role_ID, status_ID):
		self.account_ID = account_ID
		self.email = email
		self.password = password
		self.creation_date = creation_date
		self.role_ID = role_ID
		self.status_ID = status_ID

	@classmethod
	def _hash_password(cls, password: str) -> str:
		"""Hash a plain-text password using bcrypt."""
		salt: bytes = gensalt()
		return hashpw(password.encode('utf-8'), salt).decode('utf-8')

	@classmethod
	def login(cls: Type["Account"], db: Database, email: str, password: str) -> Optional["Account"]:
		"""Attempt to find an account with matching email and password."""
		row: Tuple = db.get_account_by_email(email)
		if not row:
			print("No account found with that email.")
			return None

		account_ID, db_email, db_password, creation_date, role_ID, status_ID = row

		if checkpw(password.encode('utf-8'), db_password.encode('utf-8')):
			return cls(account_ID, db_email, db_password, creation_date, role_ID, status_ID)
		else:
			print("Password incorrect.")
			return None
	
	def verify_perms(self, db: Database, required_roles: list[int]) -> bool:
		role: dict = db.get_role(self.role_ID)
		return role.roleID in required_roles
	
	def update_info(self, db: Database, **fields) -> bool:
		valid_fields: dict = {"email", "status_ID"}

		filtered_fields: dict = {}
		for key, value in fields.items():
			if key in valid_fields:
				filtered_fields[key] = value
			else:
				print(f"Ignored invalid field: {key}")

		if "email" in filtered_fields:
			try:
				filtered_fields["email"] = str(filtered_fields["email"].strip().lower())
			except ValidationError:
				return {"error": "Invalid email format."}

		if "status_ID" in filtered_fields and not db.status_exists(filtered_fields["status_ID"]):
			return {"error": "Invalid status ID."}


		if not filtered_fields:
			return {"error": "No valid fields to update."}

		translation_map = {
			"status_ID": "statusID",
			"email": "email",
		}

		filtered_fields_db = {translation_map[k]: v for k, v in filtered_fields.items()}
		success: bool = db.update_account(self.account_ID, **filtered_fields_db)

		if success:
			for key, value in filtered_fields.items():
				setattr(self, key, value)
		return {"success": success}
	
	def change_password(self, db: Database, new_password: str) -> bool:
		if len(new_password) < 8:
			return {"error": "Password must be at least 8 characters long."}
		
		if not any(char.isupper() for char in new_password):
			return {"error": "Password must contain at least one uppercase letter."}

		hashed: str = self._hash_password(new_password)
		success: bool = db.update_account(self.account_ID, password=hashed)
		if success:
			self.password = hashed
		return success
