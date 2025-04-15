from __future__ import annotations

import logging
import os
from typing import Any, TypedDict

import aiohttp
from fastapi import HTTPException
from sqlmodel import SQLModel
from starlette import status

from app.models import Film

KINOPOLISK_API_URL = "https://kinopoiskapiunofficial.tech/api/v2.2"
KINOPOISK_API_TIMEOUT = 1  # second

KINOPOISK_API_KEYS = os.environ["KINOPOISK_API_KEYS"].split(",")


class OutOfTokensError(Exception): ...


class TokenStorage:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.selected_token_i = 0

    def swap(self) -> None:
        cur = self.selected_token_i

        # Last token already selected :(
        if cur + 1 == len(self.tokens):
            raise OutOfTokensError

        self.selected_token_i += 1

    def get(self) -> str:
        return self.tokens[self.selected_token_i]

    def get_header(self) -> dict[str, str]:
        return {"X-API-KEY": self.get()}

    def tokens_left(self) -> bool:
        return (len(self.tokens) - self.selected_token_i - 1) >= 1


tokens = TokenStorage(KINOPOISK_API_KEYS)


class KinopoiskClient:
    def __init__(self, api_url: str, tokens: TokenStorage) -> None:
        self.api_url = api_url
        self.tokens = tokens

        self.stats = {}

    async def get(self, url: str, **kwds) -> KinopoiskResponse:  # noqa: ANN003
        while True:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    f"{self.api_url}/{url}",
                    **kwds,
                    headers=tokens.get_header(),
                ) as response,
            ):
                if response.status == status.HTTP_402_PAYMENT_REQUIRED:
                    logger.warning(f"SPENT: {self.stats}")  # noqa: G004
                    tokens.swap()
                    continue

                if url in self.stats:
                    self.stats[url] += 1
                else:
                    self.stats[url] = 1

                return KinopoiskResponse(
                    json=await response.json(), status=response.status
                )


class KinopoiskResponse(TypedDict):
    status: int
    json: dict[str, Any]


kinopoisk = KinopoiskClient(KINOPOLISK_API_URL, tokens)

logger = logging.getLogger(__name__)


async def get_genre_ids(genres_list: list[str]) -> list[int]:
    response = await kinopoisk.get("/films/filters")

    filters = response["json"]

    return [genre["id"] for genre in filters["genres"] if genre["genre"] in genres_list]


async def get_films_by_genres_and_keywords(
    genre_ids: list[int],
    search: str,
) -> list[Film]:
    logger.info(f"Genres: {genre_ids}, search: {search}")

    response = await kinopoisk.get(
        "/films",
        params={
            "genres": ",".join(map(str, genre_ids)),
            "page": 1,
            "keyword": search,
        },
    )
    logger.info(response["status"])
    data = response["json"]

    logger.info(data)
    films_data = data["items"]

    logger.info(f"Films data: {films_data}")  # noqa: G004
    films = []

    for film_data in films_data:
        film = Film(
            id=film_data["kinopoiskId"],
            title=film_data["nameRu"],
            image_url=film_data["posterUrl"],
            genres=[genre["genre"] for genre in film_data["genres"]],
            year=film_data["year"],
            rating=film_data["ratingKinopoisk"],
        )
        films.append(film)
    return films


async def get_film_by_id(film_id: int) -> Film:
    response = await kinopoisk.get(f"/films/{film_id}")
    if response["status"] == status.HTTP_404_NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Film not found",
        )

    film_detail = response["json"]

    return Film(
        id=film_detail["kinopoiskId"],
        title=film_detail["nameRu"],
        description=film_detail["description"],
        image_url=film_detail["coverUrl"] or film_detail["posterUrl"],
        genres=[genre["genre"] for genre in film_detail["genres"]],
        year=film_detail["year"],
        rating=film_detail["ratingKinopoisk"],
        film_url=film_detail["webUrl"],
    )
