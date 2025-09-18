import asyncio
from odmantic import AIOEngine
from motor.motor_asyncio import AsyncIOMotorClient


# Connection URI for MongoDB Atlas
MONGODB_URI = "not real " #check group for this

# Create the low-level Motor client
client = AsyncIOMotorClient(MONGODB_URI)

# Create the Odmantic engine (ODM layer)
engine = AIOEngine(client=client, database="better_yuu")


async def db_connection():
    try:
        await client.admin.command("ping")
        print("MongoDB connection is successful")
    except Exception as e:
        print("Failed to run", e)


asyncio.run(db_connection())