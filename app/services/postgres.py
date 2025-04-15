import os
from collections.abc import Generator
from typing import Any

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, Any, None]:
    with Session(engine) as session:
        yield session
