from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any

class MongoDB:
    def __init__(self, uri: str, db_name: str):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

    def collection(self, name: str):
        return self.db[name]

    async def insert_one(self, collection_name: str, document: Dict[str, Any]) -> Optional[str]:
        result = await self.collection(collection_name).insert_one(document)
        return str(result.inserted_id)

    async def insert_many(self, collection_name: str, documents: List[Dict[str, Any]]) -> List[str]:
        result = await self.collection(collection_name).insert_many(documents)
        return [str(_id) for _id in result.inserted_ids]

    async def find_one(self, collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return await self.collection(collection_name).find_one(query)

    async def find_many(self, collection_name: str, query: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        cursor = self.collection(collection_name).find(query)
        return [doc async for doc in cursor]

    async def update_one(self, collection_name: str, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        result = await self.collection(collection_name).update_one(query, {"$set": update})
        return result.modified_count > 0

    async def update_many(self, collection_name: str, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        result = await self.collection(collection_name).update_many(query, {"$set": update})
        return result.modified_count

    async def delete_one(self, collection_name: str, query: Dict[str, Any]) -> bool:
        result = await self.collection(collection_name).delete_one(query)
        return result.deleted_count > 0

    async def delete_many(self, collection_name: str, query: Dict[str, Any]) -> int:
        result = await self.collection(collection_name).delete_many(query)
        return result.deleted_count

    async def count_documents(self, collection_name: str, query: Dict[str, Any] = {}) -> int:
        return await self.collection(collection_name).count_documents(query)

    
def get_db(request: Request) -> MongoDB:
    mongodb = getattr(request.app.state, "mongodb", None)
    if mongodb is None:
        raise Exception("Database not initialized")
    return mongodb