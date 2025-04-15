from __future__ import annotations

import datetime

from passlib.context import CryptContext
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, Session, SQLModel, select

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def now() -> int:
    date = datetime.datetime.now(tz=datetime.UTC)
    return int(date.timestamp() * 1000)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    login: str = Field(index=True, unique=True)
    hashed_password: str | None = None

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)

    def set_password(self, password: str) -> None:
        self.hashed_password = pwd_context.hash(password)


class Film(SQLModel, table=True):
    id: int = Field(primary_key=True)

    # Mandatory
    title: str
    description: str | None = None
    image_url: str | None = None

    genres: list[str] = Field(
        default_factory=list,
        sa_type=ARRAY(String),  # type: ignore
    )

    # Optional
    year: int | None = None
    rating: float | None
    film_url: str | None = None


class FilmAdd(SQLModel, table=False):
    # Mandatory
    title: str
    description: str | None = None
    image_url: str | None = None

    genres: list[str] | None = Field(
        default_factory=list,
        sa_type=ARRAY(String),  # type: ignore
    )

    # Optional
    year: int | None = None
    rating: float | None = None
    film_url: str | None = None


class Genres(SQLModel, table=False):
    genres: list[str]


class FilmReturn(SQLModel, table=False):
    id: int | None = None

    title: str | None = None
    description: str | None = None
    image_url: str | None = None

    genres: list[str] | None = []

    # Optional
    year: int | None = None
    rating: float | None
    film_url: str | None = None
    is_watchlisted: bool | None = False


class Profile(SQLModel, table=False):
    username: str
    watched_count: int
    watchlist_count: int
    watched_films: list[Film]


class MessageResponse(SQLModel, table=False):
    message: str


class UserPing(SQLModel, table=False):
    username: str


class Token(SQLModel, table=False):
    access_token: str


class Image(SQLModel, table=False):
    image_url: str


class FilmWatchlist(SQLModel, table=True):
    user_id: str = Field(primary_key=True, foreign_key="user.login")
    film_id: int = Field(primary_key=True, foreign_key="film.id")

    added: datetime.datetime = Field(default_factory=datetime.datetime.now)


class FilmWatched(SQLModel, table=True):
    user_id: str = Field(primary_key=True, foreign_key="user.login")
    film_id: int = Field(primary_key=True, foreign_key="film.id")

    added: datetime.datetime = Field(default_factory=datetime.datetime.now)


def get_watched_ids(session: Session, user: User) -> list[int]:
    return list(
        session.exec(
            select(FilmWatched.film_id).where(FilmWatched.user_id == user.login)
        ).all()
    )


def get_watchlisted_ids(session: Session, user: User) -> list[int]:
    return list(
        session.exec(
            select(FilmWatchlist.film_id).where(FilmWatchlist.user_id == user.login)
        ).all()
    )
