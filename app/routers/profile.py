from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.login_manager import login_manager
from app.models import (
    Film,
    FilmWatched,
    Profile,
    User,
    get_watched_ids,
    get_watchlisted_ids,
)
from app.services.postgres import get_session

router = APIRouter(tags=["profile"], prefix="/profile")


@router.get("/")
async def get_profile(
    user: Annotated[User, Depends(login_manager)],
    session: Annotated[Session, Depends(get_session)],
) -> Profile:
    watched_films = list(
        session.exec(
            select(Film)
            .join(FilmWatched)
            .where(FilmWatched.user_id == user.login)
            .order_by(FilmWatched.added.desc())  # type: ignore
        ).all()
    )

    watched_films_id = get_watched_ids(session, user)
    to_watch_films_id = get_watchlisted_ids(session, user)

    return Profile(
        username=user.login,
        watched_count=len(watched_films_id),
        watchlist_count=len(to_watch_films_id),
        watched_films=watched_films,
    )
