import json
import os
from datetime import date
from typing import Any, Dict, List

import pandas as pd


APP_ENV_DEFAULT = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()
RUNTIME_STORE_DIR = (os.environ.get("RUNTIME_STORE_DIR") or f"fastapi_modulo/runtime_store/{APP_ENV_DEFAULT}").strip()
DATOS_PRELIMINARES_STORE_PATH = (
    os.environ.get("DATOS_PRELIMINARES_STORE_PATH")
    or os.path.join(RUNTIME_STORE_DIR, "datos_preliminares_store.json")
).strip()
SUCURSALES_STORE_PATH = (
    os.environ.get("SUCURSALES_STORE_PATH")
    or os.path.join(RUNTIME_STORE_DIR, "sucursales_store.json")
).strip()
MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INFORMACION_FINANCIERA_CATALOGO_PATH = (
    os.environ.get("INFORMACION_FINANCIERA_CATALOGO_PATH")
    or os.path.join(MODULE_DIR, "assets", "informacion_financiera_catalogo.json")
).strip()
INFORMACION_FINANCIERA_XLSX_PATH = (
    os.environ.get("INFORMACION_FINANCIERA_XLSX_PATH")
    or os.path.join(MODULE_DIR, "assets", "informacion_financiera.xlsx")
).strip()

DEFAULT_DATOS_GENERALES = {
    "responsable_general": "",
    "primer_anio_proyeccion": "",
    "anios_proyeccion": "3",
    "moneda": "$",
    "inflacion_estimada": "",
    "tasa_crecimiento": "",
    "observaciones": "",
    "sociedad": "",
    "figura_juridica": "",
    "calle": "",
    "numero_exterior": "",
    "numero_interior": "",
    "colonia": "",
    "ciudad": "",
    "municipio": "",
    "estado": "",
    "cp": "",
    "pais": "",
    "ifb_activos_m3": "",
    "ifb_activos_m2": "",
    "ifb_activos_m1": "",
    "ifb_pasivos_m3": "",
    "ifb_pasivos_m2": "",
    "ifb_pasivos_m1": "",
    "ifb_capital_m3": "",
    "ifb_capital_m2": "",
    "ifb_capital_m1": "",
    "ifb_ingresos_m3": "",
    "ifb_ingresos_m2": "",
    "ifb_ingresos_m1": "",
    "ifb_egresos_m3": "",
    "ifb_egresos_m2": "",
    "ifb_egresos_m1": "",
    "ifb_resultado_m3": "",
    "ifb_resultado_m2": "",
    "ifb_resultado_m1": "",
    "macro_inflacion_json": "",
    "macro_udi_json": "",
    "activo_fijo_json": "",
    "activo_fijo_compras_json": "",
    "gastos_rows_json": "",
    "ifb_rows_json": "",
    "ifb_conceptos_json": "",
    "cg_activo_total_growth_json": "",
    "cg_activo_total_rows_json": "",
    "cg_financiamiento_rows_json": "",
    "cg_financiamiento_standard_json": "",
    "cg_financiamiento_pasivo_pct_json": "",
    "cg_financiamiento_resultado_pct_json": "",
}

DEFAULT_ACTIVO_FIJO_ROWS = [
    {"rubro": "Terrenos", "anios": "0"},
    {"rubro": "Construcciones", "anios": "20"},
    {"rubro": "Construcciones en proceso", "anios": "5"},
    {"rubro": "Equipo de transporte", "anios": "4"},
    {"rubro": "Equipo de cómputo", "anios": "3"},
    {"rubro": "Mobiliario", "anios": "3"},
    {"rubro": "Otras propiedades, mobiliario y equipo", "anios": "2"},
]

DEFAULT_ACTIVO_FIJO_COMPRAS_ROWS = [
    {"rubro": "Propiedades, mobiliario y equipo", "proyecciones": []},
    {"rubro": "Terrenos", "proyecciones": []},
    {"rubro": "Construcciones", "proyecciones": []},
    {"rubro": "Equipo de transporte", "proyecciones": []},
    {"rubro": "Equipo de cómputo", "proyecciones": []},
    {"rubro": "Mobiliario", "proyecciones": []},
    {"rubro": "Adaptaciones y mejoras", "proyecciones": []},
]


def _ensure_store_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def load_datos_preliminares_store() -> Dict[str, str]:
    data = dict(DEFAULT_DATOS_GENERALES)
    if not os.path.exists(DATOS_PRELIMINARES_STORE_PATH):
        return data
    try:
        with open(DATOS_PRELIMINARES_STORE_PATH, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict):
            for key in data.keys():
                if key in loaded and loaded[key] is not None:
                    data[key] = str(loaded[key]).strip()
    except (OSError, json.JSONDecodeError):
        pass
    return data


def save_datos_preliminares_store(data: Dict[str, str]) -> None:
    safe_payload: Dict[str, str] = {}
    for key, default_value in DEFAULT_DATOS_GENERALES.items():
        safe_payload[key] = str(data.get(key, default_value) or "").strip()
    _ensure_store_parent_dir(DATOS_PRELIMINARES_STORE_PATH)
    with open(DATOS_PRELIMINARES_STORE_PATH, "w", encoding="utf-8") as fh:
        json.dump(safe_payload, fh, ensure_ascii=False, indent=2)


def load_sucursales_store() -> List[Dict[str, str]]:
    if not os.path.exists(SUCURSALES_STORE_PATH):
        return []
    try:
        with open(SUCURSALES_STORE_PATH, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(loaded, list):
        return []
    rows: List[Dict[str, str]] = []
    for item in loaded:
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("nombre") or "").strip()
        region = str(item.get("region") or "").strip()
        codigo = str(item.get("codigo") or "").strip()
        descripcion = str(item.get("descripcion") or "").strip()
        if not nombre and not region and not codigo and not descripcion:
            continue
        rows.append(
            {
                "nombre": nombre,
                "region": region,
                "codigo": codigo,
                "descripcion": descripcion,
            }
        )
    return rows


def save_sucursales_store(rows: List[Dict[str, str]]) -> None:
    safe_rows: List[Dict[str, str]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("nombre") or "").strip()
        region = str(item.get("region") or "").strip()
        codigo = str(item.get("codigo") or "").strip()
        descripcion = str(item.get("descripcion") or "").strip()
        if not nombre and not region and not codigo and not descripcion:
            continue
        safe_rows.append(
            {
                "nombre": nombre,
                "region": region,
                "codigo": codigo,
                "descripcion": descripcion,
            }
        )
    _ensure_store_parent_dir(SUCURSALES_STORE_PATH)
    with open(SUCURSALES_STORE_PATH, "w", encoding="utf-8") as fh:
        json.dump(safe_rows, fh, ensure_ascii=False, indent=2)


def load_informacion_financiera_catalogo() -> List[Dict[str, str]]:
    if os.path.exists(INFORMACION_FINANCIERA_XLSX_PATH):
        try:
            df = pd.read_excel(
                INFORMACION_FINANCIERA_XLSX_PATH,
                sheet_name=0,
                usecols=[0, 1, 2],
                names=["nivel", "cuenta", "descripcion"],
                header=0,
                engine="openpyxl",
            )
            df = df.dropna(how="all")
            df["nivel"] = pd.to_numeric(df["nivel"], errors="coerce").fillna(0).astype(int)
            for column in ("cuenta", "descripcion"):
                df[column] = df[column].fillna("").astype(str).str.strip()
            df = df[(df["cuenta"] != "") | (df["descripcion"] != "")]
            return df[["nivel", "cuenta", "descripcion"]].to_dict(orient="records")
        except Exception:
            pass
    if not os.path.exists(INFORMACION_FINANCIERA_CATALOGO_PATH):
        return []
    try:
        with open(INFORMACION_FINANCIERA_CATALOGO_PATH, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(loaded, list):
        return []
    df = pd.DataFrame(loaded)
    if df.empty:
        return []
    for column in ("nivel", "cuenta", "descripcion"):
        if column not in df.columns:
            df[column] = ""
    df["nivel"] = pd.to_numeric(df["nivel"], errors="coerce").fillna(0).astype(int)
    df["cuenta"] = df["cuenta"].fillna("").astype(str).str.strip()
    df["descripcion"] = df["descripcion"].fillna("").astype(str).str.strip()
    df = df[(df["cuenta"] != "") | (df["descripcion"] != "")]
    return df[["nivel", "cuenta", "descripcion"]].to_dict(orient="records")


def _parse_json_value(raw: str, fallback: Any) -> Any:
    try:
        parsed = json.loads(raw or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    return fallback if parsed is None else parsed


def _series_to_numeric(series: pd.Series, *, percent: bool = False) -> pd.Series:
    cleaned = (
        series.fillna("")
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
    )
    numeric = pd.to_numeric(cleaned, errors="coerce")
    if percent:
        return numeric.round(2)
    return numeric


def _format_amount(value: Any) -> str:
    if pd.isna(value):
        return ""
    rounded = round(float(value), 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return f"{int(round(rounded)):,}"
    return f"{rounded:,.2f}"


def _format_percent(value: Any) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):,.2f}%"


def _format_whole_amount(value: Any) -> str:
    if pd.isna(value):
        return ""
    return f"{int(round(float(value))):,}"


def _float_or_none(value: Any) -> Any:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _humanize_financiamiento_label(key: str) -> str:
    label = str(key or "").replace("pasivos_", "").replace("capital_", "").replace("_", " ").strip()
    return label.title() if label else ""


def _get_projection_years(store: Dict[str, str]) -> int:
    try:
        years = int(str(store.get("anios_proyeccion") or "").strip() or 3)
    except (TypeError, ValueError):
        years = 3
    return max(1, min(years, 10))


def _get_projection_start_year(store: Dict[str, str]) -> int:
    try:
        year = int(str(store.get("primer_anio_proyeccion") or "").strip())
    except (TypeError, ValueError):
        year = date.today().year
    return year


def get_if_period_columns(store: Dict[str, str] | None = None) -> List[Dict[str, str]]:
    current_store = store or load_datos_preliminares_store()
    start_year = _get_projection_start_year(current_store)
    projection_years = _get_projection_years(current_store)
    columns = [
        {"key": "-3", "label": str(start_year - 3)},
        {"key": "-2", "label": str(start_year - 2)},
        {"key": "-1", "label": str(start_year - 1)},
    ]
    for idx in range(projection_years):
        columns.append({"key": str(idx), "label": str(start_year + idx)})
    return columns
