# app/db/session.py
"""
Odmantic AIOEngine setup for the app.
Creates an AsyncIOMotorClient and uses it to construct an AIOEngine.
"""
from odmantic import AIOEngine
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# Create Motor client and Odmantic engine.
# Use the DB name from settings (MONGO_DB).
_client = AsyncIOMotorClient(settings.MONGO_URI)
engine = AIOEngine(client=_client, database=settings.MONGO_DB)



# --- THIS IS THE NEW, REQUIRED FUNCTION ---
async def get_engine() -> AIOEngine:
    """
    FastAPI dependency that provides a reusable AIOEngine instance.
    """
    return engine

# Usage NOTE:
# - await engine.save(model_instance)
# - await engine.find_one(Model, Model.field == value)
# - engine.get_collection(Model) returns the raw Motor collection for index creation
