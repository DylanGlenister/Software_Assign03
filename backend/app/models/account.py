import re
from typing import Optional, Type
import datetime

from bcrypt import checkpw, gensalt, hashpw
from pydantic import EmailStr, ValidationError

from ..core.database import Database, Role, Status
from ..utils.fields import filter_dict


class Account:
    def __init__(
        self,
        accountID: int,
        creationDate: str,
        role: Role,
        status: Status,
        email: str | None,
        password: str | None,
        firstname: str | None,
        lastname: str | None,
        db: Database
    ):
        self.db: Database = db
        self.accountID: int = accountID
        self.creationDate: str = creationDate
        self.role: Role = role
        self.status: Status = status
        self.email: str | None = email
        self.password: str | None = password
        self.firstname: str | None = firstname
        self.lastname: str | None = lastname

    @classmethod
    def _hash_password(cls, password: str) -> str:
        """Hash a plain-text password using bcrypt."""
        salt: bytes = gensalt()
        return hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @classmethod
    def login(
        cls: Type["Account"], db: Database, email: EmailStr, password: str
    ) -> Optional["Account"]:
        """Attempt to find an account with matching email and password."""
        account: dict | None = db.get_account(email=email)
        if not account:
            print("No account found with that email.")
            return None

        if checkpw(password.encode("utf-8"), account["password"].encode("utf-8")):
            return cls(
                accountID=account["accountID"],
                email=account["email"],
                password=account["password"],
                firstname=account["firstname"],
                lastname=account["lastname"],
                creationDate=account["creationDate"],
                role=account["role"],
                status=account["status"],
                db=db
            )
        else:
            print(f"Password '${password}' is incorrect.")
            return None

    @classmethod
    def verify_password(cls, password):
        errors = []

        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")

        if not any(char.isupper() for char in password):
            errors.append("Password must contain at least one uppercase letter.")

        if not any(char.islower() for char in password):
            errors.append("Password must contain at least one lowercase letter.")

        if not any(char.isdigit() for char in password):
            errors.append("Password must contain at least one digit.")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain at least one special character.")

        return errors

    def verify_perms(self, required_roles: list[Role], inverse: bool = False) -> bool:
        """
        Check if the user's role matches the required roles.

        - Returns True if the user's role is Role.OWNER (superuser override).
        - If inverse=True: returns True if user's role is NOT in required_roles.
        - If inverse=False: returns True if user's role IS in required_roles.
        """
        user: Role = Role(self.role)
        if user == Role.OWNER:
            return not inverse

        if inverse:
            return user not in required_roles

        return user in required_roles

    def update_info(self, **fields) -> dict:
        filtered_fields = filter_dict(
            fields, {"email", "status", "firstname", "lastname"}
        )

        if not filtered_fields:
            return {"error": "No valid fields to update."}

        if "email" in filtered_fields:
            try:
                filtered_fields["email"] = str(filtered_fields["email"].strip().lower())
            except ValidationError:
                return {"error": "Invalid email format."}

        if "status" in filtered_fields:
            try:
                filtered_fields["status"] = Role(filtered_fields["status"])
            except ValidationError:
                raise ValidationError(["Status does not exist"])

        success: bool = bool(self.db.update_account(self.accountID, **filtered_fields))

        if success:
            for key, value in filtered_fields.items():
                setattr(self, key, value)
        return {"success": success}

    def change_password(self, new_password: str) -> bool:
        errors = self.verify_password(new_password)
        if errors:
            raise ValueError("\n".join(errors))

        try:
            hashed: str = self._hash_password(new_password)
            success: bool = bool(self.db.update_account(self.accountID, password=hashed))

            if not success:
                raise RuntimeError("Failed to update password in database")

            self.password = hashed
            return True

        except Exception as e:
            raise RuntimeError(f"An unknown error occurred: {str(e)}")
