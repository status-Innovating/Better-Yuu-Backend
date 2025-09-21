"""
FastAPI app entrypoint.
Wires up GCP credentials from an environment secret (if provided) and creates DB indexes at startup.
"""

import os
import base64
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import OperationFailure

from app.core.config import settings
from app.db.session import engine
from app.api.v1.endpoints import auth as auth_router_module
from app.api.v1.endpoints import dreams as dreams_router

# --- Logging Configuration ---
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE = LOGS_DIR / "app.log"
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router_module.router)
app.include_router(dreams_router.router)


@app.on_event("startup")
async def startup_event():
    logger.info(f"VERIFYING SETTINGS: The configured Google region is '{settings.GOOGLE_REGION}'")
    logger.info("Application startup...")

    # UPDATED: Read the service account key from the settings object
    sa_b64 = settings.GCP_SA_KEY_B64
    if sa_b64:
        try:
            try:
                sa_bytes = base64.b64decode(sa_b64)
                if not sa_bytes.strip().startswith(b"{"):
                    sa_bytes = sa_b64.encode("utf-8")
            except Exception:
                sa_bytes = sa_b64.encode("utf-8")

            key_path = "/tmp/gcp_sa_key.json"
            Path(key_path).write_bytes(sa_bytes)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
            logger.info("Wrote GCP service account key to /tmp/gcp_sa_key.json")
        except Exception as e:
            logger.error("Error writing GCP SA key: %s", e, exc_info=True)

    # Create DB Indexes
    try:
        db_name = settings.MONGO_DB
        users_coll = engine.client[db_name]["users"]
        await users_coll.create_index("email", unique=True)
        
        dreams_coll_name = "dreammodel"
        dreams_coll = engine.client[db_name][dreams_coll_name]
        await dreams_coll.create_index([("user_id", 1), ("timestamp", -1)])
        logger.info("Database indexes ensured successfully.")
    except OperationFailure as e:
        logger.error("Index creation failed due to a database operation error: %s", e)
    except Exception as e:
        logger.warning("A non-critical error occurred during index creation: %s", e)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown...")
    try:
        engine.client.close()
    except Exception as e:
        logger.warning("Error during motor client shutdown: %s", e)


@app.get("/")
async def health():
    return {"status": "ok"}