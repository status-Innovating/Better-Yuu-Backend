# app/core/config.py
"""
Application configuration using Pydantic BaseSettings.
Reads configuration from environment variables (12-factor style).
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Pydantic v2 model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra fields from the environment
    )

    # MongoDB connection
    MONGO_URI: str
    MONGO_DB: str

    # JWT (JSON Web Token) settings
    # The `...` as the default value makes the field required.
    JWT_SECRET: str = Field(...)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week

    # Google OAuth Settings (now explicitly required)
    GOOGLE_CLIENT_ID: str = Field(...)
    GOOGLE_CLIENT_SECRET: str = Field(...)
    GOOGLE_REDIRECT_URI: str = Field(...)

    FRONTEND_URL: str = Field(...)

    # App
    APP_NAME: str = "yuu-backend"


# Single settings instance imported across the app
settings = Settings()
