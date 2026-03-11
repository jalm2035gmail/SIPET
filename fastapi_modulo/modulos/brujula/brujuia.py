import os
from typing import Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text
from fastapi_modulo.modulos.brujula.brujula_fixed_indicators import get_brujula_fixed_indicators

router = APIRouter()

BRUJULA_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "modulos", "brujula", "brujula.html"
)
BRUJULA_INDICADORES_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "modulos", "brujula", "brujula_indicadores.html"
)

BRUJULA_SECTIONS = {
    "dashboard": "Dashboard Ejecutivo",
    "solidez-financiera": "Solidez Financiera",
    "liquidez": "Liquidez",
    "rentabilidad": "Rentabilidad",
    "crecimiento": "Crecimiento",
    "liderazgo": "Liderazgo",
    "productividad": "Productividad",
    "balance-social": "Balance Social",
    "reportes": "Reportes",
    "configuracion": "Configuración",
    "indicadores": "Indicadores",
}

_CORE_BOUND = False


def _load_brujula_template(section_title: str, section_description: str) -> str:
    try:
        with open(BRUJULA_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            template = fh.read()
    except OSError:
        return (
            "<section>"
            f"<h2>{section_title}</h2>"
            f"<p>{section_description}</p>"
            "</section>"
        )
    return (
        template.replace("{{ BRUJULA_SECTION_TITLE }}", section_title)
        .replace("{{ BRUJULA_SECTION_DESCRIPTION }}", section_description)
    )



def _bind_core_symbols() -> None:
    global _CORE_BOUND
    if _CORE_BOUND:
        return
    from fastapi_modulo import main as core

    names = ["SessionLocal", "_normalize_tenant_id", "get_current_tenant"]
    for name in names:
        globals()[name] = getattr(core, name)
    _CORE_BOUND = True


def _current_tenant_id(request: Request | None = None) -> str:
    _bind_core_symbols()
    if request is None:
        return _normalize_tenant_id("default")
    return _normalize_tenant_id(get_current_tenant(request))


def _load_indicadores_template() -> str:
    try:
        with open(BRUJULA_INDICADORES_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "<p>No se pudo cargar la vista de indicadores.</p>"


def _ensure_brujula_indicator_table(db) -> None:
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


def _ensure_brujula_indicator_definition_table(db) -> None:
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


def _load_brujula_indicator_definition_overrides(db, tenant_id: str) -> dict[str, dict[str, str]]:
    _ensure_brujula_indicator_definition_table(db)
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


def _merged_brujula_indicator_definitions(db=None, tenant_id: str | None = None) -> list[dict]:
    items = _fixed_indicator_definitions()
    overrides: dict[str, dict[str, str]] = {}
    if db is not None and tenant_id:
        overrides = _load_brujula_indicator_definition_overrides(db, tenant_id)
    merged: list[dict] = []
    for item in items:
        current = dict(item)
        override = overrides.get(str(current.get("nombre") or "").strip().lower()) or {}
        for field in ("estandar_meta", "semaforo_rojo", "semaforo_verde"):
            if field in override:
                current[field] = str(override.get(field) or "").strip()
        merged.append(current)
    return merged


def _periods_from_projection_config():
    from fastapi_modulo.modulos.proyectando.proyectando_store_common import (
        get_if_period_columns,
        load_datos_preliminares_store,
    )

    store = load_datos_preliminares_store()
    periods = []
    for item in get_if_period_columns(store):
        key = str(item.get("key") or "").strip()
        periods.append(
            {
                "key": key,
                "label": str(item.get("label") or key),
                "kind": "historico" if key.startswith("-") else "proyectado",
            }
        )
    return periods


def _fixed_indicator_definitions() -> list[dict]:
    return get_brujula_fixed_indicators()


def _fixed_indicator_names() -> list[str]:
    return [str(item.get("nombre") or "").strip() for item in _fixed_indicator_definitions() if str(item.get("nombre") or "").strip()]


def _normalize_indicator_matrix_rows(raw_rows, periods):
    rows = raw_rows if isinstance(raw_rows, list) else []
    valid_period_keys = {str(period.get("key") or "").strip() for period in periods}
    clean = []
    seen = set()
    for idx, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        indicador = str(item.get("indicador") or "").strip()
        if not indicador:
            continue
        key = indicador.lower()
        if key in seen:
            continue
        seen.add(key)
        raw_values = item.get("values") if isinstance(item.get("values"), dict) else {}
        values = {}
        for period_key in valid_period_keys:
            values[period_key] = str(raw_values.get(period_key) or "").strip()
        clean.append({"indicador": indicador, "values": values, "orden": idx})
    return clean


def _parse_numeric_value(value: Any) -> float | None:
    raw = str(value or "").replace(",", "").replace("%", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _format_indicator_percent(value: float | None) -> str:
    if value is None:
        return ""
    return f"{float(value):,.2f}%"


def _format_indicator_amount(value: float | None) -> str:
    if value is None:
        return ""
    rounded = round(float(value), 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return f"{int(round(rounded)):,}"
    return f"{rounded:,.2f}"


def _format_indicator_number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{int(round(float(value))):,}"


def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or abs(float(denominator)) < 1e-9:
        return None
    return float(numerator) / float(denominator)


def _safe_growth(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or abs(float(previous)) < 1e-9:
        return None
    return ((float(current) - float(previous)) / float(previous)) * 100.0


def _coalesce_numeric(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return float(value)
    return None


def _sum_numeric(*values: float | None) -> float | None:
    present = [float(value) for value in values if value is not None]
    if not present:
        return None
    return sum(present)


def _average_numeric(*values: float | None) -> float | None:
    present = [float(value) for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _percent_value(numerator: float | None, denominator: float | None) -> float | None:
    ratio = _safe_divide(numerator, denominator)
    if ratio is None:
        return None
    return ratio * 100.0


def _difference_value(left: float | None, right: float | None) -> float | None:
    if left is None and right is None:
        return None
    return float(left or 0.0) - float(right or 0.0)


def _load_financial_indicator_context(periods: list[dict], store: dict[str, str] | None = None) -> dict[str, Any]:
    from fastapi_modulo.modulos.proyectando.proyectando_store_common import (
        _parse_json_value,
        load_datos_preliminares_store,
    )

    current_store = dict(store or load_datos_preliminares_store())
    raw_rows = _parse_json_value(current_store.get("ifb_rows_json", ""), [])
    rows = raw_rows if isinstance(raw_rows, list) else []
    row_map: dict[str, dict[str, Any]] = {}
    value_map: dict[str, dict[str, float | None]] = {}
    period_keys = [str(period.get("key") or "").strip() for period in periods]

    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("cuenta") or row.get("cod") or "").strip()
        if not code:
            continue
        row_map[code] = row
        raw_values = row.get("values") if isinstance(row.get("values"), dict) else {}
        value_map[code] = {key: _parse_numeric_value(raw_values.get(key)) for key in period_keys}

    def get_value(code: str, period_key: str) -> float | None:
        return (value_map.get(code) or {}).get(period_key)

    def series_growth(code: str, period_key: str) -> float | None:
        try:
            index = period_keys.index(period_key)
        except ValueError:
            return None
        if index <= 0:
            return None
        return _safe_growth(get_value(code, period_key), get_value(code, period_keys[index - 1]))

    return {
        "store": current_store,
        "row_map": row_map,
        "value_map": value_map,
        "period_keys": period_keys,
        "get_value": get_value,
        "series_growth": series_growth,
    }


def _calculate_brujula_indicator_values(periods: list[dict], store: dict[str, str] | None = None) -> dict[str, dict[str, str]]:
    context = _load_financial_indicator_context(periods, store)
    get_value = context["get_value"]
    period_keys = context["period_keys"]
    calculated: dict[str, dict[str, str]] = {name: {key: "" for key in period_keys} for name in _fixed_indicator_names()}

    def assign_percent(name: str, resolver) -> None:
        for period_key in period_keys:
            calculated[name][period_key] = _format_indicator_percent(resolver(period_key))

    def assign_amount(name: str, resolver) -> None:
        for period_key in period_keys:
            calculated[name][period_key] = _format_indicator_amount(resolver(period_key))

    def assign_number(name: str, resolver) -> None:
        for period_key in period_keys:
            calculated[name][period_key] = _format_indicator_number(resolver(period_key))

    def activo_total(period_key: str) -> float | None:
        return get_value("100-00-00-00-00-000", period_key)

    def disponibilidades(period_key: str) -> float | None:
        return get_value("101-00-00-00-00-000", period_key)

    def inversiones(period_key: str) -> float | None:
        return get_value("102-00-00-00-00-000", period_key)

    def cartera_vigente(period_key: str) -> float | None:
        return get_value("104-00-00-00-00-000", period_key)

    def cartera_vencida(period_key: str) -> float | None:
        return get_value("105-00-00-00-00-000", period_key)

    def estimacion_crediticia(period_key: str) -> float | None:
        return get_value("106-00-00-00-00-000", period_key)

    def cartera_total(period_key: str) -> float | None:
        return _sum_numeric(cartera_vigente(period_key), cartera_vencida(period_key))

    def cartera_neta(period_key: str) -> float | None:
        return _difference_value(cartera_total(period_key), estimacion_crediticia(period_key))

    def depositos_ahorro(period_key: str) -> float | None:
        return get_value("201-00-00-00-00-000", period_key)

    def depositos_vista(period_key: str) -> float | None:
        return _coalesce_numeric(get_value("201-01-00-00-00-000", period_key), depositos_ahorro(period_key))

    def prestamos_externos(period_key: str) -> float | None:
        return get_value("202-00-00-00-00-000", period_key)

    def capital_contable(period_key: str) -> float | None:
        return get_value("300-00-00-00-00-000", period_key)

    def capital_social(period_key: str) -> float | None:
        return get_value("301-00-00-00-00-000", period_key)

    def reservas(period_key: str) -> float | None:
        return get_value("302-00-00-00-00-000", period_key)

    def ingresos(period_key: str) -> float | None:
        return get_value("400-00-00-00-00-000", period_key)

    def gastos_total(period_key: str) -> float | None:
        direct = get_value("500-00-00-00-00-000", period_key)
        if direct is not None:
            return direct
        ingreso = ingresos(period_key)
        resultado = get_value("__resultado__", period_key)
        if ingreso is None or resultado is None:
            return None
        return ingreso - resultado

    def gastos_financieros(period_key: str) -> float | None:
        return _coalesce_numeric(get_value("501-00-00-00-00-000", period_key), gastos_total(period_key))

    def gastos_administracion(period_key: str) -> float | None:
        return get_value("505-00-00-00-00-000", period_key)

    def resultado_neto(period_key: str) -> float | None:
        return get_value("__resultado__", period_key)

    def socios(period_key: str) -> float | None:
        return get_value("__metric_socios__", period_key)

    def empleados(period_key: str) -> float | None:
        return get_value("__metric_empleados__", period_key)

    def activos_improductivos(period_key: str) -> float | None:
        return _sum_numeric(
            get_value("107-00-00-00-00-000", period_key),
            get_value("108-00-00-00-00-000", period_key),
            get_value("109-00-00-00-00-000", period_key),
            get_value("110-00-00-00-00-000", period_key),
            get_value("113-00-00-00-00-000", period_key),
        )

    def liquidez_inmediata(period_key: str) -> float | None:
        return _sum_numeric(disponibilidades(period_key), inversiones(period_key))

    def previous_period_value(series_resolver, period_key: str) -> float | None:
        try:
            index = period_keys.index(period_key)
        except ValueError:
            return None
        if index <= 0:
            return None
        return series_resolver(period_keys[index - 1])

    assign_percent("C2 - Indice de capitalizacion", lambda key: _percent_value(capital_contable(key), activo_total(key)))
    assign_percent("C3 - Solvencia", lambda key: _percent_value(cartera_neta(key), activo_total(key)))
    assign_percent("C4 - Credito neto", lambda key: _percent_value(cartera_vencida(key), cartera_total(key)))
    assign_percent("C5 - Indice de morosidad", lambda key: _percent_value(estimacion_crediticia(key), cartera_vencida(key)))
    assign_percent("C6 - Cobertura de cartera vencida", lambda key: _percent_value(liquidez_inmediata(key), depositos_vista(key)))
    assign_percent("C7 - Coeficiente de liquidez", lambda key: _percent_value(activos_improductivos(key), capital_contable(key)))
    assign_percent("C8 - Fondeo de activos improductivos", lambda key: _percent_value(ingresos(key), gastos_total(key)))
    assign_percent("C9 - Autosuficiencia operativa", lambda key: _percent_value(gastos_administracion(key), ingresos(key)))
    assign_percent("C10 - ROA", lambda key: _percent_value(resultado_neto(key), activo_total(key)))
    assign_amount("C11 - ROA", lambda key: _difference_value(ingresos(key), gastos_financieros(key)))

    assign_percent("O1 - Cartera vigente", lambda key: _percent_value(inversiones(key), activo_total(key)))
    assign_percent("O2 - Inversiones liquidas", lambda key: _percent_value(prestamos_externos(key), activo_total(key)))
    assign_percent("O3 - Fondeo de prestamos externos", lambda key: _percent_value(depositos_ahorro(key), activo_total(key)))
    assign_percent("O4 - Depositos de ahorro", lambda key: _percent_value(capital_social(key), activo_total(key)))
    assign_percent("O5 - Capital social", lambda key: _percent_value(reservas(key), activo_total(key)))
    assign_percent("O6 - Fondo de reserva", lambda key: _percent_value(reservas(key), capital_contable(key)))
    assign_amount("O7 - Capital no comprometido", capital_contable)
    assign_percent("O9 - Gastos de personal", lambda key: _percent_value(activos_improductivos(key), activo_total(key)))

    assign_percent("A1 - Liderazgo", lambda key: _percent_value(ingresos(key), _average_numeric(cartera_total(key), previous_period_value(cartera_total, key))))
    assign_percent("A3 - Ingreso por inversiones", lambda key: _percent_value(gastos_financieros(key), _average_numeric(depositos_ahorro(key), previous_period_value(depositos_ahorro, key))))
    assign_percent("A4 - Costo financiero por depositos", lambda key: _percent_value(gastos_financieros(key), prestamos_externos(key)))
    assign_percent("A5 - Costo de fondeo financiero", lambda key: _percent_value(resultado_neto(key), capital_contable(key)))
    assign_percent("A6 - ROE", lambda key: _percent_value(liquidez_inmediata(key), depositos_ahorro(key)))
    assign_percent("A7 - Liquidez inmediata de ahorro", lambda key: _percent_value(liquidez_inmediata(key), depositos_vista(key)))
    assign_percent("A8 - Liquidez inmediata a la vista", lambda key: _percent_value(liquidez_inmediata(key), prestamos_externos(key)))

    assign_percent("Cr1 - Castigos acumulados recuperados", lambda key: context["series_growth"]("104-00-00-00-00-000", key))
    assign_percent("Cr2 - Crecimiento de la cartera", lambda key: context["series_growth"]("102-00-00-00-00-000", key))
    assign_percent("Cr3 - Crecimiento de inversiones", lambda key: context["series_growth"]("201-00-00-00-00-000", key))
    assign_percent("Cr4 - Crecimiento en depositos", lambda key: context["series_growth"]("202-00-00-00-00-000", key))
    assign_percent("Cr5 - Crecimiento en financiamiento", lambda key: context["series_growth"]("301-00-00-00-00-000", key))
    assign_percent("Cr6 - Crecimiento en capital social", lambda key: context["series_growth"]("302-00-00-00-00-000", key))
    assign_percent("Cr7 - Crecimiento en fondo de reserva", lambda key: context["series_growth"]("__metric_socios__", key))
    assign_percent("Cr8 - Crecimiento en socios", lambda key: context["series_growth"]("100-00-00-00-00-000", key))

    assign_amount("+2 - Contribucion de crecimiento", lambda key: _safe_divide(depositos_ahorro(key), socios(key)))
    assign_number("+5 - Socios con prestamo", lambda key: _safe_divide(socios(key), empleados(key)))
    assign_number("+6 - Promedio de socios por empleado", lambda key: _safe_divide(socios(key), empleados(key)))
    assign_amount("+12 - Capacitacion de los socios", lambda key: _safe_divide(resultado_neto(key), empleados(key)))
    assign_amount("+16 - Gasto por colaborador", lambda key: _safe_divide(gastos_total(key), empleados(key)))

    return calculated


def get_brujula_indicator_notebook(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        tenant_id = _current_tenant_id(request)
        periods = _periods_from_projection_config()
        _ensure_brujula_indicator_table(db)
        db.commit()
        calculated_values = _calculate_brujula_indicator_values(periods)
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
        stored = []
        seen = set()
        for row in rows:
            indicador = str(row[0] or "").strip()
            if not indicador:
                continue
            try:
                values = __import__("json").loads(str(row[1] or "{}"))
            except Exception:
                values = {}
            key = indicador.lower()
            if key in seen:
                continue
            seen.add(key)
            stored.append({"indicador": indicador, "values": values, "orden": int(row[2] or 0)})
        stored = _normalize_indicator_matrix_rows(stored, periods)
        values_by_name = {str(item["indicador"]).strip().lower(): item.get("values") or {} for item in stored}
        fixed_rows = []
        for order, name in enumerate(_fixed_indicator_names(), start=1):
            calculated_row = calculated_values.get(name) or {}
            stored_row = values_by_name.get(name.lower()) or {}
            fixed_rows.append(
                {
                    "indicador": name,
                    "values": {
                        str(period["key"]): str(calculated_row.get(str(period["key"])) or stored_row.get(str(period["key"]), "")).strip()
                        for period in periods
                    },
                    "orden": order,
                }
            )
        return JSONResponse({"success": True, "data": {"periods": periods, "rows": fixed_rows}})
    finally:
        db.close()


def save_brujula_indicator_notebook(request: Request, data: dict = Body(...)):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        tenant_id = _current_tenant_id(request)
        periods = _periods_from_projection_config()
        rows = _normalize_indicator_matrix_rows((data or {}).get("rows"), periods)
        allowed_names = {name.lower(): name for name in _fixed_indicator_names()}
        fixed_rows = []
        values_by_name = {}
        for row in rows:
            indicator_name = str(row.get("indicador") or "").strip()
            if indicator_name.lower() not in allowed_names:
                continue
            canonical_name = allowed_names[indicator_name.lower()]
            values_by_name[canonical_name] = row.get("values") or {}
        for order, canonical_name in enumerate(_fixed_indicator_names(), start=1):
            fixed_rows.append(
                {
                    "indicador": canonical_name,
                    "values": {str(period["key"]): str((values_by_name.get(canonical_name) or {}).get(str(period["key"]), "")).strip() for period in periods},
                    "orden": order,
                }
            )
        _ensure_brujula_indicator_table(db)
        db.execute(text("DELETE FROM brujula_indicator_values WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        json = __import__("json")
        for row in fixed_rows:
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
        db.commit()
        return JSONResponse({"success": True, "data": {"rows": fixed_rows}})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


def list_brujula_indicator_definitions(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        tenant_id = _current_tenant_id(request)
        _ensure_brujula_indicator_definition_table(db)
        db.commit()
        return JSONResponse({"success": True, "data": _merged_brujula_indicator_definitions(db, tenant_id)})
    finally:
        db.close()


def save_brujula_indicator_definition(request: Request, data: dict = Body(...)):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        tenant_id = _current_tenant_id(request)
        _ensure_brujula_indicator_definition_table(db)
        allowed_names = {str(item.get("nombre") or "").strip().lower(): str(item.get("nombre") or "").strip() for item in _fixed_indicator_definitions()}
        indicador = str((data or {}).get("nombre") or (data or {}).get("indicador") or "").strip()
        if not indicador or indicador.lower() not in allowed_names:
            return JSONResponse({"success": False, "error": "Indicador invalido."}, status_code=400)
        canonical_name = allowed_names[indicador.lower()]
        estandar_meta = str((data or {}).get("estandar_meta") or "").strip()
        semaforo_rojo = str((data or {}).get("semaforo_rojo") or "").strip()
        semaforo_verde = str((data or {}).get("semaforo_verde") or "").strip()
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
                "indicador": canonical_name,
                "estandar_meta": estandar_meta,
                "semaforo_rojo": semaforo_rojo,
                "semaforo_verde": semaforo_verde,
            },
        )
        db.commit()
        merged_items = _merged_brujula_indicator_definitions(db, tenant_id)
        updated = next((item for item in merged_items if str(item.get("nombre") or "").strip().lower() == canonical_name.lower()), None)
        return JSONResponse({"success": True, "data": updated or {}})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


def delete_brujula_indicator_definition(indicator_id: int):
    return JSONResponse(
        {"success": False, "error": "Los indicadores de BRUJULA estan fijos en la aplicacion."},
        status_code=405,
    )


def import_brujula_indicator_definitions():
    return JSONResponse(
        {"success": False, "error": "La importacion esta deshabilitada porque los indicadores de BRUJULA son fijos."},
        status_code=405,
    )


def _build_section_description(section_title: str) -> str:
    if section_title == "Dashboard Ejecutivo":
        return (
            "Visualiza en tiempo real la solidez financiera, la liquidez, la "
            "rentabilidad, el crecimiento y el balance social de la institución."
        )
    return (
        f"Visualiza el comportamiento de {section_title.lower()} dentro del tablero "
        "ejecutivo de BRUJULA."
    )


def _render_brujula_page(
    request: Request,
    page_title: str,
    section_title: str,
    section_key: str,
):
    from fastapi_modulo.main import render_backend_page

    description = _build_section_description(section_title)
    return render_backend_page(
        request,
        title=page_title,
        description=description,
        content=_load_brujula_template(section_title, description).replace(
            "{{ BRUJULA_SECTION_KEY }}", section_key
        ),
        hide_floating_actions=True,
        show_page_header=False,
    )


def _render_brujula_indicadores_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    return render_backend_page(
        request,
        title="BRUJULA - Indicadores",
        description="Gestión y seguimiento de indicadores clave de desempeño.",
        content=_load_indicadores_template(),
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/brujula", response_class=HTMLResponse)
def brujula_page(request: Request):
    return _render_brujula_page(
        request,
        "BRUJULA",
        "Dashboard Ejecutivo",
        "dashboard",
    )


@router.get("/brujula/{section}", response_class=HTMLResponse)
def brujula_section_page(request: Request, section: str):
    if section == "indicadores":
        return _render_brujula_indicadores_page(request)
    section_title = BRUJULA_SECTIONS.get(section, section.replace("-", " ").title())
    return _render_brujula_page(
        request,
        f"BRUJULA - {section_title}",
        section_title,
        section,
    )


router.add_api_route("/api/brujula/indicadores/notebook", get_brujula_indicator_notebook, methods=["GET"])
router.add_api_route("/api/brujula/indicadores/notebook", save_brujula_indicator_notebook, methods=["POST"])
router.add_api_route("/api/brujula/indicadores/definiciones", list_brujula_indicator_definitions, methods=["GET"])
router.add_api_route("/api/brujula/indicadores/definicion", save_brujula_indicator_definition, methods=["POST"])
router.add_api_route("/api/brujula/indicadores/definicion/{indicator_id}", delete_brujula_indicator_definition, methods=["DELETE"])
router.add_api_route("/api/brujula/indicadores/importar", import_brujula_indicator_definitions, methods=["POST"])
