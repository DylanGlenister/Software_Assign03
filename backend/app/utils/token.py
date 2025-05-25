from datetime import datetime, timedelta, timezone
from fastapi import Depends, Header, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from ..models.customer import CustomerAccount
from ..models.account import Account
from ..core.database import get_db, Database
from .settings import SETTINGS

bearer_scheme = HTTPBearer()

def create_access_token(data: dict, expires_in_mins: int = None):
    to_encode: dict = data.copy()
    time: int = expires_in_mins if expires_in_mins else SETTINGS.access_token_expire_minutes

    expire: datetime = datetime.now(timezone.utc) + timedelta(minutes=time)
    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(to_encode, SETTINGS.secret_key, algorithm=SETTINGS.algorithm)
    if isinstance(encoded_jwt, bytes):
        encoded_jwt = encoded_jwt.decode('utf-8')
    return encoded_jwt

def decode_access_token(token: str):
    try:
        return jwt.decode(token, SETTINGS.secret_key, algorithms=[SETTINGS.algorithm])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_token_from_header(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    return credentials.credentials

def get_customer_from_token(token: str = Depends(get_token_from_header)) -> CustomerAccount:
    data = decode_access_token(token)
    if not data or "account_ID" not in data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return CustomerAccount(data["account_ID"], data["email"], "", None, 1, 1)

def get_current_account(token: str = Depends(get_token_from_header), db: Database = Depends(get_db)) -> Account:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    account_id = payload.get("account_ID")
    row = db.get_account_by_id(account_id)
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    return Account(*row)