"""Database engine + session management for hmm-studio."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

# Import models so SQLModel.metadata picks them up.
from hmm_studio.server import models  # noqa: F401


def create_db_engine(db_path: str | Path):
    """Create a SQLite engine and ensure tables exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
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
