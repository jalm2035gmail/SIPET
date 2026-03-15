from __future__ import annotations

import uuid
from datetime import datetime

from fastapi_modulo.modulos.capacitacion.modelos.db_models import CapCertificado
from fastapi_modulo.modulos.capacitacion.repositorios import evaluaciones_repository as repo
from fastapi_modulo.modulos.capacitacion.servicios.audit_service import registrar_evento


def _dt(value):
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def cert_dict(obj: CapCertificado):
    insc = obj.inscripcion
    return {
        "id": obj.id,
        "folio": obj.folio,
        "puntaje_final": obj.puntaje_final,
        "creado_por": obj.creado_por,
        "fecha_emision": _dt(obj.fecha_emision),
        "url_pdf": obj.url_pdf,
        "inscripcion_id": obj.inscripcion_id,
        "colaborador_key": insc.colaborador_key if insc else None,
        "colaborador_nombre": insc.colaborador_nombre if insc else None,
        "curso_id": insc.curso_id if insc else None,
        "curso_nombre": insc.curso.nombre if insc and insc.curso else None,
    }


def emitir_certificado(db, insc, puntaje, actor_key=None, actor_name=None, tenant_id=None):
    if insc.certificado:
        return insc.certificado
    if not getattr(insc, "aprobado", False):
        raise ValueError("La inscripción debe estar aprobada para emitir certificado")
    if float(getattr(insc, "pct_avance", 0) or 0) < 100:
        raise ValueError("La inscripción debe completar el 100% del curso para emitir certificado")
    if insc.curso and getattr(insc.curso, "bloquear_certificado_encuesta", False) and not getattr(insc, "satisfaccion", None):
        raise ValueError("Debe completar la encuesta de satisfaccion para emitir certificado")
    certificado = repo.create_certificado(db, {"inscripcion_id": insc.id, "folio": uuid.uuid4().hex[:12].upper(), "puntaje_final": puntaje, "creado_por": actor_key, "fecha_emision": datetime.utcnow(), "tenant_id": tenant_id or getattr(insc, "tenant_id", "default")})
    registrar_evento(db, "certificado", certificado.id, "issued", actor_key=actor_key, actor_nombre=actor_name, tenant_id=certificado.tenant_id, detalle={"inscripcion_id": insc.id, "curso_id": insc.curso_id, "folio": certificado.folio})
    return certificado


def get_certificado(cert_id, tenant_id=None):
    db = repo.get_db()
    try:
        obj = repo.get_certificado(db, cert_id)
        return cert_dict(obj) if obj else None
    finally:
        db.close()


def get_certificado_por_folio(folio, tenant_id=None):
    db = repo.get_db()
    try:
        obj = repo.get_certificado_por_folio(db, folio)
        return cert_dict(obj) if obj else None
    finally:
        db.close()


def get_certificados_colaborador(colaborador_key, tenant_id=None):
    db = repo.get_db()
    try:
        result = []
        for insc in repo.list_inscripciones_con_certificado(db, colaborador_key):
            if insc.certificado:
                result.append(cert_dict(insc.certificado))
        return result
    finally:
        db.close()
