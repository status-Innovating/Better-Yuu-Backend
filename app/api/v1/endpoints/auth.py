# app/api/v1/endpoints/auth.py
"""
Auth router: sign-up and sign-in endpoints.

Features included:
- Signup (POST /api/v1/auth/signup) -> creates user after hashing password
- Login  (POST /api/v1/auth/login)  -> verifies password and returns JWT access token
- get_current_user dependency to protect routes (demonstration)
"""

from datetime import datetime, timedelta
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel

from odmantic import ObjectId
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.db.session import engine
from app.domains.users.schemas import UserCreate, UserLogin, UserModel, usermodel_to_public, UserPublic

# Router for this module
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Password hashing context: bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for FastAPI dependency (token passed in Authorization: Bearer <token>)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# -------------------------
# Token helpers
# -------------------------
def create_access_token(subject: str, expires_delta: timedelta = None) -> str:
    """
    Create a JWT token encoding the `subject` (usually user id as string).
    We use HS256 and settings.JWT_SECRET. Expiry is set by ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "exp": expire}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt; return hashed string for DB storage."""
    return pwd_context.hash(password)


# -------------------------
# Auth endpoints
# -------------------------
@router.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate):
    """
    Sign up new user.
    - Validate input via UserCreate.
    - Hash password and save user.
    - Create unique index on email at app startup (see main.py); here handle duplicate key errors gracefully.
    """
    # Hash password BEFORE creating DB model
    password_hash = get_password_hash(payload.password)

    # Build the Odmantic model
    user = UserModel(
        email=payload.email,
        password_hash=password_hash,
        name=payload.name,
        display_name=payload.name if payload.name else None,
        preferences={"timezone": payload.timezone, "language": payload.language}
    )

    try:
        saved = await engine.save(user)  # persist to MongoDB
    except DuplicateKeyError:
        # Unique constraint on email violated (catch at DB level)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    except Exception as exc:
        # Generic error handling (log as needed)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create user")

    # Return public projection (no password_hash)
    return usermodel_to_public(saved)


# Token response schema
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    """
    Log a user in:
    - Find user by email (case-sensitive by default).
    - Verify password.
    - Return JWT access token with 'sub' = user_id (string).
    """
    # Find user by email
    user = await engine.find_one(UserModel, UserModel.email == payload.email)
    if not user:
        # Generic message to avoid leaking existence
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # (Optional) update last_login timestamp
    user.last_login = datetime.utcnow()
    await engine.save(user)

    access_token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=access_token)


# -------------------------
# Dependency: get_current_user
# -------------------------
async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserModel:
    """
    Decode JWT token, fetch user from DB, and return UserModel instance.
    Raises HTTPException on failure conditions.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Convert to ObjectId when querying (Odmantic uses ObjectId for model.id)
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise credentials_exception

    user = await engine.find_one(UserModel, UserModel.id == oid)
    if user is None:
        raise credentials_exception

    return user


# Example protected route demonstrating dependency usage (optional)
@router.get("/me", response_model=UserPublic)
async def me(current_user: UserModel = Depends(get_current_user)):
    """
    Protected endpoint returning current user's public profile.
    """
    return usermodel_to_public(current_user)
