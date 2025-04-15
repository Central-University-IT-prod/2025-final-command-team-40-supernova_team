import os

from fastapi import FastAPI

from app.models import MessageResponse
from app.routers import (
    auth,
    films,
    profile,
    sessions,
    watched_managment,
    watchlist_management,
)
from app.services.postgres import create_db_and_tables

# Initiate Postgres
create_db_and_tables()

# Initiate FastAPI
app = FastAPI(title="Supernova")
app.include_router(auth.router)
app.include_router(watchlist_management.router)
app.include_router(films.router)
app.include_router(watched_managment.router)
app.include_router(sessions.router)
app.include_router(profile.router)


@app.get("/")
async def ping() -> MessageResponse:
    return MessageResponse(message="Pong!")


if os.getenv("DEBUG"):
    from app.debug import recreate_db

    @app.post("/debug/drop")
    def drop() -> None:
        recreate_db()
