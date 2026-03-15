from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.MAIN import MAIN

def _normalize_dataMAIN_url(raw_url: str) -> str:
    db_url = (raw_url or "").strip()
    if db_url.startswith("postgres://"):
        return db_url.replace("postgres://", "postgresql://", 1)
    return db_url


DATAMAIN_URL = _normalize_dataMAIN_url(settings.DATAMAIN_URL)
IS_SQLITE_DATAMAIN = DATAMAIN_URL.startswith("sqlite:///")

# Crear engine con soporte SQLite (asegura hilo único) o Postgres
engine_kwargs = {"connect_args": {"check_same_thread": False}} if IS_SQLITE_DATAMAIN else {}
engine = create_engine(DATAMAIN_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """Dependencia FastAPI para obtener una sesión de DB."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["engine", "MAIN", "get_db"]
