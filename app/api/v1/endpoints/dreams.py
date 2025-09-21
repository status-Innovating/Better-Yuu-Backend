# app/api/v1/endpoints/dreams.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form, Header
from typing import List, Optional
from datetime import datetime
import os
import jwt  # PyJWT
import json
from pathlib import Path
import logging
from datetime import timezone

# Import domain services & models
from app.domains.dreams.schemas import DreamCreate, DreamDB, dreammodel_to_dto
from app.domains.dreams.services import (
    create_dream as svc_create_dream,
    list_dreams_for_user as svc_list_dreams_for_user,
    get_dream_by_id as svc_get_dream_by_id,
    analyze_dream_background as svc_analyze_dream_background,
)
from app.core.config import settings  # optional if you use settings; falls back to env
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/api/v1/dreams", tags=["dreams"])

# -------------------------
# Auth dependency
# -------------------------
JWT_SECRET = os.getenv("JWT_SECRET", getattr(settings, "JWT_SECRET", None))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", getattr(settings, "JWT_ALGORITHM", "HS256"))

async def get_current_user(authorization: Optional[str] = Header(None), x_user_id: Optional[str] = Header(None)):
    """
    Resolve the current user id.
    - Production: expects Authorization: Bearer <jwt> where payload contains {"sub": "<user_id>"}.
    - Dev/test: you can provide X-User-Id header to bypass JWT.
    Returns: dict {"user_id": "<id>"} or raises 401.
    """
    if x_user_id:
        return {"user_id": x_user_id}
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header or X-User-Id")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Authorization scheme must be Bearer")
        if not JWT_SECRET:
            raise HTTPException(status_code=500, detail="Server missing JWT_SECRET configuration")
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token - missing sub")
        return {"user_id": str(user_id)}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {e}")

# -------------------------
# File helpers (dev local upload)
# -------------------------
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./uploads")
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

def save_upload_file_local(upload_file: UploadFile) -> str:
    """
    Save uploaded file to local folder (development). For production, replace with GCS upload and return gs:// URI.
    Returns filepath string.
    """
ts = int(datetime.now(timezone.utc).timestamp() * 1000)    
safe_name = f"{ts}_{upload_file.filename}"
    dest = Path(UPLOAD_FOLDER) / safe_name
    with dest.open("wb") as f:
        f.write(upload_file.file.read())
    return str(dest)

# -------------------------
# Endpoints
# -------------------------
@router.post("/", response_model=DreamDB)
async def create_dream_endpoint(
    # UPDATED: Accept a single 'payload' form field with a JSON string for all metadata.
    # This is the standard way to send structured data with a file upload.
    payload_str: str = Form(..., alias="payload", description="A JSON string of the DreamCreate schema."),
    audio: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user)
):
    """
    Create a new dream entry using multipart/form-data.
    - **payload**: A form field containing a JSON string with the dream's metadata (text, timestamp, etc.).
    - **audio**: An optional audio file.
    """
    try:
        # Parse the JSON string from the form field and validate with Pydantic
        payload_data = json.loads(payload_str)
        payload = DreamCreate.model_validate(payload_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format in 'payload' form field.")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error in payload: {e}")

    audio_url = None
    audio_duration = None
    if audio:
        # DEV: save local file; PRODUCTION: replace with GCS upload and set audio_url to gs://bucket/obj
        audio_url = save_upload_file_local(audio)

    dream = await svc_create_dream(user_id=current_user["user_id"], payload=payload, audio_url=audio_url, audio_duration=audio_duration)
    
    # UPDATED: Use the DTO converter for a clean response
    return dreammodel_to_dto(dream)


@router.get("/me", response_model=List[DreamDB])
async def list_my_dreams(limit: int = 50, skip: int = 0, current_user = Depends(get_current_user)):
    docs = await svc_list_dreams_for_user(current_user["user_id"], limit=limit, skip=skip)
    # UPDATED: Simplified by using the DTO converter in a list comprehension
    return [dreammodel_to_dto(d) for d in docs]


@router.get("/{dream_id}", response_model=DreamDB)
async def get_dream(dream_id: str, current_user = Depends(get_current_user)):
    dream = await svc_get_dream_by_id(dream_id)
    if dream is None:
        raise HTTPException(status_code=404, detail="Dream not found")
    # Owner-only access
    if dream.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    # UPDATED: Use the DTO converter for a clean response
    return dreammodel_to_dto(dream)


@router.post("/{dream_id}/analyze", status_code=202)
async def analyze_dream_endpoint(dream_id: str, background_tasks: BackgroundTasks, current_user = Depends(get_current_user)):
    """
    Trigger analysis for a dream via Vertex AI + Speech-to-Text.
    This endpoint schedules the work as a background task and returns 202 Accepted.

    Behavior:
      - If dream has text_content: analyze that text.
      - Else if dream.audio_url is a gs:// URI: transcribe with Speech-to-Text then analyze.
      - Else returns 422 if neither text nor GCS audio present.

    The actual analysis is performed in svc_analyze_dream_background which updates the DB document.
    """
    logger.info(f"analyze_dream_endpoint: dream_id={dream_id}")
    dream = await svc_get_dream_by_id(dream_id)
    if dream is None:
        raise HTTPException(status_code=404, detail="Dream not found")
    if dream.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Basic validation: ensure we have some analyzable content or GCS audio
    has_text = bool((dream.text_content or "").strip())
    has_gcs_audio = bool(dream.audio_url and dream.audio_url.startswith("gs://"))

    if not has_text and not has_gcs_audio:
        # If audio_url is local path (dev), you must upload to GCS or transcribe on server side before analysis.
        # For production, prefer client -> signed GCS upload -> send gs:// URI.
        raise HTTPException(
            status_code=422,
            detail="No text or GCS audio available for analysis. Provide text_content or a 'gs://' audio_url."
        )

    # schedule background analysis (non-blocking)
    background_tasks.add_task(svc_analyze_dream_background, str(dream.id))
    return JSONResponse(status_code=202, content={"status": "accepted", "dream_id": str(dream.id)})
