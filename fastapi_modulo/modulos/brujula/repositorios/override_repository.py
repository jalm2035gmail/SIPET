from __future__ import annotations

from sqlalchemy import text
from fastapi_modulo.modulos.brujula.repositorios.tenant_repository import require_tenant_id


def load_overrides(db, tenant_id: str) -> dict[str, dict[str, str]]:
    tenant_id = require_tenant_id(tenant_id)
    rows = db.execute(
        text(
            """
            SELECT indicador, estandar_meta, semaforo_rojo, semaforo_verde
            FROM brujula_indicator_definition_overrides
            WHERE tenant_id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id},
    ).fetchall()
    output: dict[str, dict[str, str]] = {}
    for row in rows:
        indicador = str(row[0] or "").strip().lower()
        if not indicador:
            continue
        output[indicador] = {
            "estandar_meta": str(row[1] or "").strip(),
            "semaforo_rojo": str(row[2] or "").strip(),
            "semaforo_verde": str(row[3] or "").strip(),
        }
    return output


def upsert_override(
    db,
    tenant_id: str,
    indicador: str,
    estandar_meta: str,
    semaforo_rojo: str,
    semaforo_verde: str,
) -> None:
    tenant_id = require_tenant_id(tenant_id)
    db.execute(
        text(
            """
            INSERT INTO brujula_indicator_definition_overrides (
                tenant_id, indicador, estandar_meta, semaforo_rojo, semaforo_verde, updated_at
            )
            VALUES (
                :tenant_id, :indicador, :estandar_meta, :semaforo_rojo, :semaforo_verde, CURRENT_TIMESTAMP
            )
            ON CONFLICT(tenant_id, indicador) DO UPDATE SET
                estandar_meta = excluded.estandar_meta,
                semaforo_rojo = excluded.semaforo_rojo,
                semaforo_verde = excluded.semaforo_verde,
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "tenant_id": tenant_id,
            "indicador": indicador,
            "estandar_meta": estandar_meta,
            "semaforo_rojo": semaforo_rojo,
            "semaforo_verde": semaforo_verde,
        },
    )
