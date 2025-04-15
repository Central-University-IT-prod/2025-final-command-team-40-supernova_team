import base64
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.integrations.kinopoisk import get_films_by_genres_and_keywords, get_genre_ids
from app.login_manager import login_manager
from app.models import Film, Genres, MessageResponse, User, get_watchlisted_ids
from app.routers.films import FilmReturn
from app.services.postgres import get_session
from app.services.redis import redis_session

router = APIRouter(tags=["session"], prefix="/session")


FILMS_PER_SESSION = 10

logger = logging.getLogger(__name__)


def count_weight(film: Film, genres: list[str]) -> float:
    film_genres = [genre for genre in film.genres if genre in genres]
    return len(film_genres) / len(genres) * 0.6 + (film.rating or 0) / 10 * 0.4


@router.post("/create/{user_login}")
async def create_session(
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(login_manager)],
    user_login: str,
    genres: Genres,
) -> list[FilmReturn]:
    logger.info(base64.b64encode(user_login.encode()).decode())
    user_target = session.exec(
        select(User).where(
            User.login == user_login,
        ),
    ).first()
    if user_target is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user_target.login == user.login:
        raise HTTPException(
            status_code=400,
            detail="You can't create session with yourself",
        )

    if redis_session.get(f"session:{user.login}") == "active":
        raise HTTPException(
            status_code=400,
            detail="Session already exists with this user",
        )

    if redis_session.get(f"session:{user_target.login}") == "active":
        raise HTTPException(
            status_code=400,
            detail="Session already exists with this user",
        )

    # Create session
    redis_session.set(f"session:{user_target.login}", "active")
    redis_session.set(f"session:{user.login}", "active")
    redis_session.set(f"session:{user.login}:{user_target.login}", "active")

    user_watchlist = get_watchlisted_ids(session, user)
    user_target_watchlist = get_watchlisted_ids(session, user_target)

    user_watchlist = session.exec(select(Film).where(Film.id.in_(user_watchlist)))  # type: ignore
    user_target_watchlist = session.exec(
        select(Film).where(Film.id.in_(user_target_watchlist)),  # type: ignore
    )
    genres_list = genres.genres

    # find common films
    user_watchlist = [
        film
        for film in user_watchlist
        if any(genre in genres_list for genre in film.genres)
    ]
    user_target_watchlist = [
        film
        for film in user_target_watchlist
        if any(genre in genres_list for genre in film.genres)
    ]

    res = []
    res_end = []

    for film in user_watchlist:
        if film in user_target_watchlist:
            res.append(film)
        else:
            res_end.append(film)

    for film in user_target_watchlist:
        if film not in res and film not in res_end:
            res_end.append(film)
    res.extend(res_end)
    res = [
        film for film in res if film.title and film.image_url and film.id < 500_000_000
    ]

    if len(res) < FILMS_PER_SESSION:
        kinop_unsorted = []
        genre_ids = await get_genre_ids(genres_list)

        for id in genre_ids:
            films = await get_films_by_genres_and_keywords([id], "")
            films = [
                film
                for film in films
                if film.title
                and film.image_url
                and film.title not in [i.title for i in res]
                and film.title not in [i.title for i in kinop_unsorted]
            ]
            kinop_unsorted.extend(films)

        kinop_weighted = [(i, count_weight(i, genres_list)) for i in kinop_unsorted]
        kinop_weighted = sorted(kinop_weighted, key=lambda x: x[1], reverse=True)
        kinop_weighted = [i[0] for i in kinop_weighted]

        res.extend(kinop_weighted)

    return [
        FilmReturn(
            id=film.id,
            title=film.title,
            description=film.description,
            image_url=film.image_url,
            genres=film.genres,
            year=film.year,
            rating=film.rating,
            film_url=film.film_url,
            is_watchlisted=bool(film.id in get_watchlisted_ids(session, user)),
        )
        for film in res[:10]
    ]


@router.post("/end/{user_login}")
async def end_session(
    user_login: str,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(login_manager)],
) -> MessageResponse:
    user_target = session.exec(select(User).where(User.login == user_login)).first()

    if user_target is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user_target.login == user.login:
        raise HTTPException(
            status_code=400,
            detail="You can't end session with yourself",
        )
    redis_session.set(f"session:{user_target.login}", "inactive")
    redis_session.set(f"session:{user.login}", "inactive")
    redis_session.set(f"session:{user.login}:{user_target.login}", "inactive")

    return MessageResponse(message="Session ended")
