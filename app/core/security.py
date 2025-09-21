# app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Any, Union

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from odmantic import AIOEngine

from app.core.config import settings
from app.db.session import get_engine
# The import for schemas is no longer needed here if it only contained TokenData
from app.domains.users.models import UserModel 

ACCESS_TOKEN_COOKIE_NAME = "yuu_access_token"

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """
    Creates a JWT access token.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(
    request: Request,
    engine: AIOEngine = Depends(get_engine),
) -> UserModel:
    """
    Dependency to get the current user from the JWT stored in a cookie.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            # If the 'sub' field is missing from the token, it's invalid.
            raise credentials_exception
            
    except JWTError:
        # If the token is malformed or the signature is invalid, an error is raised.
        raise credentials_exception
    
    user = await engine.find_one(UserModel, UserModel.email == email)
    
    if user is None:
        raise credentials_exception
        
    return user
