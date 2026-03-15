from __future__ import annotations

import json

from sqlalchemy import text
from fastapi_modulo.modulos.brujula.repositorios.tenant_repository import require_tenant_id


def list_indicator_rows(db, tenant_id: str) -> list[dict]:
    tenant_id = require_tenant_id(tenant_id)
    rows = db.execute(
        text(
            """
            SELECT indicador, valores_json, orden
            FROM brujula_indicator_values
            WHERE tenant_id = :tenant_id
            ORDER BY orden ASC, id ASC
            """
        ),
        {"tenant_id": tenant_id},
    ).fetchall()
    output = []
    seen = set()
    for row in rows:
        indicador = str(row[0] or "").strip()
        if not indicador:
            continue
        try:
            values = json.loads(str(row[1] or "{}"))
        except Exception:
            values = {}
        key = indicador.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append({"indicador": indicador, "values": values, "orden": int(row[2] or 0)})
    return output


def replace_indicator_rows(db, tenant_id: str, rows: list[dict]) -> None:
    tenant_id = require_tenant_id(tenant_id)
    db.execute(text("DELETE FROM brujula_indicator_values WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
    for row in rows:
        db.execute(
            text(
                """
                INSERT INTO brujula_indicator_values (tenant_id, indicador, valores_json, orden, updated_at)
                VALUES (:tenant_id, :indicador, :valores_json, :orden, CURRENT_TIMESTAMP)
                """
            ),
            {
                "tenant_id": tenant_id,
                "indicador": row["indicador"],
                "valores_json": json.dumps(row["values"], ensure_ascii=False),
                "orden": int(row["orden"]),
            },
        )
