from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from fastapi_modulo.modulos.control_interno.repositorios.base import session_scope
from fastapi_modulo.modulos.control_interno.servicios import (
    controles_service,
    evidencia_service,
    hallazgo_service,
    programa_service,
    reporte_service,
    tablero_service,
)
from fastapi_modulo.modulos.control_interno.controladores.dependencies import save_uploaded_evidence


def _crear_control(**overrides):
    payload = {
        "codigo": "CI-001",
        "nombre": "Control de conciliacion",
        "componente": "Monitoreo",
        "area": "Finanzas",
        "periodicidad": "Mensual",
        "estado": "Activo",
    }
    payload.update(overrides)
    return controles_service.crear(payload)


def _crear_programa(**overrides):
    payload = {
        "anio": 2026,
        "nombre": "Programa anual 2026",
        "descripcion": "Plan base",
        "estado": "Borrador",
    }
    payload.update(overrides)
    return programa_service.crear_programa_service(payload)


def _crear_actividad(programa_id: int, **overrides):
    payload = {
        "descripcion": "Revisar conciliaciones",
        "responsable": "Ana",
        "fecha_inicio_programada": "2026-01-10",
        "fecha_fin_programada": "2026-01-20",
        "estado": "Programado",
    }
    payload.update(overrides)
    return programa_service.crear_actividad_service(programa_id, payload)


def _crear_evidencia(**overrides):
    payload = {
        "titulo": "Acta de revision",
        "tipo": "Documento",
        "fecha_evidencia": "2026-01-15",
        "resultado_evaluacion": "Cumple",
    }
    payload.update(overrides)
    return evidencia_service.crear_service(payload)


def _crear_hallazgo(**overrides):
    payload = {
        "codigo": "HZ-001",
        "titulo": "Diferencia de conciliacion",
        "nivel_riesgo": "Medio",
        "estado": "Abierto",
        "fecha_deteccion": "2026-02-01",
        "fecha_limite": "2026-02-15",
        "responsable": "Carlos",
    }
    payload.update(overrides)
    return hallazgo_service.crear_service(payload)


def _crear_accion(hallazgo_id: int, **overrides):
    payload = {
        "descripcion": "Regularizar diferencias",
        "responsable": "Carlos",
        "fecha_compromiso": "2026-02-10",
        "estado": "Pendiente",
    }
    payload.update(overrides)
    return hallazgo_service.crear_accion_service(hallazgo_id, payload)


def test_crud_controles():
    creado = _crear_control(nombre="  Control maestro  ", codigo="ci-900")

    assert creado["codigo"] == "CI-900"
    assert creado["nombre"] == "Control maestro"

    listado = controles_service.listar(q="maestro")
    assert [item["id"] for item in listado] == [creado["id"]]

    actualizado = controles_service.actualizar(creado["id"], {"estado": "Inactivo", "area": "Tesoreria"})
    assert actualizado["estado"] == "Inactivo"
    assert actualizado["area"] == "Tesoreria"

    opciones = controles_service.opciones()
    assert "Monitoreo" in opciones["componentes"]
    assert "Tesoreria" in opciones["areas"]

    assert controles_service.eliminar(creado["id"]) is True
    assert controles_service.obtener(creado["id"]) is None


def test_crud_programas_actividades_y_validacion_fechas():
    programa = _crear_programa()

    with pytest.raises(HTTPException) as excinfo:
        programa_service.actualizar_programa_service(programa["id"], {"estado": "Aprobado"})
    assert "sin actividades" in excinfo.value.detail

    actividad = _crear_actividad(programa["id"])
    resumen = programa_service.resumen_programa_service(programa["id"])
    assert resumen["total"] == 1
    assert resumen["conteo"]["Programado"] == 1

    aprobado = programa_service.actualizar_programa_service(programa["id"], {"estado": "Aprobado"})
    assert aprobado["estado"] == "Aprobado"

    with pytest.raises(HTTPException) as excinfo:
        _crear_actividad(
            programa["id"],
            fecha_inicio_programada="2026-03-10",
            fecha_fin_programada="2026-03-05",
        )
    assert "fecha fin programada" in excinfo.value.detail

    with pytest.raises(HTTPException) as excinfo:
        programa_service.actualizar_actividad_service(actividad["id"], {"estado": "Completado"})
    assert "fecha real de cierre" in excinfo.value.detail

    cerrada = programa_service.actualizar_actividad_service(
        actividad["id"],
        {"estado": "Completado", "fecha_fin_real": "2026-01-22"},
    )
    assert cerrada["estado"] == "Completado"
    assert cerrada["fecha_fin_real"] == "2026-01-22"

    assert programa_service.eliminar_actividad_service(actividad["id"]) is True
    assert programa_service.eliminar_programa_service(programa["id"]) is True


def test_carga_evidencia_archivo_valido_e_invalido_y_seguridad_descarga(tmp_path, models):
    valido = UploadFile(filename="evidencia.pdf", file=BytesIO(b"%PDF-1.4 prueba"))
    valido.headers = {"content-type": "application/pdf"}
    meta = asyncio.run(save_uploaded_evidence(valido))

    assert Path(meta["archivo_ruta"]).exists()
    assert meta["archivo_extension"] == ".pdf"

    evidencia = evidencia_service.crear_service(
        {
            "titulo": "PDF valido",
            "tipo": "Documento",
            "resultado_evaluacion": "Cumple",
        },
        **meta,
    )
    assert evidencia["tiene_archivo"] is True
    assert evidencia_service.obtener_ruta_archivo_service(evidencia["id"]) == meta["archivo_ruta"]

    invalido = UploadFile(filename="script.exe", file=BytesIO(b"MZ"))
    invalido.headers = {"content-type": "application/octet-stream"}
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(save_uploaded_evidence(invalido))
    assert "Extension de archivo no permitida" in excinfo.value.detail

    with pytest.raises(HTTPException) as excinfo:
        evidencia_service.crear_service(
            {"titulo": "Insegura", "tipo": "Documento"},
            archivo_ruta=str(tmp_path / "fuera.pdf"),
            archivo_uuid="uuid",
            archivo_extension=".pdf",
        )
    assert "ruta del archivo no es valida" in excinfo.value.detail

    with session_scope() as db:
        item = db.get(models["evidencia"], evidencia["id"])
        item.archivo_ruta = str(tmp_path / "fuera-del-root.pdf")
        db.flush()

    assert evidencia_service.obtener_ruta_archivo_service(evidencia["id"]) is None

    control = _crear_control(codigo="CI-AUTO")
    programa = _crear_programa(anio=2030, nombre="Programa auto")
    actividad = _crear_actividad(programa["id"], control_id=control["id"])
    vinculada = evidencia_service.crear_service(
        {
            "titulo": "Ligada automaticamente",
            "tipo": "Documento",
            "actividad_id": actividad["id"],
            "resultado_evaluacion": "Cumple",
        }
    )
    assert vinculada["actividad_id"] == actividad["id"]
    assert vinculada["control_id"] == control["id"]


def test_crud_hallazgos_acciones_y_validaciones():
    evidencia = _crear_evidencia(resultado_evaluacion="Por evaluar")
    with pytest.raises(HTTPException) as excinfo:
        _crear_hallazgo(evidencia_id=evidencia["id"])
    assert "pendiente de evaluacion" in excinfo.value.detail

    with pytest.raises(HTTPException) as excinfo:
        _crear_hallazgo(
            codigo="HZ-CRIT",
            nivel_riesgo="Crítico",
            responsable="",
            fecha_limite=None,
        )
    assert "hallazgo critico requiere responsable" in excinfo.value.detail

    hallazgo = _crear_hallazgo(codigo="HZ-002")

    with pytest.raises(HTTPException) as excinfo:
        hallazgo_service.actualizar_service(hallazgo["id"], {"estado": "Cerrado"})
    assert "accion verificada" in excinfo.value.detail

    accion = _crear_accion(hallazgo["id"])
    with pytest.raises(HTTPException) as excinfo:
        hallazgo_service.actualizar_accion_service(accion["id"], {"estado": "Verificada"})
    assert "sin evidencia de seguimiento" in excinfo.value.detail

    accion_ok = hallazgo_service.actualizar_accion_service(
        accion["id"],
        {"estado": "Ejecutada", "fecha_ejecucion": "2026-02-09", "evidencia_seguimiento": "Ticket cerrado"},
    )
    assert accion_ok["estado"] == "Ejecutada"

    with pytest.raises(HTTPException) as excinfo:
        hallazgo_service.actualizar_service(hallazgo["id"], {"estado": "Cerrado"})
    assert "accion verificada" in excinfo.value.detail

    verificada = hallazgo_service.actualizar_accion_service(
        accion["id"],
        {"estado": "Verificada", "evidencia_seguimiento": "Validado por auditoria"},
    )
    assert verificada["estado"] == "Verificada"

    cerrado = hallazgo_service.actualizar_service(hallazgo["id"], {"estado": "Cerrado"})
    assert cerrado["estado"] == "Cerrado"
    assert cerrado["acciones"][0]["estado"] == "Verificada"

    evidencia_ok = _crear_evidencia(resultado_evaluacion="Cumple")
    hallazgo_auto = _crear_hallazgo(codigo="HZ-AUTO", evidencia_id=evidencia_ok["id"])
    assert hallazgo_auto["evidencia_id"] == evidencia_ok["id"]
    assert hallazgo_auto["control_id"] == evidencia_ok["control_id"]
    assert hallazgo_auto["actividad_id"] == evidencia_ok["actividad_id"]

    assert hallazgo_service.eliminar_accion_service(accion["id"]) is True
    assert hallazgo_service.eliminar_service(hallazgo["id"]) is True


def test_reportes_exportacion_y_kpis_tablero():
    control = _crear_control(codigo="CI-777", componente="Actividades de control", area="Compras")
    programa = _crear_programa()
    actividad = _crear_actividad(
        programa["id"],
        control_id=control["id"],
        estado="Completado",
        fecha_fin_real="2026-01-18",
    )
    evidencia = _crear_evidencia(
        control_id=control["id"],
        actividad_id=actividad["id"],
        resultado_evaluacion="Cumple",
        fecha_evidencia="2026-01-18",
    )
    hallazgo = _crear_hallazgo(
        codigo="HZ-777",
        control_id=control["id"],
        componente_coso="Actividades de control",
        nivel_riesgo="Alto",
        estado="En atencion",
    )
    _crear_accion(
        hallazgo["id"],
        estado="En proceso",
        fecha_compromiso="2026-02-20",
    )

    datos = reporte_service.datos_reporte_service(
        tipo="completo",
        control_id=control["id"],
        componente_coso="Actividades de control",
        resultado_ev="Cumple",
        fecha_desde="2026-01-01",
        fecha_hasta="2026-12-31",
        version="detallada",
    )
    assert len(datos["controles"]) == 1
    assert len(datos["actividades"]) == 1
    assert len(datos["evidencias"]) == 1
    assert len(datos["hallazgos"]) == 1
    assert "Control: 1" in datos["filtros_texto"]

    excel, excel_type, excel_name = reporte_service.exportar_excel_service(datos)
    html = reporte_service.exportar_html_service(datos, printable=False)
    pdf, pdf_type, pdf_name = reporte_service.exportar_pdf_service(datos)
    assert excel[:2] == b"PK"
    assert excel_type.endswith("sheet")
    assert excel_name.endswith(".xlsx")
    assert "<html" in html.lower()
    assert pdf.startswith(b"%PDF-")
    assert pdf_type == "application/pdf"
    assert pdf_name.endswith(".pdf")

    kpi_controles = tablero_service.kpi_controles_service()
    kpi_programa = tablero_service.kpi_programa_service()
    kpi_evidencias = tablero_service.kpi_evidencias_service()
    kpi_hallazgos = tablero_service.kpi_hallazgos_service()
    resumen_area = tablero_service.resumen_global_service(area="Compras", fecha_desde="2026-01-01", fecha_hasta="2026-12-31")

    assert kpi_controles["total"] == 1
    assert kpi_programa["total_actividades"] == 1
    assert kpi_evidencias["cumple"] == 1
    assert kpi_hallazgos["altos"] == 1
    assert resumen_area["meta"]["filtros"]["area"] == "Compras"
    assert resumen_area["controles"]["cumplimiento_por_componente"]["Actividades de control"]["semaforo"] in {"verde", "amarillo", "rojo"}


def test_cascada_de_borrado(models):
    control = _crear_control(codigo="CI-444")
    programa = _crear_programa(anio=2027, nombre="Programa 2027")
    actividad = _crear_actividad(programa["id"], control_id=control["id"])
    evidencia = _crear_evidencia(control_id=control["id"], actividad_id=actividad["id"])
    hallazgo = _crear_hallazgo(control_id=control["id"], actividad_id=actividad["id"])
    accion = _crear_accion(hallazgo["id"])

    assert programa_service.eliminar_programa_service(programa["id"]) is True
    assert programa_service.obtener_actividad_service(actividad["id"]) is None

    hallazgo_2 = _crear_hallazgo(codigo="HZ-445")
    accion_2 = _crear_accion(hallazgo_2["id"])
    assert hallazgo_service.eliminar_service(hallazgo_2["id"]) is True
    assert hallazgo_service.listar_acciones_service(hallazgo_2["id"]) == []

    control_2 = _crear_control(codigo="CI-445")
    programa_2 = _crear_programa(anio=2028, nombre="Programa 2028")
    actividad_2 = _crear_actividad(programa_2["id"], control_id=control_2["id"])
    evidencia_2 = _crear_evidencia(control_id=control_2["id"], actividad_id=actividad_2["id"])
    hallazgo_3 = _crear_hallazgo(codigo="HZ-446", control_id=control_2["id"], actividad_id=actividad_2["id"])

    assert controles_service.eliminar(control_2["id"]) is True

    with session_scope() as db:
        actividad_row = db.get(models["actividad"], actividad_2["id"])
        evidencia_row = db.get(models["evidencia"], evidencia_2["id"])
        hallazgo_row = db.get(models["hallazgo"], hallazgo_3["id"])

        assert actividad_row.control_id is None
        assert evidencia_row.control_id is None
        assert hallazgo_row.control_id is None

    assert evidencia_service.obtener_service(evidencia["id"])["actividad_id"] is None
    assert hallazgo_service.obtener_service(hallazgo["id"])["actividad_id"] is None
    assert hallazgo_service.obtener_service(hallazgo["id"])["control_id"] == control["id"]
    assert hallazgo_service.obtener_service(hallazgo["id"])["total_acciones"] == 1
    assert hallazgo_service.obtener_service(hallazgo["id"])["acciones"][0]["id"] == accion["id"]
    assert evidencia_service.obtener_service(evidencia["id"])["control_id"] == control["id"]
    assert evidencia_service.obtener_service(evidencia["id"])["id"] == evidencia["id"]
