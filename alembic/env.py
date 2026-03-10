from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

database_url_from_env = (os.environ.get("DATABASE_URL") or "").strip()
if database_url_from_env.startswith("postgres://"):
    database_url_from_env = database_url_from_env.replace("postgres://", "postgresql://", 1)
if database_url_from_env:
    config.set_main_option("sqlalchemy.url", database_url_from_env)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# append the backend app package to sys.path so alembic can import it
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# add your model's MetaData object here
# for 'autogenerate' support
BACKEND_DIR = os.path.join(PROJECT_DIR, "strategic_planning", "backend")
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.models.base import Base

# Registrar modelos del módulo de capacitación para soporte de autogenerate
sys.path.insert(0, PROJECT_DIR)
try:
    import fastapi_modulo.modulos.capacitacion.cap_db_models  # noqa: F401
except Exception:
    pass

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
