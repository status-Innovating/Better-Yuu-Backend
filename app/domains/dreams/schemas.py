"""
app/domains/dreams/schemas.py

Contains:
- Odmantic Model: DreamModel  (database representation)
- Pydantic schemas: DreamCreate, DreamAnalysis, DreamDB, etc.

Notes:
 - Audio files should be uploaded to Cloud Storage (GCS/S3). Save signed URLs in `audio_url`.
 - analysis.raw_response can contain the full LLM output; control access carefully.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field as PydField, HttpUrl
from odmantic import Model, Field as OdmField


# ------------------------------
# Small structured types used inside analysis
# ------------------------------
class SymbolAnalysis(BaseModel):
    symbol: str
    confidence: float = PydField(..., ge=0.0, le=1.0)
    explanation: Optional[str] = None


class RiskFlags(BaseModel):
    """
    Risk flags inferred from analysis; used for triage and safe routing.
    Values like 'low'/'medium'/'high' allow graded responses.
    """
    self_harm: str = "none"  # enum: none|low|medium|high
    suicide: str = "none"
    violence: bool = False
    abuse_mention: bool = False


class DreamAnalysis(BaseModel):
    """
    Structured analysis produced by the AI pipeline.
    - status: lifecycle of the analysis
    - raw_response: store full model output for audits; restrict access in production.
    """
    status: str = "pending"  # pending | processing | complete | failed
    model: Optional[str] = None
    generated_at: Optional[datetime] = None
    summary: Optional[str] = None
    emotions: Optional[Dict[str, float]] = None          # e.g., {"anxiety": 0.8, "joy": 0.2}
    sentiment_score: Optional[float] = PydField(None, ge=-1.0, le=1.0)
    themes: Optional[List[str]] = None
    symbols: Optional[List[SymbolAnalysis]] = None
    risk_flags: Optional[RiskFlags] = None
    raw_response: Optional[Any] = None  # original LLM/AI response (audit), may store as dict/string


# ------------------------------
# Dream Odmantic DB model
# ------------------------------
class DreamModel(Model):
    """
    Odmantic model representing a dream entry.
    - `user_id` stored as string for simplicity (can be changed to a Reference[UserModel] if desired).
    - `analysis` holds the result of the AI pipeline. Start with `analysis` as None then populate when ready.
    """
    user_id: str = OdmField(...)  # store user id (string). Option: use Reference for real relations
    timestamp: datetime = OdmField(default_factory=datetime.utcnow)
    timezone: Optional[str] = OdmField(default="Asia/Kolkata")
    text_content: Optional[str] = OdmField(default=None, metadata={"max_length": 20000})
    audio_url: Optional[str] = OdmField(default=None)  # signed URL to Cloud Storage
    audio_duration_seconds: Optional[float] = OdmField(default=None)
    audio_transcript: Optional[str] = OdmField(default=None)
    language: Optional[str] = OdmField(default="en")
    analysis: Optional[Dict[str, Any]] = OdmField(default=None)  # store structured analysis JSON
    share_policy: Optional[Dict[str, bool]] = OdmField(default_factory=lambda: {
        "shareable": False, "forum_anonymous": False, "allow_research": False
    })
    status: str = OdmField(default="created")  # created | processing | analyzed | error
    created_at: datetime = OdmField(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = OdmField(default=None)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ------------------------------
# Pydantic / API Schemas
# ------------------------------
class DreamCreate(BaseModel):
    """
    Payload accepted when user creates a new dream entry.
    For audio uploads, prefer multipart/form-data: upload file -> return signed URL -> POST with audio_url.
    """
    text_content: Optional[str] = None
    timestamp: Optional[datetime] = None  # client may pass local timestamp; server should convert/save UTC
    timezone: Optional[str] = "Asia/Kolkata"
    share_policy: Optional[Dict[str, bool]] = PydField(
        default_factory=lambda: {"shareable": False, "forum_anonymous": False, "allow_research": False}
    )


class SymbolAnalysisSchema(SymbolAnalysis):
    pass  # reuse


class RiskFlagsSchema(RiskFlags):
    pass  # reuse


class DreamAnalysisSchema(DreamAnalysis):
    pass  # reuse; this ensures type hints and JSON schema for responses


class DreamDB(BaseModel):
    """
    Public representation of a stored dream (returned to clients).
    - analysis is included but may be null if processing not yet complete.
    """
    id: str = PydField(..., alias="_id")
    user_id: str
    timestamp: datetime
    timezone: Optional[str] = "Asia/Kolkata"
    text_content: Optional[str] = None
    audio_url: Optional[HttpUrl] = None
    audio_duration_seconds: Optional[float] = None
    audio_transcript: Optional[str] = None
    language: Optional[str] = "en"
    analysis: Optional[DreamAnalysisSchema] = None
    share_policy: Optional[Dict[str, bool]] = None
    status: str = "created"
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ------------------------------
# Convenience converters
# ------------------------------
def dreammodel_to_dto(d: DreamModel) -> DreamDB:
    """
    Convert Odmantic DreamModel to DreamDB Pydantic DTO for API response.
    Handles simple field conversions and ensures proper types.
    """
    return DreamDB(
        **{
            "_id": str(d.id),
            "user_id": d.user_id,
            "timestamp": d.timestamp,
            "timezone": d.timezone,
            "text_content": d.text_content,
            "audio_url": d.audio_url,
            "audio_duration_seconds": d.audio_duration_seconds,
            "audio_transcript": d.audio_transcript,
            "language": d.language,
            "analysis": d.analysis,  # if analysis is a dict, Pydantic will coerce it
            "share_policy": d.share_policy,
            "status": d.status,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
        }
    )
