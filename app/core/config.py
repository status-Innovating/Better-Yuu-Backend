"""
Application configuration using Pydantic BaseSettings.
Reads configuration from environment variables (12-factor style).
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # MongoDB connection URI (use a Render/Atlas URI in prod)
    MONGO_URI: str = Field(env="MONGO_URI")
    MONGO_DB: str = Field(env="MONGO_DB")

    # JWT (JSON Web Token) settings
    JWT_SECRET: str = Field(..., env="JWT_SECRET")  # must be set in env
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60 * 24 * 7, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # default 1 week
    UPLOAD_FOLDER: str = Field("./uploads", env="UPLOAD_FOLDER")
    USE_REAL_AI: bool = Field(True, env="USE_REAL_AI")

     # --- Optional Google Cloud Settings (Defaults to None if not in .env) ---
    GOOGLE_PROJECT: Optional[str] = Field(None, env="GOOGLE_PROJECT")
    GOOGLE_REGION: Optional[str] = Field(None, env="GOOGLE_REGION")
    # VERTEX_AI_MODEL: Optional[str] = Field(None, env="VERTEX_AI_MODEL")
    VERTEX_AI_MODEL: Optional[str] = Field("gemini-2.5-flash-lite")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = Field(None, env="GOOGLE_APPLICATION_CREDENTIALS")
    GCP_SA_KEY_B64: Optional[str] = Field(None, env="GCP_SA_KEY_B64")
    
    # App
    APP_NAME: str = "yuu-backend"

    class Config:
        env_file = ".env"        # local development .env file
        env_file_encoding = "utf-8"


# Single settings instance imported across the app
settings = Settings()
