from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from datetime import datetime, timezone
import mariadb

from ..models.account import Account
from .database import Database, get_db
from ..utils.settings import SETTINGS
from ..utils.token import decode_token, get_token, TokenData

utility_route = APIRouter(
    prefix=SETTINGS.api_path + "/utility",
    tags=["utility"]
)

bearer_scheme = HTTPBearer()

@utility_route.get("/health/backend", summary="Basic backend health check")
def site_health():
    """Simple health check to confirm the API is up."""
    return {
        "status": "ok",
        "message": "Backend is running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@utility_route.get("/health/database", summary="Basic database health check")
def database_health(db: Database = Depends(get_db)):
    """
    Checks DB connection and simple SELECT query.
    """
    try:
        result = db._fetch_one("SELECT 1 AS result")
        if result is None or result[0] != 1:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database query check failed: 'SELECT 1' did not return the expected value."
            )
        return {
            "status": "ok",
            "message": "Database connection and query successful",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except mariadb.Error as e:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query execution failed after successful connection: {str(e)}"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during database health check logic: {str(e)}"
        )

@utility_route.get("/getRoles")
def get_roles(db: Database = Depends(get_db)):
    roles = db.get_roles()
    formatted = [{"id": role_id, "name": name} for role_id, name in roles]
    return {"roles": formatted}

@utility_route.get("/getStatuses")
def get_statuses(db: Database = Depends(get_db)):
    statuses = db.get_statuses()
    formatted = [{"id": status_id, "name": name} for status_id, name in statuses]
    return {"statuses": formatted}


# Warning: Below this message are routes that would not be implemented on the real site, but are instead used for testing and showing implementation

@utility_route.post("/tokenInfo", summary="Token metadata and expiration")
def token_info(token: str = Depends(get_token)):
    token_data: TokenData = decode_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not token_data.exp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token does not contain expiration"
        )

    expire_time = datetime.fromtimestamp(token_data.exp, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    time_remaining = expire_time - now

    return {
        "expires_at": expire_time.isoformat(),
        "time_remaining": str(time_remaining),
        "time_remaining_seconds": time_remaining.total_seconds(),
        "data": token_data.model_dump()
    }
### TEMP ROUTE UNTILL IMPEMENTED
@utility_route.get("/getProducts")
def get_products(db: Database = Depends(get_db)):
    products = db._fetch_all("SELECT * FROM products")
    formatted = [{"id": id, "name": name} for id, name in products]
    return {"products": formatted}

@utility_route.get("/secureExample", dependencies=[Depends(bearer_scheme)], summary="Example secured route")
def secure_example():
    return {"message": "You are authorized"}
    
