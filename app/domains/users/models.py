from datetime import datetime
from typing import Optional, List, Dict, Any
from odmantic import Model, Field as OdmField, Index
from pydantic import EmailStr

class UserModel(Model):
    """
    Odmantic model for 'users' collection.
    Indexes are now handled in the main application startup.
    """
    email: EmailStr
    password_hash: Optional[str] = OdmField(default=None)
    provider: Optional[str] = OdmField(default=None)
    provider_id: Optional[str] = OdmField(default=None)
    
    name: Optional[str] = OdmField(default=None)
    display_name: Optional[str] = OdmField(default=None)
    pseudonym: Optional[str] = OdmField(default=None)
    is_mentor: bool = OdmField(default=False)
    roles: List[str] = OdmField(default_factory=list)
    
    # --- THIS LINE IS NOW CORRECTED ---
    preferences: Optional[Dict[str, Any]] = OdmField(default=None)
    
    onboarding: Optional[Dict[str, Any]] = OdmField(default=None)
    embeddings: Optional[List[float]] = OdmField(default=None)
    consent: Optional[Dict[str, Any]] = OdmField(default=None)
    status: str = OdmField(default="active")
    moderation: Optional[Dict[str, Any]] = OdmField(default=None)
    created_at: datetime = OdmField(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = OdmField(default=None)
    last_login: Optional[datetime] = OdmField(default=None)
