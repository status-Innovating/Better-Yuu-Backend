from typing import Optional
from odmantic import Field, Model
from datetime import datetime
from pydantic import EmailStr
from enum import Enum

class Provider(str, Enum):
    google = "google"
    facebook = "facebook"
    github = "github"


class UserModel(Model):
    provider: Provider
    name: str
    user_name: str
    email : EmailStr
    access_token : Optional[str] = None
    refresh_token : Optional[str] = None
    token_expiry : Optional[datetime] = None
    created_at : datetime = Field(default_factory=datetime.utcnow)







