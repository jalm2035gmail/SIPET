from fastapi import APIRouter, HTTPException
from fastapi_modulo.modulos.auditoria.modelos.aud_store import (
    update_auditoria, get_auditoria, update_hallazgo, get_hallazgo, update_recomendacion, get_recomendacion, get_aud_resumen
)

router = APIRouter()

@router.post("/auditoria/{auditoria_id}/cerrar")
def cerrar_auditoria(auditoria_id: int):
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    return update_auditoria(auditoria_id, {"estado": "cerrada"})

@router.post("/auditoria/{auditoria_id}/reabrir")
def reabrir_auditoria(auditoria_id: int):
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    return update_auditoria(auditoria_id, {"estado": "en_proceso"})

@router.post("/hallazgo/{hallazgo_id}/cambiar_estado")
def cambiar_estado_hallazgo(hallazgo_id: int, estado: str):
    hallazgo = get_hallazgo(hallazgo_id)
    if not hallazgo:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")
    return update_hallazgo(hallazgo_id, {"estado": estado})

@router.post("/recomendacion/{rec_id}/implementar")
def implementar_recomendacion(rec_id: int):
    rec = get_recomendacion(rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recomendación no encontrada")
    return update_recomendacion(rec_id, {"estado": "implementada", "porcentaje_avance": 100})

@router.post("/recomendacion/{rec_id}/verificar")
def verificar_recomendacion(rec_id: int):
    rec = get_recomendacion(rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recomendación no encontrada")
    return update_recomendacion(rec_id, {"estado": "verificada"})

@router.get("/dashboard/area")
def dashboard_area():
    resumen = get_aud_resumen()
    return resumen.get("hallazgos_por_area", {})

@router.get("/dashboard/responsable")
def dashboard_responsable():
    resumen = get_aud_resumen()
    return resumen.get("recomendaciones_por_responsable", {})

# Endpoints para exportar a PDF/Excel y plan de acción pueden agregarse según la infraestructura disponible.
