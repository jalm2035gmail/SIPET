import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float
from datetime import datetime

def _resolve_database_url() -> str:
    raw_url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
        or os.environ.get("POSTGRESQL_URL")
        or ""
    ).strip()
    if raw_url:
        if raw_url.startswith("postgres://"):
            return raw_url.replace("postgres://", "postgresql://", 1)
        return raw_url
    app_env = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()
    is_railway = any(str(value or "").strip() for key, value in os.environ.items() if key.startswith("RAILWAY_"))
    is_prod_like = app_env in {"production", "prod"} or is_railway
    default_sqlite_name = f"strategic_planning_{app_env}.db"
    sqlite_db_path = (os.environ.get("SQLITE_DB_PATH") or "").strip()
    if not sqlite_db_path and is_prod_like:
        # Railway puede iniciar sin DATABASE_URL si el servicio aún no tiene una BD adjunta.
        # Preferimos degradar a SQLite local para que el contenedor abra el puerto y exponga /health.
        sqlite_db_path = os.path.join("/tmp", default_sqlite_name)
        print(
            "[db] DATABASE_URL no configurada en producción/Railway; "
            f"usando fallback SQLite temporal en {sqlite_db_path}."
        )
    if sqlite_db_path and os.path.basename(sqlite_db_path).lower() == "strategic_planning.db" and not is_prod_like:
        sqlite_db_path = default_sqlite_name
    if not sqlite_db_path:
        # Compatibilidad: prioriza la BD local del proyecto si ya existe.
        # Evita "desaparición" de datos cuando se migra implícitamente a ~/.sipet/data.
        project_candidate = os.path.abspath(default_sqlite_name)
        legacy_project_candidate = os.path.abspath("strategic_planning.db")
        if os.path.exists(project_candidate):
            sqlite_db_path = project_candidate
        elif os.path.exists(legacy_project_candidate):
            sqlite_db_path = legacy_project_candidate
    data_dir = (os.environ.get("SIPET_DATA_DIR") or os.path.expanduser("~/.sipet/data")).strip()
    if not sqlite_db_path:
        os.makedirs(data_dir, exist_ok=True)
        sqlite_db_path = os.path.join(data_dir, default_sqlite_name)
    elif not os.path.isabs(sqlite_db_path):
        os.makedirs(data_dir, exist_ok=True)
        sqlite_db_path = os.path.join(data_dir, sqlite_db_path)
    if os.path.isabs(sqlite_db_path):
        return f"sqlite:///{sqlite_db_path}"
    return f"sqlite:///./{sqlite_db_path}"


DATABASE_URL = _resolve_database_url()
CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite:///") else {}

# Engine y SessionLocal
engine = create_engine(DATABASE_URL, connect_args=CONNECT_ARGS, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modelo DepartamentoOrganizacional
from sqlalchemy.orm import declarative_base
Base = declarative_base()

class IAInteraction(Base):
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

class IAConfig(Base):
    __tablename__ = "ia_config"
    id = Column(Integer, primary_key=True, index=True)
    ai_provider = Column(String, nullable=False)
    ai_api_key = Column(String, nullable=False)
    ai_base_url = Column(String, default="")
    ai_model = Column(String, default="")
    ai_timeout = Column(Integer, default=30)
    ai_temperature = Column(Float, default=0.7)
    ai_top_p = Column(Float, default=0.9)
    ai_num_predict = Column(Integer, default=700)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class IAFeatureFlag(Base):
    __tablename__ = "ia_feature_flags"
    id = Column(Integer, primary_key=True, index=True)
    feature_key = Column(String, nullable=False)
    enabled = Column(Integer, default=1)  # 1=habilitado, 0=deshabilitado
    role = Column(String, nullable=True)  # Si es None, aplica global
    module = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class IASuggestionDraft(Base):
    __tablename__ = "ia_suggestion_drafts"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    status = Column(String, default="generated")  # generated | applied | discarded | error
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

class IAJob(Base):
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
    status = Column(String, default="pending")  # pending | in_progress | completed | error | canceled
    progress = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=1)
    input_payload = Column(Text, default="")
    output_payload = Column(Text, default="")
    error_message = Column(Text, default="")
    provider = Column(String, default="")
    model_name = Column(String, default="")

class DepartamentoOrganizacional(Base):
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


class RegionOrganizacional(Base):
    __tablename__ = "organizational_regions"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, default="")
    codigo = Column(String, unique=True, index=True, nullable=False, default="")
    descripcion = Column(String, default="")
    orden = Column(Integer, default=0, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
