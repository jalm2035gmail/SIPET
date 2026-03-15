from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import database_exists, create_database
from apps.products.models import Product  # importa todos los modelos que quieras migrar
# ... importa más modelos según tu estructura ...

Base = declarative_base()

# Configuración base de conexión (ajusta con tus credenciales)
DB_URL = "postgresql+psycopg2://user:password@localhost:5432/tu_db"


def get_engine_for_store(store_slug: str):
    engine = create_engine(
        DB_URL,
        connect_args={"options": f"-c search_path={store_slug},public"}
    )
    return engine


def create_store_schema_and_migrate(store_slug: str):
    """
    Crea el schema para la tienda y migra los modelos (crea tablas en ese schema).
    """
    engine = create_engine(DB_URL)
    # 1. Crear el schema si no existe
    with engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{store_slug}"'))
    # 2. Migrar modelos (crear tablas) en el nuevo schema
    store_engine = get_engine_for_store(store_slug)
    Base.metadata.create_all(store_engine)
    # Si tienes modelos fuera de Base, crea sus tablas manualmente aquí
    # Product.__table__.create(bind=store_engine, checkfirst=True)
    # ...
    return True


def get_session_for_store(store_slug: str):
    engine = get_engine_for_store(store_slug)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()
