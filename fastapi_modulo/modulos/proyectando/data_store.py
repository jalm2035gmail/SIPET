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
INFORMACION_FINANCIERA_CATALOGO_PATH = (
    os.environ.get("INFORMACION_FINANCIERA_CATALOGO_PATH")
    or os.path.join("fastapi_modulo", "modulos", "proyectando", "informacion_financiera_catalogo.json")
).strip()
INFORMACION_FINANCIERA_XLSX_PATH = (
    os.environ.get("INFORMACION_FINANCIERA_XLSX_PATH")
    or os.path.join("fastapi_modulo", "modulos", "proyectando", "informacion_financiera.xlsx")
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
    "gastos_rows_json": "",
    "ifb_rows_json": "",
    "ifb_conceptos_json": "",
    "cg_activo_total_growth_json": "",
    "cg_activo_total_rows_json": "",
    "cg_financiamiento_rows_json": "",
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


def _cuenta_parent_level6(cuenta: str) -> str:
    parts = str(cuenta or "").split("-")
    if len(parts) != 6:
        return ""
    parts[2] = "00"
    parts[3] = "00"
    parts[4] = "00"
    parts[5] = "000"
    return "-".join(parts)


def normalize_ifb_rows_json(raw: str) -> str:
    rows = _parse_json_value(raw, [])
    if not isinstance(rows, list) or not rows:
        return "[]"

    normalized_rows: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        values = row.get("values", {})
        if not isinstance(values, dict):
            values = {}
        normalized_rows.append(
            {
                "cuenta": str(row.get("cuenta") or row.get("cod") or "").strip(),
                "descripcion": str(row.get("descripcion") or row.get("rubro") or "").strip(),
                "nivel": str(row.get("nivel") or "").strip(),
                "values": {
                    str(key): str(value or "").strip()
                    for key, value in values.items()
                },
            }
        )

    if not normalized_rows:
        return "[]"

    df = pd.DataFrame(normalized_rows)
    if df.empty:
        return "[]"

    for column in ("cuenta", "descripcion", "nivel"):
        if column not in df.columns:
            df[column] = ""
        df[column] = df[column].fillna("").astype(str).str.strip()
    if "values" not in df.columns:
        df["values"] = [{} for _ in range(len(df))]
    df["values"] = df["values"].apply(lambda value: value if isinstance(value, dict) else {})
    df["nivel_num"] = pd.to_numeric(df["nivel"], errors="coerce").fillna(0).astype(int)

    period_keys = sorted(
        {
            str(key).strip()
            for value_map in df["values"].tolist()
            if isinstance(value_map, dict)
            for key in value_map.keys()
            if str(key).strip() != ""
        },
        key=lambda value: (int(value) if str(value).lstrip("-").isdigit() else 9999, value),
    )
    if not period_keys:
        return json.dumps(normalized_rows, ensure_ascii=False)

    for period_key in period_keys:
        df[f"period_{period_key}"] = _series_to_numeric(
            df["values"].map(lambda value_map, key=period_key: value_map.get(key, "") if isinstance(value_map, dict) else "")
        )

    level9_df = df[df["nivel_num"] == 9].copy()
    if not level9_df.empty:
        level9_df["parent_cuenta"] = level9_df["cuenta"].map(_cuenta_parent_level6)
        grouped = (
            level9_df.groupby("parent_cuenta")[[f"period_{period_key}" for period_key in period_keys]]
            .sum(min_count=1)
            .reset_index()
        )
        grouped_map = {
            str(item["parent_cuenta"]): item
            for item in grouped.to_dict(orient="records")
            if str(item.get("parent_cuenta") or "").strip() != ""
        }
        updated_values: List[Dict[str, str]] = []
        for row in df.to_dict(orient="records"):
            row_values = dict(row.get("values") or {})
            if int(row.get("nivel_num") or 0) == 6 and row.get("cuenta") in grouped_map:
                sums_row = grouped_map[row["cuenta"]]
                for period_key in period_keys:
                    value = sums_row.get(f"period_{period_key}")
                    row_values[period_key] = _format_whole_amount(value)
            updated_values.append(row_values)
        df["values"] = updated_values

    formatted_values: List[Dict[str, str]] = []
    for row in df.to_dict(orient="records"):
        row_values = dict(row.get("values") or {})
        normalized_map: Dict[str, str] = {}
        for period_key in period_keys:
            raw_value = row_values.get(period_key, "")
            numeric = _series_to_numeric(pd.Series([raw_value])).iloc[0]
            normalized_map[period_key] = "" if pd.isna(numeric) else _format_whole_amount(numeric)
        for extra_key, extra_value in row_values.items():
            if str(extra_key) not in normalized_map:
                normalized_map[str(extra_key)] = str(extra_value or "").strip()
        formatted_values.append(normalized_map)
    df["values"] = formatted_values

    output_rows = df[["cuenta", "descripcion", "nivel", "values"]].to_dict(orient="records")
    row1 = output_rows[0] if len(output_rows) >= 1 else None
    row49 = output_rows[48] if len(output_rows) >= 49 else None
    row56 = output_rows[55] if len(output_rows) >= 56 else None
    row70 = output_rows[69] if len(output_rows) >= 70 else None
    row71 = output_rows[70] if len(output_rows) >= 71 else None

    if isinstance(row71, dict):
        values = row71.get("values", {})
        if not isinstance(values, dict):
            values = {}
        for period_key in period_keys:
            total = _series_to_numeric(pd.Series([((row1 or {}).get("values", {}) or {}).get(period_key, "")])).iloc[0]
            pasivo = _series_to_numeric(pd.Series([((row49 or {}).get("values", {}) or {}).get(period_key, "")])).iloc[0]
            capital = _series_to_numeric(pd.Series([((row56 or {}).get("values", {}) or {}).get(period_key, "")])).iloc[0]
            resultado = _series_to_numeric(pd.Series([((row70 or {}).get("values", {}) or {}).get(period_key, "")])).iloc[0]
            diff = (
                (0 if pd.isna(total) else float(total))
                - (0 if pd.isna(pasivo) else float(pasivo))
                - (0 if pd.isna(capital) else float(capital))
                - (0 if pd.isna(resultado) else float(resultado))
            )
            values[period_key] = _format_whole_amount(diff)
        row71["values"] = values
    return json.dumps(output_rows, ensure_ascii=False)


def _build_ifb_rows_for_template(store: Dict[str, str]) -> List[Dict[str, Any]]:
    current_store = dict(store or {})
    catalog_rows = load_informacion_financiera_catalogo()
    parsed_rows = _parse_json_value(current_store.get("ifb_rows_json", ""), [])
    existing_map: Dict[str, Dict[str, Any]] = {}
    if isinstance(parsed_rows, list):
        for row in parsed_rows:
            if not isinstance(row, dict):
                continue
            cuenta = str(row.get("cuenta") or row.get("cod") or "").strip()
            if cuenta:
                existing_map[cuenta] = row

    output_rows: List[Dict[str, Any]] = []
    for row in catalog_rows:
        cuenta = str(row.get("cuenta") or "").strip()
        existing = existing_map.get(cuenta, {})
        output_rows.append(
            {
                "cuenta": cuenta,
                "descripcion": str(row.get("descripcion") or existing.get("descripcion") or "").strip(),
                "nivel": str(row.get("nivel") or existing.get("nivel") or "").strip(),
                "values": existing.get("values") if isinstance(existing.get("values"), dict) else {},
            }
        )

    for synthetic in (
        {"cuenta": "__resultado__", "descripcion": "Resultado", "nivel": ""},
        {"cuenta": "__validacion__", "descripcion": "Validación", "nivel": ""},
        {"cuenta": "__metric_socios__", "descripcion": "# de Socios", "nivel": ""},
        {"cuenta": "__metric_ahorradores_menores__", "descripcion": "# de Ahorradores menores", "nivel": ""},
        {"cuenta": "__metric_sucursales__", "descripcion": "# de Sucursales (Incluyendo Matriz y/o colectoras)", "nivel": ""},
        {"cuenta": "__metric_empleados__", "descripcion": "# de Empleados", "nivel": ""},
        {"cuenta": "__metric_parte_social__", "descripcion": "Valor de la parte social", "nivel": ""},
    ):
        existing = existing_map.get(synthetic["cuenta"], {})
        output_rows.append(
            {
                "cuenta": synthetic["cuenta"],
                "descripcion": synthetic["descripcion"],
                "nivel": synthetic["nivel"],
                "values": existing.get("values") if isinstance(existing.get("values"), dict) else {},
            }
        )

    normalized = normalize_ifb_rows_json(json.dumps(output_rows, ensure_ascii=False))
    parsed_normalized = _parse_json_value(normalized, [])
    return parsed_normalized if isinstance(parsed_normalized, list) else []


def load_ifb_rows_for_template(store: Dict[str, str] | None = None) -> List[Dict[str, Any]]:
    current_store = sync_ifb_activo_total_from_crecimiento(store or load_datos_preliminares_store())
    return _build_ifb_rows_for_template(current_store)


def sync_ifb_activo_total_from_crecimiento(store: Dict[str, str]) -> Dict[str, str]:
    current_store = dict(store or {})
    if_rows = _build_ifb_rows_for_template(current_store)
    if not if_rows:
        return current_store

    periods = get_if_period_columns(current_store)
    period_by_year = {int(period["label"]): str(period["key"]) for period in periods if str(period.get("label", "")).isdigit()}
    activo_rows = _parse_json_value(current_store.get("cg_activo_total_rows_json", ""), [])
    activo_df = pd.DataFrame(activo_rows if isinstance(activo_rows, list) else [])
    if activo_df.empty:
        return current_store

    for column in ("year", "saldo"):
        if column not in activo_df.columns:
            activo_df[column] = pd.NA
    activo_df["year"] = pd.to_numeric(activo_df["year"], errors="coerce")
    activo_df["saldo"] = _series_to_numeric(activo_df["saldo"])

    activo_row = None
    for row in if_rows:
        if str(row.get("cuenta") or "").strip() == "100-00-00-00-00-000":
            activo_row = row
            break
    if not isinstance(activo_row, dict):
        return current_store

    values = activo_row.get("values") if isinstance(activo_row.get("values"), dict) else {}
    for _, record in activo_df.iterrows():
        year = record.get("year")
        saldo = record.get("saldo")
        if pd.isna(year):
            continue
        period_key = period_by_year.get(int(year))
        if not period_key:
            continue
        values[period_key] = _format_whole_amount(saldo)
    activo_row["values"] = values
    current_store["ifb_rows_json"] = normalize_ifb_rows_json(json.dumps(if_rows, ensure_ascii=False))
    return current_store


def load_activo_fijo_resumen() -> Dict[str, Any]:
    store = load_datos_preliminares_store()
    rows = _parse_json_value(store.get("activo_fijo_json", ""), [])
    activo_df = pd.DataFrame(rows if isinstance(rows, list) else [])
    if activo_df.empty:
        activo_df = pd.DataFrame(DEFAULT_ACTIVO_FIJO_ROWS)
    for column in ("rubro", "anios"):
        if column not in activo_df.columns:
            activo_df[column] = ""
    activo_df["rubro"] = activo_df["rubro"].fillna("").astype(str).str.strip()
    activo_df["anios_num"] = _series_to_numeric(activo_df["anios"])
    activo_df["anios"] = activo_df["anios_num"].map(_format_amount)
    activo_df["depreciable"] = activo_df["anios_num"].fillna(0).gt(0).map(lambda value: "Sí" if value else "No")
    activo_df = activo_df[activo_df["rubro"] != ""].reset_index(drop=True)
    rows_out = activo_df[["rubro", "anios", "depreciable"]].to_dict(orient="records")
    return {
        "rows": rows_out,
        "summary": {
            "total": int(len(rows_out)),
            "depreciables": int((activo_df["depreciable"] == "Sí").sum()),
            "vida_util_promedio": _format_amount(activo_df.loc[activo_df["anios_num"].gt(0), "anios_num"].mean()),
        },
    }


def load_gastos_resumen() -> Dict[str, Any]:
    store = load_datos_preliminares_store()
    projection_years = _get_projection_years(store)
    rows = _parse_json_value(store.get("gastos_rows_json", ""), [])
    gastos_df = pd.DataFrame(rows if isinstance(rows, list) else [])
    if gastos_df.empty:
        return {
            "rows": [],
            "projection_years": projection_years,
            "summary": {"total": 0, "niveles": "", "capturados": 0},
        }
    for column in ("codigo", "rubro", "m3", "m2", "m1"):
        if column not in gastos_df.columns:
            gastos_df[column] = ""
        gastos_df[column] = gastos_df[column].fillna("").astype(str).str.strip()
    if "proyecciones" not in gastos_df.columns:
        gastos_df["proyecciones"] = [[] for _ in range(len(gastos_df))]
    gastos_df["codigo"] = gastos_df["codigo"].astype(str).str.strip()
    gastos_df["rubro"] = gastos_df["rubro"].astype(str).str.strip()
    gastos_df["nivel"] = gastos_df["codigo"].map(lambda value: 0 if not value else value.count(".") + 1)
    gastos_df["orden"] = range(len(gastos_df))
    gastos_df["proyecciones"] = gastos_df["proyecciones"].apply(
        lambda value: value if isinstance(value, list) else ([] if value in (None, "") else [value])
    )
    gastos_df["m3_num"] = _series_to_numeric(gastos_df["m3"])
    gastos_df["m2_num"] = _series_to_numeric(gastos_df["m2"])
    gastos_df["m1_num"] = _series_to_numeric(gastos_df["m1"])
    for idx in range(projection_years):
        column = f"y{idx + 1}_num"
        gastos_df[column] = gastos_df["proyecciones"].map(
            lambda values, pos=idx: values[pos] if isinstance(values, list) and len(values) > pos else ""
        )
        gastos_df[column] = _series_to_numeric(gastos_df[column])
    output_rows: List[Dict[str, Any]] = []
    for record in gastos_df.sort_values("orden").to_dict(orient="records"):
        projections = []
        for idx in range(projection_years):
            projections.append(_format_amount(record.get(f"y{idx + 1}_num")))
        output_rows.append(
            {
                "codigo": record.get("codigo", ""),
                "rubro": record.get("rubro", ""),
                "nivel": int(record.get("nivel") or 0),
                "m3": _format_amount(record.get("m3_num")),
                "m2": _format_amount(record.get("m2_num")),
                "m1": _format_amount(record.get("m1_num")),
                "proyecciones": projections,
            }
        )
    niveles = sorted({int(level) for level in gastos_df["nivel"].dropna().tolist() if int(level) > 0})
    numeric_columns = ["m3_num", "m2_num", "m1_num"] + [f"y{idx + 1}_num" for idx in range(projection_years)]
    captured_mask = gastos_df[numeric_columns].notna().any(axis=1)
    return {
        "rows": output_rows,
        "projection_years": projection_years,
        "summary": {
            "total": int(len(output_rows)),
            "niveles": ", ".join(str(level) for level in niveles),
            "capturados": int(captured_mask.sum()),
        },
    }


def load_crecimiento_general_resumen() -> Dict[str, List[Dict[str, Any]]]:
    store = load_datos_preliminares_store()
    projection_years = _get_projection_years(store)
    activo_rows = load_crecimiento_general_activo_total_editor(store)["rows"]
    financiamiento_rows = _parse_json_value(store.get("cg_financiamiento_rows_json", ""), {})

    activo_df = pd.DataFrame(activo_rows if isinstance(activo_rows, list) else [])
    if activo_df.empty:
        activo_table: List[Dict[str, Any]] = []
    else:
        for column in ("offset", "year", "saldo", "crecimiento", "pct"):
            if column not in activo_df.columns:
                activo_df[column] = pd.NA
        activo_df["offset"] = pd.to_numeric(activo_df["offset"], errors="coerce")
        activo_df["year"] = pd.to_numeric(activo_df["year"], errors="coerce")
        activo_df["saldo"] = _series_to_numeric(activo_df["saldo"])
        activo_df = activo_df[
            activo_df["offset"].between(-3, projection_years - 1, inclusive="both")
        ]
        activo_df = activo_df.sort_values(by=["offset", "year"], na_position="last").reset_index(drop=True)
        activo_table = []
        for record in activo_df.to_dict(orient="records"):
            activo_table.append(
                {
                    "year": int(record["year"]) if pd.notna(record["year"]) else "",
                    "saldo": _format_amount(record["saldo"]),
                    "crecimiento": _format_amount(record.get("crecimiento")),
                    "pct": _format_percent(record.get("pct")),
                }
            )

    financiamiento_source = financiamiento_rows if isinstance(financiamiento_rows, dict) else {}
    financiamiento_df = pd.DataFrame.from_dict(financiamiento_source, orient="index")
    if financiamiento_df.empty:
        pasivo_table: List[Dict[str, Any]] = []
        patrimonio_table: List[Dict[str, Any]] = []
    else:
        financiamiento_df = financiamiento_df.reset_index().rename(columns={"index": "clave"})
        financiamiento_df["orden"] = range(len(financiamiento_df))
        for column in ("y0_amount", "y1_amount", "proj_amount"):
            if column not in financiamiento_df.columns:
                financiamiento_df[column] = pd.NA
            financiamiento_df[column] = _series_to_numeric(financiamiento_df[column])
        financiamiento_df["rubro"] = financiamiento_df["clave"].map(_humanize_financiamiento_label)
        financiamiento_df["seccion"] = financiamiento_df["clave"].map(
            lambda key: "pasivo" if str(key).startswith("pasivos_") else ("patrimonio" if str(key).startswith("capital_") else "")
        )
        financiamiento_df = financiamiento_df[financiamiento_df["seccion"] != ""].sort_values("orden")

        def _to_rows(section: str) -> List[Dict[str, Any]]:
            section_df = financiamiento_df[financiamiento_df["seccion"] == section]
            rows: List[Dict[str, Any]] = []
            for record in section_df.to_dict(orient="records"):
                rows.append(
                    {
                        "rubro": record["rubro"],
                        "y0": _format_amount(record["y0_amount"]),
                        "y1": _format_amount(record["y1_amount"]),
                        "proj": _format_amount(record["proj_amount"]),
                    }
                )
            return rows

        pasivo_table = _to_rows("pasivo")
        patrimonio_table = _to_rows("patrimonio")

    return {
        "activo_total": activo_table,
        "pasivo_total": pasivo_table,
        "patrimonio": patrimonio_table,
    }


def load_crecimiento_general_activo_total_editor(store: Dict[str, str] | None = None) -> Dict[str, Any]:
    current_store = store or load_datos_preliminares_store()
    projection_years = _get_projection_years(current_store)
    start_year = _get_projection_start_year(current_store)
    raw_rows = _parse_json_value(current_store.get("cg_activo_total_rows_json", ""), [])
    growth_map_raw = _parse_json_value(current_store.get("cg_activo_total_growth_json", ""), {})
    growth_map = growth_map_raw if isinstance(growth_map_raw, dict) else {}

    df = pd.DataFrame(raw_rows if isinstance(raw_rows, list) else [])
    if df.empty:
        return {"rows": [], "growth_map": growth_map, "projection_years": projection_years}

    for column in ("offset", "year", "saldo", "crecimiento", "pct"):
        if column not in df.columns:
            df[column] = pd.NA
    df["offset"] = pd.to_numeric(df["offset"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["saldo"] = _series_to_numeric(df["saldo"])
    df["crecimiento"] = _series_to_numeric(df["crecimiento"])
    df["pct"] = _series_to_numeric(df["pct"], percent=True)
    df = df[df["offset"].between(-3, projection_years - 1, inclusive="both")].copy()
    df = df.sort_values(by=["offset", "year"], na_position="last").reset_index(drop=True)

    historical_rows = []
    for offset in (-3, -2, -1):
        match = df[df["offset"] == offset]
        if match.empty:
            continue
        record = match.iloc[0].to_dict()
        historical_rows.append(
            {
                "offset": int(offset),
                "year": int(record["year"]) if pd.notna(record["year"]) else start_year + int(offset),
                "saldo": _float_or_none(record.get("saldo")),
                "crecimiento": _float_or_none(record.get("crecimiento")),
                "pct": _float_or_none(record.get("pct")),
                "projected": False,
            }
        )

    rows_out = list(historical_rows)
    prev_saldo = historical_rows[-1]["saldo"] if historical_rows else None
    for offset in range(projection_years):
        pct_value = growth_map.get(str(offset), None)
        pct_numeric = _float_or_none(_series_to_numeric(pd.Series([pct_value]), percent=True).iloc[0]) if pct_value not in (None, "") else None
        if pct_numeric is None:
            match = df[df["offset"] == offset]
            pct_numeric = _float_or_none(match.iloc[0]["pct"]) if not match.empty else None
        saldo_value = None
        crecimiento_value = None
        if prev_saldo is not None and pct_numeric is not None:
            crecimiento_value = prev_saldo * (pct_numeric / 100.0)
            saldo_value = prev_saldo + crecimiento_value
        else:
            match = df[df["offset"] == offset]
            if not match.empty:
                saldo_value = _float_or_none(match.iloc[0]["saldo"])
                crecimiento_value = _float_or_none(match.iloc[0]["crecimiento"])
        rows_out.append(
            {
                "offset": int(offset),
                "year": start_year + int(offset),
                "saldo": saldo_value,
                "crecimiento": crecimiento_value,
                "pct": pct_numeric,
                "projected": True,
            }
        )
        if saldo_value is not None:
            prev_saldo = saldo_value

    return {
        "rows": rows_out,
        "growth_map": {str(key): str(value or "").strip() for key, value in growth_map.items()},
        "projection_years": projection_years,
    }


def save_crecimiento_general_activo_total_growth(growth_map_raw: Dict[str, Any]) -> Dict[str, Any]:
    store = load_datos_preliminares_store()
    projection_years = _get_projection_years(store)
    normalized_growth_map: Dict[str, str] = {}
    for idx in range(projection_years):
        key = str(idx)
        raw_value = "" if growth_map_raw is None else growth_map_raw.get(key, "")
        numeric = _series_to_numeric(pd.Series([raw_value]), percent=True).iloc[0]
        normalized_growth_map[key] = "" if pd.isna(numeric) else str(round(float(numeric), 2)).rstrip("0").rstrip(".")

    editor_payload = load_crecimiento_general_activo_total_editor(
        {**store, "cg_activo_total_growth_json": json.dumps(normalized_growth_map, ensure_ascii=False)}
    )
    rows_to_save: List[Dict[str, Any]] = []
    for row in editor_payload["rows"]:
        rows_to_save.append(
            {
                "offset": row.get("offset"),
                "year": row.get("year"),
                "saldo": row.get("saldo"),
                "crecimiento": row.get("crecimiento"),
                "pct": row.get("pct"),
                "hasData": True if row.get("saldo") is not None or row.get("pct") is not None else False,
            }
        )
    store["cg_activo_total_growth_json"] = json.dumps(normalized_growth_map, ensure_ascii=False)
    store["cg_activo_total_rows_json"] = json.dumps(rows_to_save, ensure_ascii=False)
    store = sync_ifb_activo_total_from_crecimiento(store)
    save_datos_preliminares_store(store)
    return load_crecimiento_general_activo_total_editor(store)
