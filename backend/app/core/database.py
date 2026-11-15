"""SQLAlchemy engine/session. SQLite for dev; Postgres via DATABASE_URL in prod."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_columns():
    """Lightweight additive migration for SQLite dev DBs: add columns that
    create_all() cannot add to an existing table. No data loss, no Alembic
    needed for Phase 1."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    wanted = {
        "videos": {"detected_language": "VARCHAR(16)"},
        "clips": {
            "title_variations": "TEXT", "caption_variations": "TEXT",
            "selected_caption": "TEXT", "selected_hook": "VARCHAR(512)",
            "cta": "VARCHAR(255)", "detected_language": "VARCHAR(16)",
        },
    }
    with engine.begin() as conn:
        for table, cols in wanted.items():
            try:
                existing = {c["name"] for c in inspector.get_columns(table)}
            except Exception:
                continue
            for col, ddl in cols.items():
                if col not in existing:
                    conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{col}" {ddl}'))


def init_db():
    # Import models so Base.metadata knows all tables.
    import app.models.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    for d in (settings.videos_dir, settings.clips_dir, settings.covers_dir):
        d.mkdir(parents=True, exist_ok=True)
