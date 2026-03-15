from __future__ import annotations

import json
from datetime import datetime

from fastapi_modulo.modulos.capacitacion.repositorios import audit_repository as repo

repo.ensure_schema()


def _dt(value):
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def evento_dict(obj):
    detalle = obj.detalle_json
    if isinstance(detalle, str):
        try:
            detalle = json.loads(detalle)
        except (TypeError, ValueError):
            detalle = {"raw": detalle}
    return {
        "id": obj.id,
        "tenant_id": obj.tenant_id,
        "entidad_tipo": obj.entidad_tipo,
        "entidad_id": obj.entidad_id,
        "accion": obj.accion,
        "actor_key": obj.actor_key,
        "actor_nombre": obj.actor_nombre,
        "detalle": detalle or {},
        "creado_en": _dt(obj.creado_en),
    }


def registrar_evento(db, entidad_tipo, entidad_id, accion, *, actor_key=None, actor_nombre=None, detalle=None, tenant_id=None):
    return repo.create_evento(
        db,
        {
            "tenant_id": tenant_id or "default",
            "entidad_tipo": entidad_tipo,
            "entidad_id": entidad_id,
            "accion": accion,
            "actor_key": actor_key,
            "actor_nombre": actor_nombre,
            "detalle_json": detalle or {},
            "creado_en": datetime.utcnow(),
        },
    )


def list_eventos(entidad_tipo, entidad_id):
    db = repo.get_db()
    try:
        return [evento_dict(item) for item in repo.list_eventos(db, entidad_tipo, entidad_id)]
    finally:
        db.close()
