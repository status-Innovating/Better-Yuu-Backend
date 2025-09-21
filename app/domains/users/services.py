# app/domains/users/services.py

from datetime import datetime
from odmantic import AIOEngine
from pydantic import EmailStr
from .models import UserModel

async def upsert_user_from_oauth(
    engine: AIOEngine,
    *,
    email: EmailStr,
    provider: str,
    provider_id: str,
    name_from_provider: str,
) -> UserModel:
    """
    Finds a user by email to link an OAuth account, or creates a new one.
    This logic handles both new and existing users gracefully.
    """
    user = await engine.find_one(UserModel, UserModel.email == email)
    now = datetime.utcnow()

    if user:
        # --- User exists: Link OAuth and update their info ---
        user.provider = provider
        user.provider_id = provider_id
        # Update name/display_name only if they are not already set
        if not user.name:
            user.name = name_from_provider
        if not user.display_name:
            user.display_name = name_from_provider
        user.last_login = now
        user.updated_at = now
    else:
        # --- User does not exist: Create a new one from OAuth data ---
        user = UserModel(
            email=email,
            provider=provider,
            provider_id=provider_id,
            name=name_from_provider,
            display_name=name_from_provider, # Set both name and display_name
            last_login=now,
            created_at=now,
        )
    
    await engine.save(user)
    return user
