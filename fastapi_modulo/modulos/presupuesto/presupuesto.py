from __future__ import annotations

from datetime import datetime, timedelta
from html import escape
from io import StringIO
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict
import sqlite3
import threading
import unicodedata
import re
import json

import pandas as pd
from fastapi import APIRouter, Request, UploadFile, File, Body
from fastapi.responses import HTMLResponse, Response, JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.login_utils import get_login_identity_context

router = APIRouter()
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PRESUPUESTO_TXT_PATH = PROJECT_ROOT / "presupuesto.txt"
CONTROL_MENSUAL_STORE_PATH = PROJECT_ROOT / "fastapi_modulo" / "modulos" / "presupuesto" / "control_mensual_store.json"


def _normalize_rubro_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper()
    text = " ".join(text.replace(".", " ").replace(",", " ").split())
    return text


def _normalize_import_col(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


def _normalize_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


RUBRO_TIPO_MAP = {
    _normalize_rubro_key("INT NORMAL VIGENTE"): "Ingreso",
    _normalize_rubro_key("INT NORMAL VENCIDO"): "Ingreso",
    _normalize_rubro_key("GASTOS POR INTERESES"): "Egreso",
    _normalize_rubro_key("ESTIMACION PREV. P."): "Egreso",
    _normalize_rubro_key("OTROS INGRESOS"): "Ingreso",
    _normalize_rubro_key("INT MORATORIO VIGENTE"): "Ingreso",
    _normalize_rubro_key("INT MORATORIO VENCIDO"): "Ingreso",
    _normalize_rubro_key("INTERESES DE DISPONIBILIDADES"): "Ingreso",
    _normalize_rubro_key("INTERESES DE INVERSIONES"): "Ingreso",
    _normalize_rubro_key("OTROS PRODUCTOS"): "Ingreso",
    _normalize_rubro_key("COMISIONES Y TARIFAS COBRADAS"): "Ingreso",
    _normalize_rubro_key("COMISIONES Y TARIFAS PAGADAS"): "Egreso",
    _normalize_rubro_key("SALARIOS"): "Egreso",
    _normalize_rubro_key("AGUINALDO"): "Egreso",
    _normalize_rubro_key("GRATIFICACIONES"): "Egreso",
    _normalize_rubro_key("PRESTACIONES"): "Egreso",
    _normalize_rubro_key("HONORARIOS"): "Egreso",
    _normalize_rubro_key("GASTOS DE PROMOCION Y PUBLICIDAD"): "Egreso",
    _normalize_rubro_key("APORTACIONES AL FONDO DE PROTECCION"): "Egreso",
    _normalize_rubro_key("IMPUESTOS Y DERECHOS DIVERSOS"): "Egreso",
    _normalize_rubro_key("GASTOS NO DEDUCIBLES"): "Egreso",
    _normalize_rubro_key("GASTOS EN TECNOLOGIA"): "Egreso",
    _normalize_rubro_key("DEPRECIACIONES"): "Egreso",
    _normalize_rubro_key("AMORTIZACIONES"): "Egreso",
    _normalize_rubro_key("COSTO NETO DEL PERIODO"): "Egreso",
    _normalize_rubro_key("OTROS GASTOS DE ADMINISTRACION Y PROMOCION"): "Egreso",
    _normalize_rubro_key("OPERACIONES DISCONTINUAS"): "Egreso",
    _normalize_rubro_key("UTILIDAD O PERDIDA"): "",
}


def _resolve_tipo(rubro: str) -> str:
    return RUBRO_TIPO_MAP.get(_normalize_rubro_key(rubro), "")


def _get_colores_context() -> dict:
    from fastapi_modulo.main import get_colores_context
    return get_colores_context()


def _load_presupuesto_dataframe() -> pd.DataFrame:
    if not PRESUPUESTO_TXT_PATH.exists():
        return pd.DataFrame(columns=["cod", "tipo", "rubro", "monto", "mensual"])
    df = pd.read_csv(
        PRESUPUESTO_TXT_PATH,
        sep="\t",
        header=None,
        names=["cod", "rubro", "monto"],
        dtype=str,
        engine="python",
        keep_default_na=False,
        on_bad_lines="skip",
    )
    for col in ["cod", "rubro", "monto"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df = df[(df["cod"] != "") | (df["rubro"] != "") | (df["monto"] != "")].copy()
    df["tipo"] = df["rubro"].map(_resolve_tipo)
    df["rubro"] = df["rubro"].str.capitalize()
    monto_num = pd.to_numeric(df["monto"].str.replace(",", "", regex=False), errors="coerce")
    df["monto"] = monto_num.map(lambda val: f"{int(round(val)):,}" if pd.notna(val) else "").where(
        monto_num.notna(), df["monto"]
    )
    df["mensual"] = monto_num.div(12).map(lambda val: f"{int(round(val)):,}" if pd.notna(val) else "")
    return df[["cod", "tipo", "rubro", "monto", "mensual"]]


def _control_mensual_header_html() -> str:
    meses = [
        ("01", "Ene"),
        ("02", "Feb"),
        ("03", "Mar"),
        ("04", "Abr"),
        ("05", "May"),
        ("06", "Jun"),
        ("07", "Jul"),
        ("08", "Ago"),
        ("09", "Sep"),
        ("10", "Oct"),
        ("11", "Nov"),
        ("12", "Dic"),
    ]
    top = "".join(
        (
            f'<th colspan="3" class="month-group-head month-{numero}">'
            f'<button type="button" class="month-toggle-btn" data-month-toggle="{numero}" aria-label="Mostrar u ocultar {nombre}">▾</button>'
            f"{nombre}<span hidden class=\"mes-num-hidden\">{numero}</span></th>"
        )
        for numero, nombre in meses
    )
    bottom = "".join(
        (
            f'<th class="tabla-oficial-num month-col month-{numero}" data-month-col="{numero}">Proyectado</th>'
            f'<th class="tabla-oficial-num month-col month-{numero}" data-month-col="{numero}">Realizado</th>'
            f'<th class="tabla-oficial-num month-col month-{numero} month-percent-col" data-month-col="{numero}">%</th>'
        )
        for numero, _ in meses
    )
    return top, bottom


def _control_mensual_rows_html(df: pd.DataFrame) -> str:
    meses = [f"{i:02d}" for i in range(1, 13)]
    rows = []
    for idx, row in enumerate(df.itertuples(index=False), start=1):
        rubro = escape(str(getattr(row, "rubro", "") or ""))
        celdas = []
        for mes in meses:
            celdas.append(
                f'<td class="tabla-oficial-num month-col month-{mes}" data-month-col="{mes}"><input class="tabla-oficial-input num" type="text" name="cm_{idx}_{mes}_proyectado" value="0" inputmode="numeric"></td>'
            )
            celdas.append(
                f'<td class="tabla-oficial-num month-col month-{mes}" data-month-col="{mes}"><input class="tabla-oficial-input num" type="text" name="cm_{idx}_{mes}_realizado" value="0" inputmode="numeric"></td>'
            )
            celdas.append(
                f'<td class="tabla-oficial-num month-col month-{mes} month-percent-col" data-month-col="{mes}"><input class="tabla-oficial-input num cm-percent-input" type="text" name="cm_{idx}_{mes}_percent" value="0%" inputmode="numeric" readonly></td>'
            )
        rows.append(f"<tr><td>{rubro}</td>{''.join(celdas)}</tr>")
    return "".join(rows)


def _presupuesto_table_rows_html(df: pd.DataFrame) -> str:
    rows = []
    for row in df.itertuples(index=False):
        cod = escape(str(getattr(row, "cod", "") or ""))
        tipo = escape(str(getattr(row, "tipo", "") or ""))
        rubro = escape(str(getattr(row, "rubro", "") or ""))
        monto = escape(str(getattr(row, "monto", "") or "0"))
        mensual = escape(str(getattr(row, "mensual", "") or "0"))
        rows.append(
            "<tr>"
            f'<td class="cod-col" style="display:none;">{cod}</td>'
            f'<td class="tipo-col" style="display:none;">{tipo}</td>'
            f'<td class="rubro-col">{rubro}</td>'
            f'<td class="tabla-oficial-num"><input class="tabla-oficial-input presupuesto-num-input num" type="text" value="{monto}" inputmode="numeric"></td>'
            f'<td class="tabla-oficial-num presupuesto-mensual">{mensual}</td>'
            "</tr>"
        )
    return "".join(rows)


def _build_presupuesto_csv_response() -> Response:
    df = _load_presupuesto_dataframe()
    rubros = [
        str(getattr(row, "rubro", "") or "").strip()
        for row in df.itertuples(index=False)
        if str(getattr(row, "rubro", "") or "").strip()
    ]
    if not rubros:
        rubros = ["Ejemplo rubro"]
    rows = []
    for rubro in rubros:
        item = {"Rubro": rubro}
        for mes in range(0, 13):
            item[f"mes {mes}"] = 0
        rows.append(item)
    export_df = pd.DataFrame(rows)
    stream = StringIO()
    export_df.to_csv(stream, index=False)
    content = stream.getvalue()
    headers = {"Content-Disposition": "attachment; filename=plantilla_real_mensual_presupuesto.csv"}
    return Response(content, media_type="text/csv; charset=utf-8", headers=headers)


def _build_presupuesto_control_template_csv_response() -> Response:
    # Mismo formato oficial de "Descargar CSV" para evitar dos plantillas distintas.
    return _build_presupuesto_csv_response()


def _read_import_dataframe(upload: UploadFile) -> pd.DataFrame:
    filename = (upload.filename or "").strip().lower()
    if filename.endswith(".csv"):
        return pd.read_csv(upload.file, dtype=str, keep_default_na=False)
    if filename.endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
        return pd.read_excel(upload.file, dtype=str).fillna("")
    raise ValueError("Formato no soportado. Usa CSV o Excel.")


def _to_int_or_none(value) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    normalized = raw.replace(",", "").replace(" ", "")
    try:
        numeric = float(normalized)
    except ValueError:
        return None
    if not pd.notna(numeric):
        return None
    return int(round(numeric))


def _load_control_mensual_store() -> dict:
    if not CONTROL_MENSUAL_STORE_PATH.exists():
        return {"rows": [], "updated_at": ""}
    try:
        raw = json.loads(CONTROL_MENSUAL_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"rows": [], "updated_at": ""}
    if not isinstance(raw, dict):
        return {"rows": [], "updated_at": ""}
    rows = raw.get("rows")
    if not isinstance(rows, list):
        rows = []
    return {
        "rows": rows,
        "updated_at": str(raw.get("updated_at") or ""),
    }


def _save_control_mensual_store(payload: dict) -> None:
    CONTROL_MENSUAL_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTROL_MENSUAL_STORE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_report_filter_catalog() -> dict:
    # Import diferido para evitar ciclos de importación con main.py.
    from fastapi_modulo.main import SessionLocal as CoreSessionLocal, Usuario, _decrypt_sensitive
    from fastapi_modulo.db import DepartamentoOrganizacional, RegionOrganizacional

    db = CoreSessionLocal()
    try:
        departamentos = []
        for dep in db.query(DepartamentoOrganizacional).all():
            nombre = str(getattr(dep, "nombre", "") or "").strip()
            codigo = str(getattr(dep, "codigo", "") or "").strip()
            padre = str(getattr(dep, "padre", "") or "").strip()
            if not nombre:
                continue
            departamentos.append(
                {
                    "nombre": nombre,
                    "codigo": codigo,
                    "padre": padre,
                }
            )

        regiones = []
        for reg in db.query(RegionOrganizacional).all():
            nombre = str(getattr(reg, "nombre", "") or "").strip()
            codigo = str(getattr(reg, "codigo", "") or "").strip()
            if not nombre:
                continue
            regiones.append({"nombre": nombre, "codigo": codigo})

        colaboradores = []
        for user in db.query(Usuario).all():
            nombre = str(getattr(user, "nombre", "") or "").strip()
            username = str(_decrypt_sensitive(getattr(user, "usuario", "")) or "").strip()
            departamento = str(getattr(user, "departamento", "") or "").strip()
            label = nombre or username
            if not label:
                continue
            colaboradores.append(
                {
                    "label": label,
                    "value": username or label,
                    "departments": [departamento] if departamento else [],
                }
            )
    finally:
        db.close()

    sucursales_store = load_sucursales_store()
    sucursales = []
    for item in sucursales_store:
        nombre = str(item.get("nombre") or "").strip()
        codigo = str(item.get("codigo") or "").strip()
        region = str(item.get("region") or "").strip()
        if not nombre:
            continue
        sucursales.append({"nombre": nombre, "codigo": codigo, "region": region})

    # Mapa rápido por región para derivar departamentos/sucursales.
    deps = [{"nombre": d["nombre"], "codigo": d["codigo"], "padre": d["padre"]} for d in departamentos]
    dep_names = {d["nombre"] for d in deps}

    def _unique_payload(items):
        seen = set()
        result = []
        for item in items:
            value = str(item.get("value") or "").strip()
            if not value:
                continue
            key = _normalize_key(value)
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return sorted(result, key=lambda x: str(x.get("label") or "").lower())

    by_level = {
        "consolidado": [{"label": "Consolidado general", "value": "global", "departments": []}],
        "departamento": _unique_payload(
            [
                {
                    "label": d["nombre"],
                    "value": d["codigo"] or d["nombre"],
                    "departments": [d["nombre"]],
                }
                for d in deps
            ]
        ),
        "sucursal": _unique_payload(
            [
                {
                    "label": s["nombre"],
                    "value": s["codigo"] or s["nombre"],
                    "departments": [s["nombre"]] if s["nombre"] in dep_names else [],
                }
                for s in sucursales
            ]
        ),
        "region": _unique_payload(
            [
                {
                    "label": r["nombre"],
                    "value": r["codigo"] or r["nombre"],
                    "departments": sorted(
                        {
                            d["nombre"]
                            for d in deps
                            if _normalize_key(d.get("padre", "")) in {_normalize_key(r["nombre"]), _normalize_key(r.get("codigo", ""))}
                        }
                    ),
                }
                for r in regiones
            ]
        ),
        "colaborador": _unique_payload(colaboradores),
    }
    return by_level


@router.get("/descargar-csv-presupuesto", tags=["presupuesto"])
async def descargar_csv_presupuesto():
    """Descargar CSV del presupuesto anual actual."""
    return _build_presupuesto_csv_response()


@router.get("/presupuesto-reportes-filtros", tags=["presupuesto"])
async def obtener_presupuesto_reportes_filtros(nivel: str = "consolidado"):
    requested = str(nivel or "consolidado").strip().lower()
    catalog = _load_report_filter_catalog()
    allowed = {"consolidado", "region", "departamento", "sucursal", "colaborador"}
    if requested not in allowed:
        requested = "consolidado"
    return JSONResponse(
        {
            "success": True,
            "nivel": requested,
            "niveles": [
                {"value": "consolidado", "label": "Consolidado"},
                {"value": "region", "label": "Región"},
                {"value": "departamento", "label": "Departamento"},
                {"value": "sucursal", "label": "Sucursal"},
                {"value": "colaborador", "label": "Colaborador"},
            ],
            "items": catalog.get(requested, []),
        }
    )


@router.get("/descargar-plantilla-presupuesto", tags=["presupuesto"])
async def descargar_plantilla_presupuesto():
    """Plantilla para importar datos mensuales (con número de mes)."""
    return _build_presupuesto_control_template_csv_response()


@router.post("/importar-control-mensual", tags=["presupuesto"])
async def importar_control_mensual(file: UploadFile = File(...)):
    try:
        df = _read_import_dataframe(file)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)
    except Exception:
        return JSONResponse({"success": False, "error": "No se pudo leer el archivo"}, status_code=400)

    if df.empty:
        return JSONResponse({"success": False, "error": "El archivo está vacío"}, status_code=400)

    original_cols = list(df.columns)
    normalized_cols = {_normalize_import_col(col): col for col in original_cols}

    rubro_col = next((normalized_cols.get(key) for key in ("rubro", "nombre_rubro", "concepto")), None)
    month_col = next((normalized_cols.get(key) for key in ("mes_numero", "mes", "month", "numero_mes")), None)
    proyectado_col = next((normalized_cols.get(key) for key in ("proyectado", "monto_proyectado", "proyectado_mensual")), None)
    realizado_col = next((normalized_cols.get(key) for key in ("realizado", "monto_realizado", "realizado_mensual")), None)
    wide_month_cols: Dict[int, str] = {}
    for normalized, original in normalized_cols.items():
        # Acepta: mes_0, mes0, month_0 ... mes_12
        match = re.match(r"^(?:mes|month)_?([0-9]{1,2})$", normalized)
        if not match:
            continue
        month_idx = int(match.group(1))
        if month_idx < 0 or month_idx > 12:
            continue
        wide_month_cols[month_idx] = original

    is_wide_format = bool(rubro_col and wide_month_cols)
    if not rubro_col and not is_wide_format:
        return JSONResponse(
            {
                "success": False,
                "error": "Columnas obligatorias: Rubro y meses (mes 0..mes 12) o formato largo con mes_numero.",
                "columns_detected": original_cols,
            },
            status_code=400,
        )
    if not is_wide_format and (not month_col):
        return JSONResponse(
            {
                "success": False,
                "error": "En formato largo debes incluir columna mes_numero (1-12).",
                "columns_detected": original_cols,
            },
            status_code=400,
        )
    if not is_wide_format and (not proyectado_col and not realizado_col):
        return JSONResponse(
            {
                "success": False,
                "error": "Debes incluir al menos una columna de valores: proyectado o realizado.",
                "columns_detected": original_cols,
            },
            status_code=400,
        )

    entries = []
    row_errors = []
    duplicate_keys = set()
    seen_keys = set()
    initial_data_rows = 0
    if is_wide_format:
        for idx, row in df.iterrows():
            line_no = int(idx) + 2
            rubro = str(row.get(rubro_col, "") or "").strip()
            if not rubro:
                row_errors.append(f"Línea {line_no}: rubro vacío.")
                continue
            initial_value = _to_int_or_none(row.get(wide_month_cols.get(0, ""), "")) if wide_month_cols.get(0) else None
            if initial_value not in (None, 0):
                initial_data_rows += 1
            for mes_int in range(1, 13):
                month_column = wide_month_cols.get(mes_int)
                if not month_column:
                    continue
                realizado = _to_int_or_none(row.get(month_column, ""))
                if realizado is None:
                    continue
                mes = f"{mes_int:02d}"
                key = (_normalize_rubro_key(rubro), mes)
                if key in seen_keys:
                    duplicate_keys.add(key)
                seen_keys.add(key)
                entries.append(
                    {
                        "line": line_no,
                        "rubro": rubro,
                        "rubro_key": key[0],
                        "mes_numero": mes_int,
                        "mes": mes,
                        "proyectado": None,
                        "realizado": realizado,
                    }
                )
    else:
        for idx, row in df.iterrows():
            line_no = int(idx) + 2
            rubro = str(row.get(rubro_col, "") or "").strip()
            mes_raw = row.get(month_col, "")
            mes_int = _to_int_or_none(mes_raw)
            proyectado = _to_int_or_none(row.get(proyectado_col, "")) if proyectado_col else None
            realizado = _to_int_or_none(row.get(realizado_col, "")) if realizado_col else None

            if not rubro:
                row_errors.append(f"Línea {line_no}: rubro vacío.")
                continue
            if not mes_int or mes_int < 1 or mes_int > 12:
                row_errors.append(f"Línea {line_no}: mes_numero inválido ({mes_raw}). Debe ser 1-12.")
                continue
            if proyectado is None and realizado is None:
                row_errors.append(f"Línea {line_no}: sin valores en proyectado/realizado.")
                continue

            mes = f"{mes_int:02d}"
            key = (_normalize_rubro_key(rubro), mes)
            if key in seen_keys:
                duplicate_keys.add(key)
            seen_keys.add(key)
            entries.append(
                {
                    "line": line_no,
                    "rubro": rubro,
                    "rubro_key": key[0],
                    "mes_numero": mes_int,
                    "mes": mes,
                    "proyectado": proyectado,
                    "realizado": realizado,
                }
            )

    if row_errors:
        return JSONResponse(
            {
                "success": False,
                "error": "Se detectaron errores en el archivo.",
                "details": row_errors[:50],
            },
            status_code=400,
        )

    return JSONResponse(
        {
            "success": True,
            "entries": entries,
            "summary": {
                "rows": len(entries),
                "duplicates_in_file": len(duplicate_keys),
                "initial_data_rows": int(initial_data_rows),
                "format": "wide_real_only" if is_wide_format else "long",
            },
        }
    )


@router.get("/control-mensual-datos", tags=["presupuesto"])
async def obtener_control_mensual_datos():
    store = _load_control_mensual_store()
    # Compatibilidad con frontend legado y nuevo:
    # - rows/updated_at en raíz
    # - data con el objeto completo
    return JSONResponse(
        {
            "success": True,
            "rows": store.get("rows", []),
            "updated_at": store.get("updated_at", ""),
            "data": store,
        }
    )


@router.post("/guardar-control-mensual", tags=["presupuesto"])
async def guardar_control_mensual(data: dict = Body(default={})):
    rows = data.get("rows")
    if not isinstance(rows, list):
        return JSONResponse({"success": False, "error": "rows debe ser una lista"}, status_code=400)
    sanitized = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        rubro = str(item.get("rubro") or "").strip()
        if not rubro:
            continue
        months = item.get("months")
        if not isinstance(months, dict):
            continue
        row_months = {}
        for mes in range(1, 13):
            key = f"{mes:02d}"
            payload = months.get(key)
            if not isinstance(payload, dict):
                payload = {}
            proyectado = _to_int_or_none(payload.get("proyectado"))
            realizado = _to_int_or_none(payload.get("realizado"))
            row_months[key] = {
                "proyectado": int(proyectado or 0),
                "realizado": int(realizado or 0),
            }
        sanitized.append({"rubro": rubro, "months": row_months})
    store_payload = {
        "rows": sanitized,
        "updated_at": pd.Timestamp.utcnow().isoformat(),
    }
    _save_control_mensual_store(store_payload)
    return JSONResponse({"success": True, "saved_rows": len(sanitized)})


@router.get("/presupuesto", response_class=HTMLResponse)
def proyectando_presupuesto_page(request: Request):
    """Página de proyección de presupuesto con shell oficial."""
    df = _load_presupuesto_dataframe()
    presupuesto_table_rows = _presupuesto_table_rows_html(df)
    control_mensual_header_top, control_mensual_header_bottom = _control_mensual_header_html()
    control_mensual_rows = _control_mensual_rows_html(df)
    template = request.app.state.templates.env.get_template("modulos/presupuesto/presupuesto.html")
    content = template.render(
        presupuesto_table_rows=presupuesto_table_rows,
        control_mensual_header_top=control_mensual_header_top,
        control_mensual_header_bottom=control_mensual_header_bottom,
        control_mensual_rows=control_mensual_rows,
    )

    return request.app.state.templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Fase 9: Presupuesto",
            "description": "Gestiona el presupuesto anual y su carga de datos.",
            "page_title": "Fase 9: Presupuesto",
            "page_description": "Gestiona el presupuesto anual y su carga de datos.",
            "section_label": "",
            "section_title": "",
            "content": content,
            "floating_actions_html": "",
            "hide_floating_actions": True,
            "show_page_header": False,
            "colores": _get_colores_context(),
        },
    )


# ─────────────────────────────────────────────
# Presupuesto · Base IA
# ─────────────────────────────────────────────
_PRESUPUESTO_BASE_IA_EXTRA_BLOCK = "presupuesto_base_ia_extra"
_PRESUPUESTO_BASE_IA_WEEKLY_META_BLOCK = "presupuesto_base_ia_weekly_meta"
_PRESUPUESTO_BASE_IA_WEEKLY_INTERVAL_DAYS = 7
_presupuesto_base_ia_cron_lock = threading.Lock()

MESES_NOMBRES = {
    "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
    "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
    "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre",
}


def _get_core_imports():
    """Importaciones diferidas para evitar ciclos."""
    from fastapi_modulo.main import SessionLocal as CoreSessionLocal, is_superadmin, render_backend_page
    from fastapi_modulo.modulos.planificacion.plan_estrategico_service import _ensure_strategic_identity_table
    return CoreSessionLocal, is_superadmin, render_backend_page, _ensure_strategic_identity_table


def _upsert_presupuesto_ia_block(db, bloque: str, payload: Any) -> None:
    encoded = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
    db.execute(
        text(
            "INSERT INTO strategic_identity_config (bloque, payload, updated_at) "
            "VALUES (:b, :p, CURRENT_TIMESTAMP) "
            "ON CONFLICT (bloque) DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP"
        ),
        {"b": bloque, "p": encoded},
    )


def _build_presupuesto_ia_payload() -> Dict[str, Any]:
    """Consolida datos de presupuesto anual + control mensual para la IA."""
    _, _, _, _ensure_strategic_identity_table = _get_core_imports()
    from fastapi_modulo.main import SessionLocal as CoreSessionLocal
    db = CoreSessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.commit()
        meta_rows = db.execute(
            text("SELECT bloque, payload FROM strategic_identity_config WHERE bloque IN (:extra, :meta)"),
            {"extra": _PRESUPUESTO_BASE_IA_EXTRA_BLOCK, "meta": _PRESUPUESTO_BASE_IA_WEEKLY_META_BLOCK},
        ).fetchall()
        payload_map = {str(r[0]).strip(): str(r[1] or "") for r in meta_rows}
        try:
            extra = json.loads(payload_map.get(_PRESUPUESTO_BASE_IA_EXTRA_BLOCK, "{}") or "{}")
        except Exception:
            extra = {}
        try:
            weekly_meta = json.loads(payload_map.get(_PRESUPUESTO_BASE_IA_WEEKLY_META_BLOCK, "{}") or "{}")
        except Exception:
            weekly_meta = {}
        contenido_adicional = str((extra if isinstance(extra, dict) else {}).get("texto") or "").strip()
        weekly_meta = weekly_meta if isinstance(weekly_meta, dict) else {}
    finally:
        db.close()

    # Presupuesto anual
    df = _load_presupuesto_dataframe()
    rubros = []
    total_ingresos = 0
    total_egresos = 0
    for row in df.itertuples(index=False):
        rubro_name = str(getattr(row, "rubro", "") or "").strip()
        tipo = str(getattr(row, "tipo", "") or "").strip()
        monto_str = str(getattr(row, "monto", "") or "").replace(",", "")
        try:
            monto_num = int(float(monto_str)) if monto_str else 0
        except Exception:
            monto_num = 0
        mensual_str = str(getattr(row, "mensual", "") or "").replace(",", "")
        try:
            mensual_num = int(float(mensual_str)) if mensual_str else 0
        except Exception:
            mensual_num = 0
        if not rubro_name:
            continue
        rubros.append({
            "cod": str(getattr(row, "cod", "") or ""),
            "rubro": rubro_name,
            "tipo": tipo,
            "monto_anual": monto_num,
            "mensual_promedio": mensual_num,
        })
        if tipo == "Ingreso":
            total_ingresos += monto_num
        elif tipo == "Egreso":
            total_egresos += monto_num

    # Control mensual (proyectado vs realizado)
    store = _load_control_mensual_store()
    control_rows = store.get("rows", [])
    control_updated_at = store.get("updated_at", "")
    meses_con_datos = []
    for mes_num in range(1, 13):
        mes_key = f"{mes_num:02d}"
        proyectado_total = 0
        realizado_total = 0
        tiene_datos = False
        for row in control_rows:
            months = row.get("months") or {}
            mes_data = months.get(mes_key) or {}
            p = int(mes_data.get("proyectado") or 0)
            r = int(mes_data.get("realizado") or 0)
            if p or r:
                tiene_datos = True
            proyectado_total += p
            realizado_total += r
        if tiene_datos:
            pct = round((realizado_total / proyectado_total * 100) if proyectado_total else 0, 2)
            meses_con_datos.append({
                "mes": mes_key,
                "nombre": MESES_NOMBRES.get(mes_key, mes_key),
                "proyectado_total": proyectado_total,
                "realizado_total": realizado_total,
                "ejecucion_pct": pct,
            })

    presupuesto_str = f"{total_ingresos:,}" if total_ingresos else "N/D"
    egresos_str = f"{total_egresos:,}" if total_egresos else "N/D"
    utilidad = total_ingresos - total_egresos

    return {
        "contenido_adicional": {"texto": contenido_adicional},
        "cron_semanal": {
            "activo": True,
            "intervalo_dias": int(weekly_meta.get("interval_days") or _PRESUPUESTO_BASE_IA_WEEKLY_INTERVAL_DAYS),
            "ultima_actualizacion": str(weekly_meta.get("last_refresh_at") or ""),
            "proxima_actualizacion": str(weekly_meta.get("next_refresh_at") or ""),
            "estado": str(weekly_meta.get("last_status") or ""),
        },
        "presupuesto_anual": {
            "rubros": rubros,
            "total_rubros": len(rubros),
            "total_ingresos": total_ingresos,
            "total_egresos": total_egresos,
            "utilidad_estimada": utilidad,
            "resumen": f"Ingresos: {presupuesto_str} · Egresos: {egresos_str} · Resultado: {utilidad:,}",
        },
        "control_mensual": {
            "meses": meses_con_datos,
            "updated_at": control_updated_at,
            "total_meses_con_datos": len(meses_con_datos),
        },
    }


def _build_presupuesto_ia_html(payload: Dict[str, Any]) -> str:
    anual = payload.get("presupuesto_anual", {})
    control = payload.get("control_mensual", {})
    cron = payload.get("cron_semanal", {})
    rubros = anual.get("rubros", [])
    meses = control.get("meses", [])
    contenido_adicional_texto = str((payload.get("contenido_adicional") or {}).get("texto") or "")
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)

    # Tabla de rubros
    rubros_rows = "".join(
        "<tr>"
        f"<td style='padding:4px 8px;'>{escape(r.get('cod', ''))}</td>"
        f"<td style='padding:4px 8px;'>{escape(r.get('rubro', ''))}</td>"
        f"<td style='padding:4px 8px;'><span style='color:{'#166534' if r.get('tipo') == 'Ingreso' else '#991b1b' if r.get('tipo') == 'Egreso' else '#334155'};font-weight:600;'>{escape(r.get('tipo', ''))}</span></td>"
        f"<td style='padding:4px 8px;text-align:right;'>{r.get('monto_anual', 0):,}</td>"
        f"<td style='padding:4px 8px;text-align:right;'>{r.get('mensual_promedio', 0):,}</td>"
        "</tr>"
        for r in rubros
    ) or "<tr><td colspan='5' style='padding:4px 8px;color:#64748b;'>Sin datos cargados</td></tr>"

    # Tabla de control mensual
    meses_rows = "".join(
        "<tr>"
        f"<td style='padding:4px 8px;'><b>{escape(m.get('nombre', ''))}</b></td>"
        f"<td style='padding:4px 8px;text-align:right;'>{m.get('proyectado_total', 0):,}</td>"
        f"<td style='padding:4px 8px;text-align:right;'>{m.get('realizado_total', 0):,}</td>"
        f"<td style='padding:4px 8px;text-align:right;'>{m.get('ejecucion_pct', 0):.1f}%</td>"
        "</tr>"
        for m in meses
    ) or "<tr><td colspan='4' style='padding:4px 8px;color:#64748b;'>Sin control mensual cargado</td></tr>"

    return (
        "<section style='display:grid;gap:12px;'>"
        # Header
        "<section style='border:1px solid #bfdbfe;background:#eff6ff;border-radius:12px;padding:12px;'>"
        "<h3 style='margin:0 0 8px;'>Base IA · Presupuesto</h3>"
        "<p style='margin:0;color:#334155;'>Fuente consolidada para consulta de IA: presupuesto anual y control mensual.</p>"
        "</section>"
        # Resumen financiero
        "<section style='border:1px solid #dbe4ea;border-radius:12px;padding:12px;background:#f8fafc;'>"
        "<h4 style='margin:0 0 8px;'>Resumen financiero anual</h4>"
        f"<p style='margin:0;color:#334155;'>"
        f"Rubros: <b>{int(anual.get('total_rubros') or 0)}</b> · "
        f"Ingresos: <b>{int(anual.get('total_ingresos') or 0):,}</b> · "
        f"Egresos: <b>{int(anual.get('total_egresos') or 0):,}</b> · "
        f"Resultado estimado: <b>{int(anual.get('utilidad_estimada') or 0):,}</b>"
        "</p>"
        "</section>"
        # Tabla rubros
        "<section style='border:1px solid #dbe4ea;border-radius:12px;padding:12px;background:#fff;'>"
        "<h4 style='margin:0 0 8px;'>Tabla de rubros (presupuesto anual)</h4>"
        "<div style='overflow-x:auto;'>"
        "<table style='width:100%;border-collapse:collapse;font-size:12px;'>"
        "<thead><tr style='background:#f1f5f9;'>"
        "<th style='padding:4px 8px;text-align:left;'>Código</th>"
        "<th style='padding:4px 8px;text-align:left;'>Rubro</th>"
        "<th style='padding:4px 8px;text-align:left;'>Tipo</th>"
        "<th style='padding:4px 8px;text-align:right;'>Monto anual</th>"
        "<th style='padding:4px 8px;text-align:right;'>Mensual prom.</th>"
        "</tr></thead>"
        f"<tbody>{rubros_rows}</tbody>"
        "</table>"
        "</div>"
        "</section>"
        # Control mensual
        "<section style='border:1px solid #dbe4ea;border-radius:12px;padding:12px;background:#fff;'>"
        f"<h4 style='margin:0 0 8px;'>Control mensual</h4>"
        f"<p style='margin:0 0 8px;font-size:12px;color:#64748b;'>Última actualización: {escape(str(control.get('updated_at') or 'N/D'))} · {int(control.get('total_meses_con_datos') or 0)} mes(es) con datos</p>"
        "<div style='overflow-x:auto;'>"
        "<table style='width:100%;border-collapse:collapse;font-size:12px;'>"
        "<thead><tr style='background:#f1f5f9;'>"
        "<th style='padding:4px 8px;text-align:left;'>Mes</th>"
        "<th style='padding:4px 8px;text-align:right;'>Proyectado</th>"
        "<th style='padding:4px 8px;text-align:right;'>Realizado</th>"
        "<th style='padding:4px 8px;text-align:right;'>% Ejecución</th>"
        "</tr></thead>"
        f"<tbody>{meses_rows}</tbody>"
        "</table>"
        "</div>"
        "</section>"
        # Cron semanal
        "<section style='border:1px solid #dbe4ea;border-radius:12px;padding:12px;background:#fff;'>"
        "<h4 style='margin:0 0 8px;'>Cron semanal (renovación automática)</h4>"
        f"<p style='margin:0 0 6px;color:#334155;'>Intervalo: <b>{int((cron or {}).get('intervalo_dias') or _PRESUPUESTO_BASE_IA_WEEKLY_INTERVAL_DAYS)} días</b> · "
        f"Última actualización: <b>{escape(str((cron or {}).get('ultima_actualizacion') or 'N/D'))}</b> · "
        f"Próxima: <b>{escape(str((cron or {}).get('proxima_actualizacion') or 'N/D'))}</b></p>"
        f"<p style='margin:0 0 10px;color:#64748b;font-size:12px;'>Estado: {escape(str((cron or {}).get('estado') or 'sin_ejecucion'))}</p>"
        "<button type='button' id='pres-base-ia-refresh' style='background:#14532d;color:#fff;border:1px solid #14532d;border-radius:10px;padding:8px 14px;cursor:pointer;'>Actualizar ahora (reemplaza contenido previo)</button>"
        "<span id='pres-base-ia-refresh-status' style='margin-left:10px;font-size:12px;color:#475569;'></span>"
        "<script>(function(){"
        "const btn=document.getElementById('pres-base-ia-refresh');"
        "const st=document.getElementById('pres-base-ia-refresh-status');"
        "if(!btn||!st)return;"
        "btn.addEventListener('click',async function(){"
        "  btn.disabled=true;st.textContent='Actualizando...';"
        "  try{"
        "    const res=await fetch('/proyectando/presupuesto/base-ia/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({force:true})});"
        "    const data=await res.json();"
        "    if(!res.ok||!data||data.success!==true)throw new Error((data&&data.error)||'Error');"
        "    st.textContent='Actualizado. Recarga para ver cambios.';"
        "  }catch(err){st.textContent=err.message||'Error';}"
        "  finally{btn.disabled=false;}"
        "});})();</script>"
        "</section>"
        # Contenido adicional editable
        "<section style='border:1px solid #dbe4ea;border-radius:12px;padding:12px;background:#fff;'>"
        "<h4 style='margin:0 0 8px;'>Contenido adicional para IA (editable)</h4>"
        "<p style='margin:0 0 8px;color:#475569;'>Contexto adicional que la IA usará en conversaciones sobre presupuesto.</p>"
        f"<textarea id='pres-base-ia-extra' style='width:100%;min-height:180px;padding:10px;border:1px solid #cbd5e1;border-radius:10px;font-size:13px;'>{escape(contenido_adicional_texto)}</textarea>"
        "<div style='margin-top:10px;display:flex;gap:10px;align-items:center;'>"
        "<button type='button' id='pres-base-ia-save' style='background:#0f172a;color:#fff;border:1px solid #0f172a;border-radius:10px;padding:8px 14px;cursor:pointer;'>Guardar contenido adicional</button>"
        "<span id='pres-base-ia-save-status' style='font-size:12px;color:#475569;'></span>"
        "</div>"
        "<script>(function(){"
        "const btn=document.getElementById('pres-base-ia-save');"
        "const txt=document.getElementById('pres-base-ia-extra');"
        "const st=document.getElementById('pres-base-ia-save-status');"
        "if(!btn||!txt||!st)return;"
        "btn.addEventListener('click',async function(){"
        "  btn.disabled=true;st.textContent='Guardando...';"
        "  try{"
        "    const res=await fetch('/proyectando/presupuesto/base-ia/contenido',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({texto:String(txt.value||'')})});"
        "    const data=await res.json();"
        "    if(!res.ok||!data||data.success!==true)throw new Error((data&&data.error)||'Error');"
        "    st.textContent='Guardado correctamente';"
        "  }catch(err){st.textContent=err.message||'Error al guardar';}"
        "  finally{btn.disabled=false;}"
        "});})();</script>"
        "</section>"
        # Payload JSON
        "<section style='border:1px solid #dbe4ea;border-radius:12px;padding:12px;background:#fff;'>"
        "<h4 style='margin:0 0 8px;'>Payload estructurado (JSON)</h4>"
        f"<pre style='margin:0;white-space:pre-wrap;word-break:break-word;background:#0f172a;color:#e2e8f0;padding:12px;border-radius:10px;font-size:12px;'>{escape(payload_json)}</pre>"
        "</section>"
        "</section>"
    )


def _refresh_weekly_presupuesto_base_ia_if_due(force: bool = False) -> dict:
    """Actualiza el resumen semanal del presupuesto, reemplazando el contenido anterior."""
    _, _, _, _ensure_strategic_identity_table = _get_core_imports()
    from fastapi_modulo.main import SessionLocal as CoreSessionLocal
    with _presupuesto_base_ia_cron_lock:
        db = CoreSessionLocal()
        try:
            _ensure_strategic_identity_table(db)
            meta_row = db.execute(
                text("SELECT payload FROM strategic_identity_config WHERE bloque = :b LIMIT 1"),
                {"b": _PRESUPUESTO_BASE_IA_WEEKLY_META_BLOCK},
            ).fetchone()
            try:
                meta = json.loads(str(meta_row[0] or "{}")) if meta_row else {}
            except Exception:
                meta = {}
            last_refresh_raw = str(meta.get("last_refresh_at") or "").strip()
            now = datetime.utcnow()
            last_dt = None
            if last_refresh_raw:
                try:
                    last_dt = datetime.fromisoformat(last_refresh_raw)
                except Exception:
                    pass
            due = force or (last_dt is None) or ((now - last_dt) >= timedelta(days=_PRESUPUESTO_BASE_IA_WEEKLY_INTERVAL_DAYS))
            if not due:
                next_at = (last_dt + timedelta(days=_PRESUPUESTO_BASE_IA_WEEKLY_INTERVAL_DAYS)).isoformat() if last_dt else ""
                return {"updated": False, "reason": "not_due", "last_refresh_at": last_refresh_raw, "next_refresh_at": next_at}

            # Genera snapshot de texto con datos actuales
            df = _load_presupuesto_dataframe()
            store = _load_control_mensual_store()
            ingresos, egresos = 0, 0
            lineas = [
                f"=== Snapshot semanal Presupuesto === Corte: {now.isoformat()}",
                f"Control mensual actualizado: {store.get('updated_at', 'N/D')}",
            ]
            # ── Sección 1: Catálogo de rubros con tipo y monto ──────────────
            lineas.append("\n--- RUBROS PRESUPUESTARIOS ---")
            rubro_index: dict = {}  # rubro_lower → {"tipo", "monto", "cod"}
            for row in df.itertuples(index=False):
                rubro = str(getattr(row, "rubro", "") or "").strip()
                tipo = str(getattr(row, "tipo", "") or "").strip()
                cod = str(getattr(row, "cod", "") or getattr(row, "codigo", "") or "").strip()
                monto_str = str(getattr(row, "monto", "") or "").replace(",", "")
                try:
                    monto_num = int(float(monto_str)) if monto_str else 0
                except Exception:
                    monto_num = 0
                if not rubro:
                    continue
                rubro_index[rubro.lower()] = {"tipo": tipo, "monto": monto_num, "cod": cod, "rubro": rubro}
                lineas.append(f"  [{cod}] {tipo or '---'} | {rubro}: {monto_num:,}")
                if tipo == "Ingreso":
                    ingresos += monto_num
                elif tipo == "Egreso":
                    egresos += monto_num
            lineas.append(
                f"\nTOTALES: Ingresos {ingresos:,} · Egresos {egresos:,} · "
                f"Resultado {ingresos - egresos:,} ({'superávit' if ingresos >= egresos else 'déficit'})"
            )

            # ── Sección 2: Control mensual consolidado ──────────────────────
            lineas.append("\n--- CONTROL MENSUAL CONSOLIDADO ---")
            proy_anual_total, real_anual_total = 0, 0
            for mes_num in range(1, 13):
                mes_key = f"{mes_num:02d}"
                proy, real = 0, 0
                for row in store.get("rows", []):
                    mes_data = (row.get("months") or {}).get(mes_key) or {}
                    proy += int(mes_data.get("proyectado") or 0)
                    real += int(mes_data.get("realizado") or 0)
                if proy or real:
                    pct = round(real / proy * 100, 1) if proy else 0.0
                    estado = "✓ ejecutado" if pct >= 90 else ("⚠ bajo" if pct < 50 else "→ parcial")
                    lineas.append(
                        f"  {MESES_NOMBRES.get(mes_key, mes_key)}: Proyectado {proy:,} · "
                        f"Realizado {real:,} · {pct}% {estado}"
                    )
                    proy_anual_total += proy
                    real_anual_total += real
            pct_anual = round(real_anual_total / proy_anual_total * 100, 1) if proy_anual_total else 0.0
            lineas.append(
                f"\nEjecución anual acumulada: Proyectado {proy_anual_total:,} · "
                f"Realizado {real_anual_total:,} · {pct_anual}%"
            )

            # ── Sección 3: Control mensual por RUBRO ────────────────────────
            lineas.append("\n--- CONTROL MENSUAL POR RUBRO ---")
            for row in store.get("rows", []):
                rubro_r = str(row.get("rubro") or row.get("nombre") or "").strip()
                if not rubro_r:
                    continue
                tipo_r = rubro_index.get(rubro_r.lower(), {}).get("tipo", "---")
                proy_r, real_r = 0, 0
                mes_detalle = []
                for mes_num in range(1, 13):
                    mes_key = f"{mes_num:02d}"
                    md = (row.get("months") or {}).get(mes_key) or {}
                    p = int(md.get("proyectado") or 0)
                    r = int(md.get("realizado") or 0)
                    proy_r += p
                    real_r += r
                    if p or r:
                        mes_detalle.append(
                            f"{MESES_NOMBRES.get(mes_key, mes_key)}: P {p:,}/R {r:,}"
                        )
                if proy_r or real_r:
                    pct_r = round(real_r / proy_r * 100, 1) if proy_r else 0.0
                    lineas.append(
                        f"  {tipo_r} | {rubro_r}: "
                        f"Anual proyectado {proy_r:,} · realizado {real_r:,} · {pct_r}%"
                    )
                    if mes_detalle:
                        lineas.append("    " + " | ".join(mes_detalle))

            new_text = "\n".join(lineas)
            _upsert_presupuesto_ia_block(db, _PRESUPUESTO_BASE_IA_EXTRA_BLOCK, {"texto": new_text})
            next_at = (now + timedelta(days=_PRESUPUESTO_BASE_IA_WEEKLY_INTERVAL_DAYS)).isoformat()
            _upsert_presupuesto_ia_block(db, _PRESUPUESTO_BASE_IA_WEEKLY_META_BLOCK, {
                "last_refresh_at": now.isoformat(),
                "next_refresh_at": next_at,
                "interval_days": _PRESUPUESTO_BASE_IA_WEEKLY_INTERVAL_DAYS,
                "last_status": "ok",
                "last_error": "",
                "generated_chars": len(new_text),
            })
            db.commit()
            return {"updated": True, "last_refresh_at": now.isoformat(), "next_refresh_at": next_at, "generated_chars": len(new_text)}
        except Exception as exc:
            db.rollback()
            raise exc
        finally:
            db.close()


@router.get("/presupuesto/base-ia", response_class=HTMLResponse)
def presupuesto_base_ia_page(request: Request):
    _, is_superadmin, render_backend_page, _ = _get_core_imports()
    if not is_superadmin(request):
        return RedirectResponse(url="/no-acceso", status_code=302)
    try:
        _refresh_weekly_presupuesto_base_ia_if_due(force=False)
    except Exception:
        pass
    payload = _build_presupuesto_ia_payload()
    return render_backend_page(
        request,
        title="Base IA · Presupuesto",
        description="Concentrado de presupuesto anual y control mensual para consulta de IA.",
        content=_build_presupuesto_ia_html(payload),
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get("/presupuesto/base-ia/datos", response_class=JSONResponse)
def presupuesto_base_ia_api(request: Request):
    _, is_superadmin, _, _ = _get_core_imports()
    if not is_superadmin(request):
        return JSONResponse({"success": False, "error": "Acceso denegado"}, status_code=403)
    try:
        _refresh_weekly_presupuesto_base_ia_if_due(force=False)
    except Exception:
        pass
    payload = _build_presupuesto_ia_payload()
    return JSONResponse({"success": True, "data": payload})


@router.get("/presupuesto/base-ia/contenido", response_class=JSONResponse)
def presupuesto_base_ia_contenido_get(request: Request):
    _, is_superadmin, _, _ensure_strategic_identity_table = _get_core_imports()
    from fastapi_modulo.main import SessionLocal as CoreSessionLocal
    if not is_superadmin(request):
        return JSONResponse({"success": False, "error": "Acceso denegado"}, status_code=403)
    db = CoreSessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.commit()
        row = db.execute(
            text("SELECT payload FROM strategic_identity_config WHERE bloque = :b LIMIT 1"),
            {"b": _PRESUPUESTO_BASE_IA_EXTRA_BLOCK},
        ).fetchone()
        try:
            pj = json.loads(str(row[0] or "{}")) if row else {}
        except Exception:
            pj = {}
        texto = str((pj if isinstance(pj, dict) else {}).get("texto") or "").strip()
        return JSONResponse({"success": True, "data": {"texto": texto}})
    finally:
        db.close()


@router.put("/presupuesto/base-ia/contenido", response_class=JSONResponse)
def presupuesto_base_ia_contenido_put(request: Request, data: dict = Body(...)):
    _, is_superadmin, _, _ensure_strategic_identity_table = _get_core_imports()
    from fastapi_modulo.main import SessionLocal as CoreSessionLocal
    if not is_superadmin(request):
        return JSONResponse({"success": False, "error": "Acceso denegado"}, status_code=403)
    texto = str(data.get("texto") or "").strip()
    db = CoreSessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        _upsert_presupuesto_ia_block(db, _PRESUPUESTO_BASE_IA_EXTRA_BLOCK, {"texto": texto})
        db.commit()
        return JSONResponse({"success": True, "data": {"texto": texto}})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse({"success": False, "error": "No se pudo guardar."}, status_code=500)
    finally:
        db.close()


@router.post("/presupuesto/base-ia/refresh", response_class=JSONResponse)
def presupuesto_base_ia_refresh(request: Request, data: dict = Body(default={})):
    _, is_superadmin, _, _ = _get_core_imports()
    if not is_superadmin(request):
        return JSONResponse({"success": False, "error": "Acceso denegado"}, status_code=403)
    force = bool((data or {}).get("force", True))
    try:
        result = _refresh_weekly_presupuesto_base_ia_if_due(force=force)
        return JSONResponse({"success": True, "data": result})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
