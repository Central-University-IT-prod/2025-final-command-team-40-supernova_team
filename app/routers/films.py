from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from sqlmodel import Session, select
from starlette import status

from app.integrations.gemini import get_discussions
from app.integrations.kinopoisk import (
    get_film_by_id,
    get_films_by_genres_and_keywords,
    get_genre_ids,
)
from app.login_manager import login_manager
from app.models import Film, FilmReturn, Image, User, get_watchlisted_ids
from app.services.minio import add_image
from app.services.postgres import get_session

router = APIRouter(tags=["films"], prefix="/films")

KINOPOLISK_API_KEY = "REDACTED"
KINOPOLISK_API_URL = "https://kinopoiskapiunofficial.tech/api/v2.2"


@router.post("/add-image")
async def upload_film_image(
    request: Request,
    file: UploadFile,
    user: Annotated[User, Depends(login_manager)],  # noqa: ARG001
) -> Image:
    base_url = str(request.base_url)

    image_url = add_image(file, base_url)
    return Image(image_url=image_url)


@router.get("/discuss/{film_name}/{year}")
async def get_themes_for_discussion(
    user: Annotated[User, Depends(login_manager)],  # noqa: ARG001
    film_name: str,
    year: int,
) -> list[str]:
    return get_discussions(film_name, year)


@router.get("/discuss-id/{film_id}")
async def get_themes_for_discussion_by_id(
    film_id: int,
    user: Annotated[User, Depends(login_manager)],  # noqa: ARG001
    session: Annotated[Session, Depends(get_session)],
) -> list[str]:
    film = session.get(Film, film_id)

    if film is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    film_name = film.title
    film_year = film.year

    if film_year is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    return get_discussions(film_name, film_year)


@router.get("/")
async def get_films(
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(login_manager)],
    search: Annotated[str | None, Query()] = None,
    genres: Annotated[list[str] | None, Query()] = None,
) -> list[FilmReturn]:
    query = select(Film)

    if search:
        search = f"%{search.lower()}%"
        query = query.where(
            (Film.title.ilike(search)),  # type: ignore
        )
    else:
        search = ""
    if genres and len(genres) > 0:
        query = query.where(Film.genres.overlap(genres))  # type: ignore (works)
    else:
        genres = []

    films = list(session.exec(query).all())
    # Find genre IDs
    genre_ids = await get_genre_ids(genres)
    # Request to Kinopoisk API to get films by genres
    films_kinopoisk = await get_films_by_genres_and_keywords(genre_ids, search)
    films_kinopoisk = [
        film
        for film in films_kinopoisk
        if film not in films and film.title and film.image_url
    ]
    if not films_kinopoisk:
        films_kinopoisk = []

    watchlist = get_watchlisted_ids(session, user)

    films.extend(films_kinopoisk)
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
            is_watchlisted=bool(film.id in watchlist),
        )
        for film in films
        if film.id < 500_000_000
    ]


@router.get("/{film_id}")
async def get_film(
    film_id: int,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(login_manager)],
) -> FilmReturn:
    film = session.exec(select(Film).where(Film.id == film_id)).first()

    if not film:
        film = await get_film_by_id(film_id)
        if not film:
            raise HTTPException(status_code=404, detail="Film not found")

    watchlist = get_watchlisted_ids(session, user)

    film_discussed = FilmReturn(
        id=film.id,
        title=film.title,
        description=film.description,
        image_url=film.image_url,
        genres=film.genres,
        year=film.year,
        rating=film.rating,
        film_url=film.film_url,
        is_watchlisted=bool(film.id in watchlist),
    )

    return film_discussed  # noqa: RET504
