"""Auth routes: register, login, current user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth_deps import get_current_user
from auth_schemas import TokenResponse, UserLogin, UserPublic, UserRegister
from auth_security import create_access_token, hash_password, verify_password
from database import get_db
from models import User

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(body: UserRegister, db: Session = Depends(get_db)) -> UserPublic:
    """Create a new account (password stored hashed in PostgreSQL)."""
    user = User(
        email=body.email.lower().strip(),
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc
    db.refresh(user)
    return UserPublic.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Exchange email/password for a JWT access token."""
    stmt = select(User).where(User.email == body.email.lower().strip())
    user = db.execute(stmt).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserPublic,
    openapi_extra={"security": [{"BearerAuth": []}]},
)
def me(current: User = Depends(get_current_user)) -> UserPublic:
    """Return the authenticated user (requires `Authorization: Bearer <token>`)."""
    return UserPublic.model_validate(current)
