"""
app/domains/users/schemas.py

Contains:
- Odmantic Model: UserModel  (database representation)
- Pydantic schemas: UserCreate, UserUpdate, UserPublic, UserDB (API + internal DTOs)

Notes:
 - This file uses odmantic.Model for DB-level objects and Pydantic BaseModel for API contracts.
 - Passwords must always be hashed before creating UserModel.password_hash.
 - Consider creating a unique index on `email` at DB setup time (see comments below).
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field as PydField, ConfigDict
from odmantic import Model, Field as OdmField

# ------------------------------
# Helper / small structured types
# ------------------------------


class Preferences(BaseModel):
    """
    User notification / privacy preferences.
    Kept as a small typed Pydantic model for convenient validation in endpoints.
    """
    timezone: Optional[str] = PydField(default="Asia/Kolkata")
    language: Optional[str] = PydField(default="en")
    notifications: Optional[Dict[str, bool]] = PydField(
        default_factory=lambda: {"email": True, "push": True, "mentor_nudges": True}
    )
    privacy: Optional[Dict[str, bool]] = PydField(
        default_factory=lambda: {"share_dreams_anonymously": False, "show_in_matching": True}
    )


class Consent(BaseModel):
    """Model to capture user consent options and timestamp."""
    terms: bool
    data_sharing: bool = False
    date_accepted: Optional[datetime] = None


class ModerationInfo(BaseModel):
    """Simple moderation metadata stored for the user (flags, last flagged time)."""
    flags: int = 0
    last_flagged_at: Optional[datetime] = None


# ------------------------------
# Odmantic DB Model
# ------------------------------
class UserModel(Model):
    """
    Odmantic model for 'users' collection.

    IMPORTANT:
    - Do not expose `password_hash` via APIs (use UserPublic or similar).
    - If you prefer document relationships, you can later change `pseudonym` or `onboarding` into proper embedded models.
    - To create a unique index on `email`, run (example):
        db = engine.get_database()
        await db.users.create_index("email", unique=True)
      Or use ODMantinc's index helpers at startup.
    """

    email: EmailStr = OdmField(...)  # unique constraint should be applied at DB-level
    password_hash: str = OdmField(...)  # hashed (bcrypt/argon2) password
    name: Optional[str] = OdmField(default=None)
    display_name: Optional[str] = OdmField(default=None)
    pseudonym: Optional[str] = OdmField(default=None)
    is_mentor: bool = OdmField(default=False)
    roles: List[str] = OdmField(default_factory=list)
    preferences: Optional[Dict[str, Any]] = OdmField(default=None)
    onboarding: Optional[Dict[str, Any]] = OdmField(default=None)
    embeddings: Optional[List[float]] = OdmField(default=None)  # vector embeddings for matching (optional)
    consent: Optional[Dict[str, Any]] = OdmField(default=None)
    status: str = OdmField(default="active")  # 'active' | 'suspended' | 'deleted'
    moderation: Optional[Dict[str, Any]] = OdmField(default=None)
    created_at: datetime = OdmField(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = OdmField(default=None)
    last_login: Optional[datetime] = OdmField(default=None)

    # class Config:
    #     # Odmantic uses Pydantic under the hood; this is a safe place to adjust JSON encoders if needed.
    #     json_encoders = {datetime: lambda v: v.isoformat()}


# ------------------------------
# Pydantic / API Schemas
# ------------------------------
class UserCreate(BaseModel):
    """
    Schema for user signup request.
    - password is plain-text at this boundary; remember to hash before DB insertion.
    """
    email: EmailStr
    password: str  # plain on input -> hash before saving
    name: Optional[str] = None
    timezone: Optional[str] = "Asia/Kolkata"
    language: Optional[str] = "en"
    onboarding: Optional[Dict[str, Any]] = None
    # NOTE: Do not accept roles/is_mentor from a regular signup request (server-side only)


class UserUpdate(BaseModel):
    """
    Fields allowed to be partially updated by the user via PATCH.
    Only include updatable fields here.
    """
    name: Optional[str] = None
    display_name: Optional[str] = None
    pseudonym: Optional[str] = None
    preferences: Optional[Preferences] = None
    onboarding: Optional[Dict[str, Any]] = None

class UserLogin(BaseModel):
    """
    Request body for login endpoint.
    """
    email: EmailStr
    password: str


class UserDB(BaseModel):
    """
    Internal representation of a user sent to internal services or used in tests.
    Contains password_hash (sensible only in server-side contexts).
    """
    id: str = PydField(..., alias="_id")
    email: EmailStr
    password_hash: str
    name: Optional[str]
    display_name: Optional[str]
    pseudonym: Optional[str]
    is_mentor: bool
    roles: List[str]
    preferences: Optional[Preferences]
    consent: Optional[Consent]
    status: str
    moderation: Optional[ModerationInfo]
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]

    class Config:
        allow_population_by_field_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserPublic(BaseModel):
    """
    Public-facing user representation returned by endpoints.
    Never include password_hash here.
    """
    id: str = PydField(..., alias="_id")
    email: EmailStr
    display_name: Optional[str] = None
    pseudonym: Optional[str] = None
    is_mentor: bool = False
    preferences: Optional[Preferences] = None
    created_at: datetime

    class Config:
        allow_population_by_field_name = True
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ------------------------------
# Convenience converters (optional helpers)
# ------------------------------
def usermodel_to_public(user: UserModel) -> UserPublic:
    """
    Convert an Odmantic UserModel instance to a UserPublic DTO.
    Useful in endpoints to hide sensitive fields before returning to client.
    """
    # Note: Odmantic's Model has an 'id' attribute which is an ObjectId; convert to str
    return UserPublic(
        **{
            "_id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "pseudonym": user.pseudonym,
            "is_mentor": user.is_mentor,
            "preferences": user.preferences,
            "created_at": user.created_at,
        }
    )



class UserInDB(BaseModel):
    """
    Pydantic schema for returning user data via the API.
    This is the correct Pydantic v2 syntax.
    """
    # model_config is the new way to configure models in v2
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    name: Optional[str] = None
    display_name: Optional[str] = None
    pseudonym: Optional[str] = None
    is_mentor: bool
    roles: List[str]
    status: str
    created_at: datetime
    last_login: Optional[datetime] = None
