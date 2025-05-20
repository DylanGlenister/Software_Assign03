from fastapi import APIRouter
from ..utils.database import MongoDB, get_db

account_route = APIRouter(prefix="/accounts", tags=["accounts"])
