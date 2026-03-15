from __future__ import annotations

from sqlalchemy import text


def ensure_indicator_table_schema(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS brujula_indicator_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id VARCHAR(100) NOT NULL DEFAULT 'default',
                indicador VARCHAR(255) NOT NULL DEFAULT '',
                valores_json TEXT NOT NULL DEFAULT '{}',
                orden INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    try:
        cols = db.execute(text("PRAGMA table_info(brujula_indicator_values)")).fetchall()
        col_names = {str(col[1]).strip().lower() for col in cols if len(col) > 1}
        if "tenant_id" not in col_names:
            db.execute(text("ALTER TABLE brujula_indicator_values ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'"))
        db.execute(text("UPDATE brujula_indicator_values SET tenant_id = 'default' WHERE tenant_id IS NULL OR tenant_id = ''"))
        db.execute(text("DROP INDEX IF EXISTS ux_brujula_indicator_values_indicador"))
        db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_brujula_indicator_values_tenant_indicador ON brujula_indicator_values(tenant_id, indicador)"))
    except Exception:
        pass


def ensure_override_table_schema(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS brujula_indicator_definition_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id VARCHAR(100) NOT NULL DEFAULT 'default',
                indicador VARCHAR(255) NOT NULL DEFAULT '',
                estandar_meta TEXT NOT NULL DEFAULT '',
                semaforo_rojo TEXT NOT NULL DEFAULT '',
                semaforo_verde TEXT NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    try:
        cols = db.execute(text("PRAGMA table_info(brujula_indicator_definition_overrides)")).fetchall()
        col_names = {str(col[1]).strip().lower() for col in cols if len(col) > 1}
        if "tenant_id" not in col_names:
            db.execute(text("ALTER TABLE brujula_indicator_definition_overrides ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'"))
        db.execute(text("UPDATE brujula_indicator_definition_overrides SET tenant_id = 'default' WHERE tenant_id IS NULL OR tenant_id = ''"))
        db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_brujula_indicator_definition_overrides_tenant_indicador ON brujula_indicator_definition_overrides(tenant_id, indicador)"))
    except Exception:
        pass
