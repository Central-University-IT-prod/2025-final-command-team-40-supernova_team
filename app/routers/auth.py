from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlmodel import Session, select

from app.login_manager import login_manager
from app.models import MessageResponse, Token, User, UserPing
from app.services.postgres import get_session
from app.services.redis import redis_session

router = APIRouter(tags=["auth"], prefix="/auth")


@router.post("/login")
async def login(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
) -> Token:
    # Verify user credentials
    user = session.exec(select(User).where(User.login == username)).first()

    if user and user.verify_password(password):
        # Generate JWT token
        access_token = login_manager.create_access_token(user.login)

        # Store the token in Redis
        redis_session.set(f"access_token:{user.login}", access_token)

        # Return the access token
        return Token(access_token=access_token)

    raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/register")
async def register(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
) -> Token:
    # Check if the user already exists
    existing_user = session.exec(select(User).where(User.login == username)).first()

    if existing_user:
        raise HTTPException(status_code=401, detail="Login already registered")

    # Register the new user
    user = User(login=username)
    user.set_password(password)

    session.add(user)
    session.commit()

    # Return success status
    access_token = login_manager.create_access_token(user.login)

    # Store the token in Redis
    redis_session.set(f"access_token:{user.login}", access_token)

    # Return the access token
    return Token(access_token=access_token)


@router.post("/logout/{login}")
async def logout(
    login: str,
    user: Annotated[User, Depends(login_manager)],  # noqa: ARG001
) -> MessageResponse:
    redis_session.delete(f"access_token:{login}")
    return MessageResponse(message="Logged out")


@router.get("/ping")
async def auth_ping(user: Annotated[User, Depends(login_manager)]) -> UserPing:
    return UserPing(username=user.login)
