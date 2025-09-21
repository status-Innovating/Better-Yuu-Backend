"""
API endpoints for user authentication, supporting both password-based and Google OAuth2 flows.

This implementation uses a secure, HttpOnly cookie to store the JWT for all
authentication methods, which is the recommended practice to mitigate XSS attacks.
"""

from fastapi import APIRouter, Depends, Request, Response, status, HTTPException
from fastapi.responses import RedirectResponse
from httpx_oauth.clients.google import GoogleOAuth2
from odmantic import AIOEngine
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    create_access_token,
    get_current_user,
)
from app.db.session import get_engine
from app.domains.users import services as user_services
from app.domains.users.models import UserModel
from app.domains.users.schemas import UserInDB

# --- SETUP ---

router = APIRouter()

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Google OAuth client initialization
google_client = GoogleOAuth2(
    settings.GOOGLE_CLIENT_ID,
    settings.GOOGLE_CLIENT_SECRET,
)

# --- SCHEMAS FOR PASSWORD AUTH ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# --- HELPER FUNCTIONS ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a password using bcrypt."""
    return pwd_context.hash(password)

# --- PASSWORD-BASED AUTH ENDPOINTS ---

@router.post("/signup", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, engine: AIOEngine = Depends(get_engine)):
    """
    Handles new user registration with email and password.
    """
    # Check if a user with this email already exists (could be from OAuth)
    existing_user = await engine.find_one(UserModel, UserModel.email == payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    password_hash = get_password_hash(payload.password)
    user = UserModel(
        email=payload.email,
        password_hash=password_hash,
        name=payload.name,
        display_name=payload.name,
    )

    try:
        saved_user = await engine.save(user)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered."
        )
    return saved_user


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(response: Response, payload: UserLogin, engine: AIOEngine = Depends(get_engine)):
    """
    Handles user login with email and password.
    On success, it sets a secure HttpOnly cookie with the JWT.
    """
    user = await engine.find_one(UserModel, UserModel.email == payload.email)
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    
    access_token = create_access_token(subject=user.email)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"message": "Login successful"}

# --- GOOGLE OAUTH2 ENDPOINTS ---

@router.get("/login/google", include_in_schema=False)
async def login_google():
    """
    Redirects the user to Google's authentication page.
    """
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    authorization_url = await google_client.get_authorization_url(
        redirect_uri, scope=["email", "profile"]
    )
    return RedirectResponse(authorization_url)


@router.get("/google/callback", include_in_schema=False)
async def auth_google_callback(request: Request, engine: AIOEngine = Depends(get_engine)):
    """
    Handles the callback from Google, upserts the user, sets the session cookie,
    and redirects to the frontend.
    """
    code = request.query_params.get("code")
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    token_data = await google_client.get_access_token(code, redirect_uri)
    user_id, user_email, user_info = await google_client.get_user_info(token_data)

    user = await user_services.upsert_user_from_oauth(
        engine=engine,
        email=user_email,
        provider="google",
        provider_id=user_id,
        name_from_provider=user_info.get("name", user_email.split('@')[0]),
    )

    access_token = create_access_token(subject=user.email)

    response = RedirectResponse(url=settings.FRONTEND_URL, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response

# --- COMMON SESSION ENDPOINTS ---

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    """
    Logs the user out by deleting the access token cookie.
    """
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
    return {"message": "Successfully logged out"}


@router.get("/users/me", response_model=UserInDB)
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
    """
    Protected endpoint to fetch the details of the currently logged-in user.
    """
    return current_user
