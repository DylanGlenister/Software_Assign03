from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from fastapi import status as httpStatus
from pydantic import EmailStr

from ..core.database import Database, Role, Status
from .account import Account


class EmployeeAccount(Account):
    def __init__(
        self, accountID: int, creationDate: str, role: Role,
        status: Status, email: EmailStr | None, password: str | None,
        firstname: str | None, lastname: str | None,
    ):
        super().__init__(
            accountID, creationDate, role, status,
            email, password, firstname, lastname)

    def e():
        pass
