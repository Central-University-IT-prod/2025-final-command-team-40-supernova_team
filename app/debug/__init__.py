from sqlmodel import SQLModel

from app.services.postgres import engine


def recreate_db() -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
