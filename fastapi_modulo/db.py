import json
import os
from contextvars import ContextVar
from datetime import datetime
from typing import Dict, Optional

from dotenv import load_dotenv
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

APP_ENV_DEFAULT = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()
DEFAULT_SIPET_DATA_DIR = (os.environ.get("SIPET_DATA_DIR") or os.path.expanduser("~/.sipet/data")).strip()
_REQUEST_HOST: ContextVar[str] = ContextVar("sipet_request_host", default="")
_ENGINE_CACHE: Dict[str, Engine] = {}
_SESSION_FACTORY_CACHE: Dict[str, sessionmaker] = {}


def _normalize_host(value: Optional[str]) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    raw = raw.split("/", 1)[0]
    raw = raw.split(",", 1)[0].strip()
    if ":" in raw and raw.count(":") == 1:
        raw = raw.split(":", 1)[0]
    return raw


def _normalize_dataMAIN_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql://", 1)
    return raw_url


def _resolve_sqlite_path(raw_path: str) -> str:
    candidate = (raw_path or "").strip()
    if not candidate:
        default_name = f"strategic_planning_{APP_ENV_DEFAULT}.db"
        return os.path.join(PROJECT_ROOT, default_name)
    if os.path.isabs(candidate):
        return candidate
    return os.path.abspath(os.path.join(PROJECT_ROOT, candidate))


def _coerce_dataMAIN_target_to_url(target: str) -> str:
    raw = (target or "").strip()
    if not raw:
        raise RuntimeError("Destino de MAIN de datos vacío.")
    if "://" in raw:
        return _normalize_dataMAIN_url(raw)
    sqlite_path = _resolve_sqlite_path(raw)
    return f"sqlite:///{sqlite_path}"


def _resolve_default_dataMAIN_url() -> str:
    raw_url = (
        os.environ.get("DATAMAIN_URL")
        or os.environ.get("POSTGRES_URL")
        or os.environ.get("POSTGRESQL_URL")
        or ""
    ).strip()
    if raw_url:
        return _normalize_dataMAIN_url(raw_url)

    sqlite_db_path = (os.environ.get("SQLITE_DB_PATH") or "").strip()
    if sqlite_db_path:
        return _coerce_dataMAIN_target_to_url(sqlite_db_path)

    is_railway = any(str(value or "").strip() for key, value in os.environ.items() if key.startswith("RAILWAY_"))
    is_prod_like = APP_ENV_DEFAULT in {"production", "prod"} or is_railway
    default_name = f"strategic_planning_{APP_ENV_DEFAULT}.db"
    if is_prod_like:
        fallback_path = os.path.join("/tmp", default_name)
        print(
            "[db] DATAMAIN_URL no configurada en producción/Railway; "
            f"usando fallback SQLite temporal en {fallback_path}."
        )
        return f"sqlite:///{fallback_path}"

    return f"sqlite:///{os.path.join(PROJECT_ROOT, default_name)}"


def _load_host_dataMAIN_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    raw_json = (os.environ.get("HOST_DATAMAIN_MAP_JSON") or "").strip()
    if raw_json:
        try:
            data = json.loads(raw_json)
            if isinstance(data, dict):
                for host, target in data.items():
                    normalized_host = _normalize_host(str(host))
                    normalized_target = str(target or "").strip()
                    if normalized_host and normalized_target:
                        mapping[normalized_host] = normalized_target
        except Exception as exc:
            print(f"[db] No se pudo leer HOST_DATAMAIN_MAP_JSON: {exc}")

    raw_pairs = (os.environ.get("HOST_DATAMAIN_MAP") or "").strip()
    if raw_pairs:
        for chunk in raw_pairs.split(","):
            host, separator, target = chunk.partition("=")
            if not separator:
                continue
            normalized_host = _normalize_host(host)
            normalized_target = str(target or "").strip()
            if normalized_host and normalized_target:
                mapping[normalized_host] = normalized_target

    return mapping


HOST_DATAMAIN_MAP = _load_host_dataMAIN_map()
DATAMAIN_URL = _resolve_default_dataMAIN_url()


def _extract_sqlite_path(db_url: str) -> Optional[str]:
    if not db_url.startswith("sqlite:///"):
        return None
    return db_url.replace("sqlite:///", "", 1).split("?", 1)[0]


def set_request_host(host: Optional[str]):
    return _REQUEST_HOST.set(_normalize_host(host))


def reset_request_host(token) -> None:
    _REQUEST_HOST.reset(token)


def get_request_host() -> str:
    return _REQUEST_HOST.get("")


def get_dataMAIN_url_for_host(host: Optional[str] = None) -> str:
    normalized_host = _normalize_host(host) or get_request_host()
    if normalized_host and normalized_host in HOST_DATAMAIN_MAP:
        return _coerce_dataMAIN_target_to_url(HOST_DATAMAIN_MAP[normalized_host])
    return DATAMAIN_URL


def get_engine_for_host(host: Optional[str] = None) -> Engine:
    db_url = get_dataMAIN_url_for_host(host)
    engine_instance = _ENGINE_CACHE.get(db_url)
    if engine_instance is not None:
        return engine_instance
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite:///") else {}
    engine_instance = create_engine(db_url, connect_args=connect_args, echo=False)
    _ENGINE_CACHE[db_url] = engine_instance
    return engine_instance


def get_session_factory_for_host(host: Optional[str] = None) -> sessionmaker:
    db_url = get_dataMAIN_url_for_host(host)
    session_factory = _SESSION_FACTORY_CACHE.get(db_url)
    if session_factory is not None:
        return session_factory
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=get_engine_for_host(host),
    )
    _SESSION_FACTORY_CACHE[db_url] = session_factory
    return session_factory


def get_current_engine() -> Engine:
    return get_engine_for_host()


def get_current_dataMAIN_info(host: Optional[str] = None) -> Dict[str, str]:
    db_url = get_dataMAIN_url_for_host(host)
    sqlite_path = _extract_sqlite_path(db_url)
    info = {
        "host": _normalize_host(host) or get_request_host() or "",
        "url": db_url,
        "engine": "sqlite" if sqlite_path else "postgresql",
        "path": sqlite_path or "",
        "name": os.path.basename(sqlite_path) if sqlite_path else "postgresql",
    }
    return info


def dispose_engine_for_host(host: Optional[str] = None) -> None:
    db_url = get_dataMAIN_url_for_host(host)
    engine_instance = _ENGINE_CACHE.pop(db_url, None)
    _SESSION_FACTORY_CACHE.pop(db_url, None)
    if engine_instance is not None:
        engine_instance.dispose()


class _DynamicSessionLocal:
    def __call__(self, **kwargs):
        return get_session_factory_for_host()(**kwargs)


engine = get_engine_for_host()
SessionLocal = _DynamicSessionLocal()
MAIN = declarative_base()


class IAInteraction(MAIN):
    __tablename__ = "ia_interactions"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    feature_key = Column(String, nullable=True)
    input_payload = Column(String, nullable=True)
    output_payload = Column(String, nullable=True)
    model_name = Column(String, nullable=True)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    estimated_cost = Column(String, default="0")
    status = Column(String, default="pending")
    error_message = Column(String, default="")


class IAConfig(MAIN):
    __tablename__ = "ia_config"
    id = Column(Integer, primary_key=True, index=True)
    ai_provider = Column(String, nullable=False)
    ai_api_key = Column(String, nullable=False)
    ai_MAIN_url = Column(String, default="")
    ai_model = Column(String, default="")
    ai_timeout = Column(Integer, default=30)
    ai_temperature = Column(Float, default=0.7)
    ai_top_p = Column(Float, default=0.9)
    ai_num_predict = Column(Integer, default=700)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IAFeatureFlag(MAIN):
    __tablename__ = "ia_feature_flags"
    id = Column(Integer, primary_key=True, index=True)
    feature_key = Column(String, nullable=False)
    enabled = Column(Integer, default=1)
    role = Column(String, nullable=True)
    module = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IASuggestionDraft(MAIN):
    __tablename__ = "ia_suggestion_drafts"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    status = Column(String, default="generated")
    target_module = Column(String, default="")
    target_entity = Column(String, default="")
    target_entity_id = Column(String, default="")
    target_field = Column(String, default="")
    prompt_text = Column(Text, default="")
    original_text = Column(Text, default="")
    suggested_text = Column(Text, default="")
    edited_text = Column(Text, default="")
    applied_text = Column(Text, default="")
    discard_reason = Column(Text, default="")
    error_message = Column(Text, default="")
    interaction_id = Column(Integer, default=0)


class IAJob(MAIN):
    __tablename__ = "ia_jobs"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    role = Column(String, nullable=True)
    module = Column(String, default="")
    feature_key = Column(String, default="suggest_objective_text")
    job_type = Column(String, default="suggest_objective_text")
    queue = Column(String, default="default")
    status = Column(String, default="pending")
    progress = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=1)
    input_payload = Column(Text, default="")
    output_payload = Column(Text, default="")
    error_message = Column(Text, default="")
    provider = Column(String, default="")
    model_name = Column(String, default="")


class DepartamentoOrganizacional(MAIN):
    __tablename__ = "organizational_departments"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, default="")
    codigo = Column(String, unique=True, index=True, nullable=False, default="")
    padre = Column(String, default="N/A")
    responsable = Column(String, default="")
    color = Column(String, default="#1d4ed8")
    estado = Column(String, default="Activo")
    orden = Column(Integer, default=0, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RegionOrganizacional(MAIN):
    __tablename__ = "organizational_regions"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, default="")
    codigo = Column(String, unique=True, index=True, nullable=False, default="")
    descripcion = Column(String, default="")
    orden = Column(Integer, default=0, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
