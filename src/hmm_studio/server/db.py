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
    """Additively add any FitJob columns missing from an existing table.

    SQLModel.create_all() creates missing TABLES but never alters existing
    ones, so a DB created under an older schema is missing every column added
    since it was first created — e.g. ``covariate_names`` / ``lengths`` /
    ``parent_id`` / ``k_override`` (K-scan) and ``emission_override`` /
    ``n_mix_override`` (compare). SQLite supports cheap additive ALTERs; add
    any column the model declares but the table lacks, as NULLable (existing
    rows get NULL — the app's readers already treat empty/None as the default).
    Idempotent: a no-op once every column exists.
    """
    table = FitJob.__table__
    with engine.begin() as conn:
        existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table.name})"))}
        for col in table.columns:
            if col.name in existing:
                continue
            sqltype = col.type.compile(dialect=engine.dialect)
            conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN "{col.name}" {sqltype}'))


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
