from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field as PydField, HttpUrl
from odmantic import Model, Field as OdmField

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
    text_content: Optional[str] = OdmField(default=None, max_length=20000)
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