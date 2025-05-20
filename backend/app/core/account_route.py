from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any

from ..utils.database import MongoDB, get_db

account_route = APIRouter(prefix="/accounts", tags=["accounts"])

@account_route.get("/{email}")
async def get_account(email: str, db: MongoDB = Depends(get_db)) -> Optional[Dict[str, Any]]:
    """Fetch account by email."""
    account = await db.collection("accounts").find_one({"email": email})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account["id"] = str(account["_id"])
    del account["_id"]
    return account