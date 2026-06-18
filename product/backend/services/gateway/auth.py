"""Module d'authentification JWT pour Thoth Gateway.

Endpoints:
    POST /auth/register   — Créer un compte
    POST /auth/login      — Connexion (renvoie un JWT)
    GET  /auth/me         — Profil de l'utilisateur connecté

Dépendances:
    python-jose[cryptography]  → JWT
    passlib[bcrypt]            → hachage des mots de passe
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.database import get_session, init_db
from shared.models import User

# ──────────────────────────────────────────────
# Configuration JWT
# ──────────────────────────────────────────────

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "thoth-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 heures

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/auth", tags=["auth"])


# ──────────────────────────────────────────────
# Modèles Pydantic
# ──────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or "@" not in v:
            raise ValueError("Email invalide")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Le nom d'utilisateur doit contenir au moins 3 caractères")
        if len(v) > 50:
            raise ValueError("Le nom d'utilisateur est trop long (50 max)")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Le mot de passe doit contenir au moins 6 caractères")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    created_at: Optional[str] = None
    last_login: Optional[str] = None


# ──────────────────────────────────────────────
# Utilitaires JWT
# ──────────────────────────────────────────────


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Dépendance FastAPI : extraire et valider l'utilisateur depuis le JWT."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token invalide")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable ou désactivé")
    return user


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_session)):
    """Créer un nouveau compte utilisateur."""
    # Vérifier si l'email existe déjà
    result = await session.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Un compte avec cet email existe déjà")

    # Vérifier si le username existe déjà
    result = await session.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ce nom d'utilisateur est déjà pris")

    # Créer l'utilisateur
    user = User(
        id=str(uuid.uuid4()),
        email=request.email,
        username=request.username,
        hashed_password=get_password_hash(request.password),
        is_active=True,
        created_at=datetime.utcnow(),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Générer le token
    access_token = create_access_token(data={"sub": user.id})
    return TokenResponse(access_token=access_token, user=user.to_dict())


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)):
    """Authentifier un utilisateur et retourner un JWT."""
    result = await session.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    # Mettre à jour last_login
    user.last_login = datetime.utcnow()
    await session.commit()

    access_token = create_access_token(data={"sub": user.id})
    return TokenResponse(access_token=access_token, user=user.to_dict())


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retourner les informations de l'utilisateur connecté."""
    return current_user.to_dict()


@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Rafraîchir le token JWT avant expiration."""
    new_token = create_access_token(data={"sub": current_user.id})
    return TokenResponse(access_token=new_token, user=current_user.to_dict())
