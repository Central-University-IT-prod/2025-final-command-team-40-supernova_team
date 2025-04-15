from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlmodel import Session, select

from app.integrations.kinopoisk import get_film_by_id
from app.login_manager import login_manager
from app.models import Film, FilmAdd, FilmWatched, FilmWatchlist, MessageResponse, User
from app.services.minio import add_image
from app.services.postgres import get_session

router = APIRouter(tags=["watched"], prefix="/watched")


@router.get("/")
def get_watched(
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(login_manager)],
) -> list[Film]:
    return list(
        session.exec(
            select(Film)
            .join(FilmWatched)
            .where(FilmWatched.user_id == user.login)
            .order_by(FilmWatched.added.desc())  # type: ignore
        ).all()
    )


@router.post("/add")
async def add_new_film_to_watched(
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

    watched_record = FilmWatched(user_id=user.login, film_id=db_film.id)
    session.add(watched_record)
    session.commit()

    return MessageResponse(message="Film added to watched")


@router.post("/add-with-image")
def add_new_film_with_image_to_watched(
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

    watched_record = FilmWatched(user_id=user.login, film_id=db_film.id)
    session.add(watched_record)
    session.commit()

    return MessageResponse(message="Film added to watched")


@router.post("/add/{film_id}")
async def add_existing_film_to_watched(
    film_id: int,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(login_manager)],
) -> MessageResponse:
    film = session.exec(select(Film).where(Film.id == film_id)).first()

    if film is None:
        session.add(await get_film_by_id(film_id))
        session.commit()

    if film := session.get(FilmWatchlist, (user.login, film_id)):
        session.delete(film)
        session.commit()

    # As we dont have `ON CONFLICT`
    if session.get(FilmWatched, (user.login, film_id)) is None:
        watched_record = FilmWatched(user_id=user.login, film_id=film_id)
        session.add(watched_record)
        session.commit()

    return MessageResponse(message="Film added to watched")
