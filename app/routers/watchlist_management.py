import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlmodel import Session, select

from app.integrations.kinopoisk import get_film_by_id
from app.login_manager import login_manager
from app.models import Film, FilmAdd, FilmWatchlist, MessageResponse, User
from app.services.minio import add_image
from app.services.postgres import get_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["watchlist"], prefix="/watchlist")


@router.get("/")
def get_watchlist(
    user: Annotated[User, Depends(login_manager)],
    session: Annotated[Session, Depends(get_session)],
) -> list[Film]:
    return list(
        session.exec(
            select(Film)
            .join(FilmWatchlist)
            .where(FilmWatchlist.user_id == user.login)
            .order_by(FilmWatchlist.added.desc())  # type: ignore
        ).all()
    )


@router.post("/add")
async def add_new_film_to_watchlist(
    film: FilmAdd,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(login_manager)],
) -> MessageResponse:
    db_film = Film.model_validate_json(film.model_dump_json())

    session.add(db_film)
    session.commit()
    session.refresh(db_film)
    db_film.id += 500_000_000
    session.add(db_film)
    session.commit()

    watchlist_record = FilmWatchlist(user_id=user.login, film_id=db_film.id)
    session.add(watchlist_record)
    session.commit()

    return MessageResponse(message="Film added to watchlist")


@router.post("/add-with-image")
def add_new_film_with_image_to_watchlist(
    film: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(login_manager)],
) -> MessageResponse:
    base_url = str(request.base_url)
    image_url = add_image(file, base_url)

    db_film = Film.model_validate_json(film)
    db_film.image_url = image_url

    session.add(db_film)
    session.commit()
    session.refresh(db_film)
    db_film.id += 500_000_000
    session.add(db_film)
    session.commit()

    logger.info("Film id: %s", db_film.id)

    watchlist_record = FilmWatchlist(user_id=user.login, film_id=db_film.id)
    session.add(watchlist_record)
    session.commit()

    return MessageResponse(message="Film added to watchlist")


@router.post("/add/{film_id}")
async def add_existing_film_to_watchlist(
    film_id: int,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(login_manager)],
) -> MessageResponse:
    film = session.exec(select(Film).where(Film.id == film_id)).first()

    if film is None:
        logger.info("Film %s was not found in local database, seeking on kinopoisk")
        film = await get_film_by_id(film_id)
        logger.info("Added film %s to watchlist", film.id)
        session.add(film)
        session.commit()

    # As we dont have `ON CONFLICT`
    if session.get(FilmWatchlist, (user.login, film_id)) is None:
        watchlist_record = FilmWatchlist(user_id=user.login, film_id=film_id)
        session.add(watchlist_record)
        session.commit()

    return MessageResponse(message="Film added to watchlist")


@router.delete("/remove/{film_id}")
async def remove_film_from_watchlist(
    film_id: int,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(login_manager)],
) -> MessageResponse:
    if record := session.get(FilmWatchlist, (user.login, film_id)):
        session.delete(record)
    else:
        return MessageResponse(message="Film not found in watchlist")

    session.add(user)
    session.commit()

    return MessageResponse(message="Film removed from watchlist")
