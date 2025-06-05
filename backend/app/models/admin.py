from typing import Optional
from pydantic import EmailStr
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from .account import Account
from ..core.database import Database, Role, Status


class AdminAccount(Account):
    """Admin-specific account operations extending base Account functionality.

    Provides admin capabilities including account management,
    password resets, and bulk operations with consistent patterns.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def change_others_password(
        self, db: Database, new_password: str, account_id: int
    ) -> None:
        """Change another user's password with admin privileges.

        Args:
            db: Database connection instance
            new_password: Plaintext password to set
            account_id: Target account ID to modify

        Raises:
            HTTPException: 422 if password fails validation
            HTTPException: 500 if database update fails
        """
        if errors := self.verify_password(new_password):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(errors))

        hashed_password = self._hash_password(new_password)
        if not db.update_account(account_id, password=hashed_password):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update password for account {account_id}",
            )

        self.password = hashed_password

    def create_account(
        self, db: Database, role: Role, email: EmailStr, password: str
    ) -> int:
        """Create a new user account with admin privileges.

        Args:
            db: Database connection instance
            role: Role enum value for new account
            email: Validated email address
            password: Plaintext password for new account

        Returns:
            Created account ID

        Raises:
            HTTPException: 409 if email exists
            HTTPException: 422 if password invalid
            HTTPException: 500 if creation fails
        """
        if db.get_account(email=email.lower().strip()):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Account with email {email} already exists",
            )

        if errors := self.verify_password(password):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(errors))

        account_id = db.create_account(
            email=email.lower().strip(),
            password=self._hash_password(password),
            role=role,
        )

        if not account_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create account",
            )

        return account_id

    def get_account(self, db: Database, account_id: int) -> dict:
        """Retrieve account details by ID.

        Args:
            db: Database connection instance
            account_id: Target account ID to retrieve

        Returns:
            Dictionary containing account details

        Raises:
            HTTPException: 404 if account not found
        """
        if not (account := db.get_account(account_id=account_id)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account {account_id} not found",
            )

        return account

    def deactivate_account(self, db: Database, account_id: int) -> bool:
        """Deactivate an account without deleting it.

        Args:
            db: Database connection instance
            account_id: Target account ID to deactivate

        Returns:
            True if deactivation succeeded

        Raises:
            HTTPException: 404 if account not found
            HTTPException: 500 if update fails
        """
        self.get_account(db, account_id)

        if not db.update_account(account_id, status=Status.INACTIVE):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to deactivate account {account_id}",
            )

        return True

    def delete_accounts(self, db: Database, account_ids: list[int]) -> bool:
        """Permanently delete multiple accounts.

        Args:
            db: Database connection instance
            account_ids: List of account IDs to delete

        Returns:
            True if all deletions succeeded

        Raises:
            HTTPException: 500 if deletion fails
        """
        if not db.delete_accounts(account_ids):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete accounts {account_ids}",
            )

        return True

    def get_all_accounts(
        self, db: Database, filters: Optional[dict] = None
    ) -> list[dict]:
        """Retrieve all accounts with optional filtering.

        Args:
            db: Database connection instance
            filters: Optional dictionary of filter parameters

        Returns:
            List of account dictionaries matching filters

        Raises:
            HTTPException: 500 if query fails
        """
        try:
            return db.get_accounts(**(filters or {}))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Account retrieval failed: {str(e)}",
            )
