from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings
from app.tools.hash_utils import compute_jd_hash


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    db_path = database_url.replace("sqlite:///", "", 1)
    path = Path(db_path)
    if not path.is_absolute():
        path = settings.project_root / path
    path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent(settings.database_url)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if settings.database_url.startswith("sqlite"):
        _migrate_sqlite_jobs_hash()


def _migrate_sqlite_jobs_hash() -> None:
    with engine.begin() as connection:
        columns = connection.execute(text("PRAGMA table_info(jobs)")).fetchall()
        column_names = {column[1] for column in columns}
        if "jd_hash" not in column_names:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN jd_hash VARCHAR(64) DEFAULT ''"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_jd_hash ON jobs (jd_hash)"))
        rows = connection.execute(text("SELECT id, jd_text FROM jobs WHERE jd_hash IS NULL OR jd_hash = ''")).fetchall()
        for row in rows:
            connection.execute(
                text("UPDATE jobs SET jd_hash = :jd_hash WHERE id = :job_id"),
                {"jd_hash": compute_jd_hash(row.jd_text or ""), "job_id": row.id},
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
