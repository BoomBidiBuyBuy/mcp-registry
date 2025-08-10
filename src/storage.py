import os
from typing import Callable, Tuple

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


def _default_database_url() -> str:
    # Default to file-based SQLite for dev; user can override to MySQL/Postgres via env
    return os.getenv("DATABASE_URL", "sqlite:///./dev.db")


def get_engine_and_sessionmaker() -> Tuple[object, sessionmaker]:
    database_url = _default_database_url()
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    engine = create_engine(database_url, echo=False, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, SessionLocal


def init_db(engine) -> None:
    from models import MCPService, MCPTool  # noqa: F401 - import to register models

    Base.metadata.create_all(bind=engine)


def get_db_session(SessionLocal: sessionmaker) -> Callable:
    def _get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    return _get_db
