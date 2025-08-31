import os
from typing import Callable, Tuple
from sqlalchemy import inspect, text
from constants import DEFAULT_SYSTEM_PROMPT_MAX_LENGTH

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
    Base.metadata.create_all(bind=engine)
    # Ensure new columns exist for backward compatibility without migrations
    try:
        insp = inspect(engine)
        cols = [c.get("name") for c in insp.get_columns("mcp_roles")]
        if "default_system_prompt" not in cols:
            # Best-effort portable SQL; works for SQLite/MySQL/Postgres
            with engine.begin() as conn:
                conn.execute(
                    text(
                        f"ALTER TABLE mcp_roles ADD COLUMN default_system_prompt VARCHAR({DEFAULT_SYSTEM_PROMPT_MAX_LENGTH}) NOT NULL DEFAULT ''"
                    )
                )
    except Exception:
        # Do not crash startup if inspection/DDL fails; assume fresh DB
        pass


def get_db_session(SessionLocal: sessionmaker) -> Callable:
    def _get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    return _get_db
