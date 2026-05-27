"""Database engine + session management for hmm-studio."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import text

# Import models so SQLModel.metadata picks them up.
from hmm_studio.server import models  # noqa: F401
from hmm_studio.server.models import FitJob


def _ensure_fitjob_columns(engine) -> None:
    """Additively add compare-mode columns to an existing fitjob table.

    SQLModel.create_all() creates missing TABLES but never alters existing
    ones, so a DB created before the compare feature lacks emission_override /
    n_mix_override. SQLite supports cheap additive ALTERs; add any missing.
    Idempotent: a no-op once the columns exist.
    """
    table = FitJob.__tablename__
    wanted = {"emission_override": "VARCHAR", "n_mix_override": "INTEGER"}
    with engine.begin() as conn:
        existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
        for name, sqltype in wanted.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sqltype}"))


def create_db_engine(db_path: str | Path):
    """Create a SQLite engine and ensure tables exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    _ensure_fitjob_columns(engine)
    return engine


@contextmanager
def get_session(engine) -> Iterator[Session]:
    """Yield a session bound to ``engine``; commits or rolls back on exit."""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
