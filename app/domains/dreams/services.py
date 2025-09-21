"""
Dream business logic updated to call real AI services (ai_engine.services).
Uses asyncio and background tasks to avoid blocking the event loop.
Includes structured logging and follows SonarQube best practices.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from odmantic import AIOEngine

from app.db.session import get_engine
from app.domains.dreams.models import DreamModel
from app.domains.dreams.schemas import DreamCreate
from app.domains.ai_engine import services as ai_services


# ------------------------------
# Logging Setup
# ------------------------------
logger = logging.getLogger(__name__)


# ------------------------------
# Constants
# ------------------------------
DEFAULT_LANGUAGE = "en"
DEFAULT_SHARE_POLICY = {
    "shareable": False,
    "forum_anonymous": False,
    "allow_research": False
}
STATUS_CREATED = "created"
STATUS_PROCESSING = "processing"
STATUS_ANALYZED = "analyzed"
STATUS_ERROR = "error"


# ------------------------------
# Core Services
# ------------------------------

async def create_dream(
    user_id: str,
    payload: DreamCreate,
    audio_url: Optional[str] = None,
    audio_duration: Optional[float] = None
) -> DreamModel:
    """
    Create a new dream entry in the database.
    """
    engine: AIOEngine = get_engine()
    now = datetime.now(timezone.utc)  # ✅ SonarQube fix: use timezone-aware UTC

    dream = DreamModel(
        user_id=user_id,
        timestamp=payload.timestamp or now,
        timezone=payload.timezone or "UTC",
        text_content=payload.text_content,
        audio_url=audio_url,
        audio_duration_seconds=audio_duration,
        audio_transcript=None,
        language=DEFAULT_LANGUAGE,
        analysis=None,
        share_policy=payload.share_policy or DEFAULT_SHARE_POLICY,
        status=STATUS_CREATED,
        created_at=now,
        updated_at=now
    )

    logger.info(f"Creating dream for user_id={user_id}, dream_id will be assigned after save.")
    await engine.save(dream)
    logger.info(f"Dream created with id={dream.id}")

    return dream


async def list_dreams_for_user(
    user_id: str,
    limit: int = 50,
    skip: int = 0
) -> List[DreamModel]:
    """
    Retrieve a paginated list of dreams for a specific user, sorted by creation date (newest first).
    """
    engine: AIOEngine = get_engine()
    logger.info(f"Fetching dreams for user_id={user_id}, skip={skip}, limit={limit}")

    docs = await engine.find(
        DreamModel,
        DreamModel.user_id == user_id,
        sort=DreamModel.created_at.desc(),
        skip=skip,
        limit=limit
    )

    logger.info(f"Found {len(docs)} dreams for user_id={user_id}")
    return docs


async def get_dream_by_id(dream_id: str) -> Optional[DreamModel]:
    """
    Retrieve a dream by its ID. Returns None if ID is invalid or dream not found.
    """
    engine: AIOEngine = get_engine()

    try:
        obj_id = ObjectId(dream_id)
    except InvalidId:
        logger.warning(f"Invalid ObjectId format: {dream_id}")
        return None

    logger.debug(f"Querying dream with ObjectId={obj_id}")
    doc = await engine.find_one(DreamModel, DreamModel.id == obj_id)

    if doc:
        logger.info(f"Dream found: id={doc.id}, user_id={doc.user_id}")
    else:
        logger.warning(f"Dream not found for id={dream_id}")

    return doc


# ------------------------------
# Background Analysis Service
# ------------------------------

async def analyze_dream_background(dream_id: str) -> None:
    """
    Background task to analyze a dream's content (text or audio) using AI services.
    Updates the dream's `analysis` and `status` fields in the database.
    Safe to run asynchronously — handles all errors internally.
    """
    logger.info(f"Starting background analysis for dream_id={dream_id}")

    engine: AIOEngine = get_engine()

    # Validate and convert dream_id
    try:
        obj_id = ObjectId(dream_id)
    except InvalidId:
        logger.error(f"Invalid ObjectId format in background task: {dream_id}")
        return

    # Fetch dream
    dream = await engine.find_one(DreamModel, DreamModel.id == obj_id)
    if not dream:
        logger.warning(f"Dream not found for id={dream_id} during background analysis")
        return

    logger.info(f"Processing dream id={dream.id} for user_id={dream.user_id}")

    # Update status to processing
    dream.status = STATUS_PROCESSING
    dream.updated_at = datetime.now(timezone.utc)  # ✅ SonarQube fix
    await engine.save(dream)
    logger.debug(f"Dream {dream.id} status updated to '{STATUS_PROCESSING}'")

    text_to_analyze = dream.text_content or ""

    # If no text, try to transcribe from audio (GCS only)
    if not text_to_analyze and dream.audio_url:
        if dream.audio_url.startswith("gs://"):
            try:
                logger.info(f"Transcribing audio from GCS: {dream.audio_url}")
                transcript = await ai_services.transcribe_gcs_audio(dream.audio_url)
                dream.audio_transcript = transcript
                text_to_analyze = transcript
                logger.info(f"Transcription completed for dream {dream.id}, length={len(transcript)} chars")
            except Exception as e:
                error_msg = f"transcription error: {str(e)}"
                logger.exception(f"Failed to transcribe audio for dream {dream.id}: {error_msg}")
                await _mark_dream_as_failed(engine, dream, error_msg)
                return
        else:
            error_msg = "audio_url not a gs:// URI; STT requires GCS or local audio upload."
            logger.warning(f"Cannot transcribe non-GCS audio for dream {dream.id}: {dream.audio_url}")
            await _mark_dream_as_failed(engine, dream, error_msg)
            return

    # Skip if still no text
    if not text_to_analyze.strip():
        error_msg = "No text content available for analysis after transcription attempt."
        logger.warning(f"Dream {dream.id} has no analyzable text")
        await _mark_dream_as_failed(engine, dream, error_msg)
        return

    # Analyze text with Vertex AI
    try:
        logger.info(f"Analyzing text for dream {dream.id} with Vertex AI...")
        analysis = await ai_services.analyze_text_with_vertex(text_to_analyze)
        dream.analysis = analysis
        dream.status = STATUS_ANALYZED
        dream.updated_at = datetime.now(timezone.utc)  # ✅ SonarQube fix
        await engine.save(dream)
        logger.info(f"Dream {dream.id} successfully analyzed and updated")
    except Exception as exc:
        error_msg = f"analysis error: {str(exc)}"
        logger.exception(f"Failed to analyze dream {dream.id}: {error_msg}")
        await _mark_dream_as_failed(engine, dream, error_msg)


# ------------------------------
# Helper Functions
# ------------------------------

async def _mark_dream_as_failed(
    engine: AIOEngine,
    dream: DreamModel,
    error_message: str
) -> None:
    """
    Helper to update dream status to 'error' with error message in analysis field.
    Avoids code duplication.
    """
    dream.analysis = {
        "status": STATUS_ERROR,
        "error": error_message
    }
    dream.status = STATUS_ERROR
    dream.updated_at = datetime.now(timezone.utc)  # ✅ SonarQube fix
    await engine.save(dream)
    logger.error(f"Dream {dream.id} marked as failed: {error_message}")