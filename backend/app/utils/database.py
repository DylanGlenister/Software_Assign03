from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

class MongoDB:
    def __init__(self, uri: str, db_name: str):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

    def collection(self, name: str):
        return self.db[name]
    
def get_db(request: Request) -> MongoDB:
    mongodb = getattr(request.app.state, "mongodb", None)
    if mongodb is None:
        raise Exception("Database not initialized")
    return mongodb