# app/main.py
"""
FastAPI app entrypoint.
- Includes router(s).
- Creates DB indexes at startup (e.g., unique index on users.email).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import OperationFailure

from app.core.config import settings
from app.db.session import engine
from app.domains.users.models import UserModel
from app.api.v1.endpoints import auth as auth_router_module  # import router module

app = FastAPI(title=settings.APP_NAME)

# Basic CORS (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this list in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router_module.router)


# Create indexes at startup (idempotent)
@app.on_event("startup")
async def create_indexes():
    """
    Create DB indexes (run once at startup). This avoids race conditions if multiple instances run:
    - `email` unique index on users collection.
    """
    # get_motor_collection returns MotorCollection for raw index creation
    users_coll = engine.get_collection(UserModel)

    try:
        # Ensure unique index on email
        await users_coll.create_index("email", unique=True)
    except OperationFailure as e:
        # Index creation failure (log or handle in real app)
        # For example: if unique constraints conflict with existing duplicates, you'll need a migration.
        print("Index creation error:", str(e))

# Health check
@app.get("/")
async def health():
    return {"status": "ok"}
