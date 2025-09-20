# app/core/config.py
"""
Application configuration using Pydantic BaseSettings.
Reads configuration from environment variables (12-factor style).
"""

from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # MongoDB connection URI (use a Render/Atlas URI in prod)
    MONGO_URI: str = Field(env="MONGO_URI")
    MONGO_DB: str = Field(env="MONGO_DB")

    # JWT (JSON Web Token) settings
    JWT_SECRET: str = Field(..., env="JWT_SECRET")  # must be set in env
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60 * 24 * 7, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # default 1 week

    # App
    APP_NAME: str = "yuu-backend"

    class Config:
        env_file = ".env"        # local development .env file
        env_file_encoding = "utf-8"


# Single settings instance imported across the app
settings = Settings()
