from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Optional
from pydantic import BaseModel

from ..core.database import get_db, Database, Role, Status
from .settings import SETTINGS

bearer_scheme = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    accountID: int
    email: str
    role: Role
    status: Status
    exp: Optional[int] = None


def create_token(
    data: dict,
    expires_in: int = SETTINGS.access_token_expire_minutes,
    secret_key: str = SETTINGS.secret_key,
    algorithm: str = SETTINGS.algorithm,
) -> str:
    """Create a JWT token with the given data and expiration."""
    payload = data.copy()
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=expires_in)
    payload["exp"] = int(expire_time.timestamp())

    encoded = jwt.encode(payload, secret_key, algorithm=algorithm)
    return encoded if isinstance(encoded, str) else encoded.decode("utf-8")


def decode_token(
    token: str,
    secret_key: str = SETTINGS.secret_key,
    algorithm: str = SETTINGS.algorithm,
) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return TokenData(**payload)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Optional[str]:
    """
    Gets the JWT token from the authorization headers.
    """
    if credentials:
        return credentials.credentials
    return None


def get_secure_token(
    credentials: HTTPAuthorizationCredentials = Depends(get_token),
) -> str:
    """
    Gets the JWT token from the authorization headers, throwing an error if its missing.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )

    return credentials


def get_account_data(
    token: str = Depends(get_secure_token), db: Database = Depends(get_db)
) -> dict:
    """
    Validate token and get full account details from database.
    """
    token_data = decode_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    account_data = db.get_account(accountId=token_data.accountID)
    if not account_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    account_data["db"] = db
    return account_data
