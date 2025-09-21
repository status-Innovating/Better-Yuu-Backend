from pydantic.config import ConfigDict
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

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


# ------------------------------
# Convenience converters
# ------------------------------
def dreammodel_to_dto(d: DreamModel) -> DreamDB:
    """
    Convert Odmantic DreamModel to DreamDB Pydantic DTO for API response.
    Handles simple field conversions and ensures proper types.
    """
    # Using model_dump and then constructing the DTO ensures correct aliasing and type coercion
    model_data = d.model_dump()
    model_data["_id"] = str(d.id) # Ensure the id is a string for the alias
    return DreamDB.model_validate(model_data)