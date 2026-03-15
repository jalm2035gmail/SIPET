import json
from typing import Any, Dict, List

import pandas as pd

from fastapi_modulo.modulos.proyectando.modelos.proyectando_store_common import (
    DEFAULT_ACTIVO_FIJO_COMPRAS_ROWS,
    DEFAULT_ACTIVO_FIJO_ROWS,
    _float_or_none,
    _format_amount,
    _format_whole_amount,
    _parse_json_value,
    _series_to_numeric,
    _get_projection_years,
    get_if_period_columns,
    load_datos_preliminares_store,
    load_informacion_financiera_catalogo,
    save_datos_preliminares_store,
)


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
                "values": {str(key): str(value or "").strip() for key, value in values.items()},
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
    row22 = output_rows[21] if len(output_rows) >= 22 else None
    row23 = output_rows[22] if len(output_rows) >= 23 else None
    row30 = output_rows[29] if len(output_rows) >= 30 else None
    row36 = output_rows[35] if len(output_rows) >= 36 else None
    row42 = output_rows[41] if len(output_rows) >= 42 else None
    row1 = output_rows[0] if len(output_rows) >= 1 else None
    row49 = output_rows[48] if len(output_rows) >= 49 else None
    row56 = output_rows[55] if len(output_rows) >= 56 else None
    row70 = output_rows[69] if len(output_rows) >= 70 else None
    row71 = output_rows[70] if len(output_rows) >= 71 else None

    if isinstance(row22, dict):
        values = row22.get("values", {})
        if not isinstance(values, dict):
            values = {}
        for period_key in period_keys:
            row23_value = _series_to_numeric(pd.Series([((row23 or {}).get("values", {}) or {}).get(period_key, "")])).iloc[0]
            row30_value = _series_to_numeric(pd.Series([((row30 or {}).get("values", {}) or {}).get(period_key, "")])).iloc[0]
            row36_value = _series_to_numeric(pd.Series([((row36 or {}).get("values", {}) or {}).get(period_key, "")])).iloc[0]
            row42_value = _series_to_numeric(pd.Series([((row42 or {}).get("values", {}) or {}).get(period_key, "")])).iloc[0]
            total = (
                (0 if pd.isna(row23_value) else float(row23_value))
                + (0 if pd.isna(row30_value) else float(row30_value))
                - (0 if pd.isna(row36_value) else float(row36_value))
                - (0 if pd.isna(row42_value) else float(row42_value))
            )
            values[period_key] = _format_whole_amount(total)
        row22["values"] = values

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


def sync_ifb_financiamiento_from_crecimiento(store: Dict[str, str]) -> Dict[str, str]:
    current_store = dict(store or {})
    if_rows = _build_ifb_rows_for_template(current_store)
    if not if_rows:
        return current_store

    periods = get_if_period_columns(current_store)
    row1 = if_rows[0] if len(if_rows) >= 1 and isinstance(if_rows[0], dict) else None
    row49 = if_rows[48] if len(if_rows) >= 49 and isinstance(if_rows[48], dict) else None
    row56 = if_rows[55] if len(if_rows) >= 56 and isinstance(if_rows[55], dict) else None
    row70 = if_rows[69] if len(if_rows) >= 70 and isinstance(if_rows[69], dict) else None
    if not row1:
        return current_store

    values1 = row1.get("values", {}) if isinstance(row1.get("values"), dict) else {}
    values49 = row49.get("values", {}) if row49 and isinstance(row49.get("values"), dict) else {}
    values56 = row56.get("values", {}) if row56 and isinstance(row56.get("values"), dict) else {}
    values70 = row70.get("values", {}) if row70 and isinstance(row70.get("values"), dict) else {}

    pasivo_pct_rows = _parse_json_value(current_store.get("cg_financiamiento_pasivo_pct_json", ""), {})
    resultado_pct_rows = _parse_json_value(current_store.get("cg_financiamiento_resultado_pct_json", ""), {})
    pasivo_pct_map = pasivo_pct_rows if isinstance(pasivo_pct_rows, dict) else {}
    resultado_pct_map = resultado_pct_rows if isinstance(resultado_pct_rows, dict) else {}

    for period in periods:
        key = str(period["key"])
        if not key.lstrip("-").isdigit() or int(key) < 0:
            continue
        activo = _series_to_numeric(pd.Series([values1.get(key, "")])).iloc[0]
        if pd.isna(activo):
            continue
        pasivo_pct = _series_to_numeric(pd.Series([pasivo_pct_map.get(key, "")]), percent=True).iloc[0]
        resultado_pct = _series_to_numeric(pd.Series([resultado_pct_map.get(key, "")]), percent=True).iloc[0]
        if row49 is not None and not pd.isna(pasivo_pct):
            values49[key] = _format_whole_amount(float(activo) * (float(pasivo_pct) / 100.0))
        if row70 is not None and not pd.isna(resultado_pct):
            values70[key] = _format_whole_amount(float(activo) * (float(resultado_pct) / 100.0))
        if row56 is not None:
            capital_pct = 100.0 - (0.0 if pd.isna(pasivo_pct) else float(pasivo_pct)) - (0.0 if pd.isna(resultado_pct) else float(resultado_pct))
            values56[key] = _format_whole_amount(float(activo) * (capital_pct / 100.0))

    if row49 is not None:
        row49["values"] = values49
    if row56 is not None:
        row56["values"] = values56
    if row70 is not None:
        row70["values"] = values70
    current_store["ifb_rows_json"] = normalize_ifb_rows_json(json.dumps(if_rows, ensure_ascii=False))
    return current_store


def load_ifb_rows_for_template(store: Dict[str, str] | None = None) -> List[Dict[str, Any]]:
    current_store = sync_ifb_activo_total_from_crecimiento(store or load_datos_preliminares_store())
    current_store = sync_ifb_financiamiento_from_crecimiento(current_store)
    return _build_ifb_rows_for_template(current_store)


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


def load_activo_fijo_compras_editor_from_store(store: Dict[str, str]) -> Dict[str, Any]:
    projection_years = _get_projection_years(store)
    start_year = int(get_if_period_columns(store)[3]["label"]) if len(get_if_period_columns(store)) > 3 else 0
    raw_rows = _parse_json_value(store.get("activo_fijo_compras_json", ""), [])
    compras_df = pd.DataFrame(raw_rows if isinstance(raw_rows, list) else [])
    if compras_df.empty:
        compras_df = pd.DataFrame(DEFAULT_ACTIVO_FIJO_COMPRAS_ROWS)
    if "rubro" not in compras_df.columns:
        compras_df["rubro"] = ""
    if "proyecciones" not in compras_df.columns:
        compras_df["proyecciones"] = [[] for _ in range(len(compras_df))]
    compras_df["rubro"] = compras_df["rubro"].fillna("").astype(str).str.strip()
    compras_df["proyecciones"] = compras_df["proyecciones"].apply(
        lambda value: value if isinstance(value, list) else ([] if value in (None, "") else [value])
    )
    compras_df = compras_df[compras_df["rubro"] != ""].reset_index(drop=True)
    if not compras_df.empty:
        projection_columns = []
        for idx in range(projection_years):
            column = f"proj_{idx}"
            compras_df[column] = compras_df["proyecciones"].map(
                lambda values, pos=idx: values[pos] if isinstance(values, list) and len(values) > pos else ""
            )
            compras_df[column] = _series_to_numeric(compras_df[column])
            projection_columns.append(column)
        mask_total = compras_df["rubro"].str.upper().eq("PROPIEDADES, MOBILIARIO Y EQUIPO")
        if mask_total.any():
            total_idx = compras_df.index[mask_total][0]
            detail_df = compras_df.loc[~mask_total, projection_columns]
            compras_df.loc[total_idx, projection_columns] = detail_df.sum(axis=0, min_count=1).fillna(0)
            compras_df.at[total_idx, "proyecciones"] = [
                "" if pd.isna(compras_df.at[total_idx, column]) else _format_whole_amount(compras_df.at[total_idx, column])
                for column in projection_columns
            ]
    years = [start_year + idx for idx in range(projection_years)]
    rows_out: List[Dict[str, Any]] = []
    for record in compras_df.to_dict(orient="records"):
        projections = []
        values = record.get("proyecciones") if isinstance(record.get("proyecciones"), list) else []
        for idx in range(projection_years):
            numeric = _series_to_numeric(pd.Series([values[idx] if len(values) > idx else ""])).iloc[0]
            projections.append(_format_whole_amount(numeric) if not pd.isna(numeric) else "")
        rows_out.append({"rubro": record.get("rubro", ""), "proyecciones": projections})
    return {"years": years, "rows": rows_out}


def load_activo_fijo_compras_editor() -> Dict[str, Any]:
    return load_activo_fijo_compras_editor_from_store(load_datos_preliminares_store())


def save_activo_fijo_compras_editor(rows_raw: List[Dict[str, Any]]) -> Dict[str, Any]:
    store = load_datos_preliminares_store()
    projection_years = _get_projection_years(store)
    incoming = rows_raw if isinstance(rows_raw, list) else []
    compras_df = pd.DataFrame(incoming if incoming else DEFAULT_ACTIVO_FIJO_COMPRAS_ROWS)
    if "rubro" not in compras_df.columns:
        compras_df["rubro"] = ""
    if "proyecciones" not in compras_df.columns:
        compras_df["proyecciones"] = [[] for _ in range(len(compras_df))]
    compras_df["rubro"] = compras_df["rubro"].fillna("").astype(str).str.strip()
    compras_df["proyecciones"] = compras_df["proyecciones"].apply(
        lambda value: value if isinstance(value, list) else ([] if value in (None, "") else [value])
    )
    projection_columns = []
    for idx in range(projection_years):
        column = f"proj_{idx}"
        compras_df[column] = compras_df["proyecciones"].map(
            lambda values, pos=idx: values[pos] if isinstance(values, list) and len(values) > pos else ""
        )
        compras_df[column] = _series_to_numeric(compras_df[column])
        projection_columns.append(column)
    mask_total = compras_df["rubro"].str.upper().eq("PROPIEDADES, MOBILIARIO Y EQUIPO")
    if mask_total.any():
        total_idx = compras_df.index[mask_total][0]
        detail_df = compras_df.loc[~mask_total, projection_columns]
        compras_df.loc[total_idx, projection_columns] = detail_df.sum(axis=0, min_count=1).fillna(0)
    safe_rows: List[Dict[str, Any]] = []
    for record in compras_df.to_dict(orient="records"):
        rubro = str(record.get("rubro") or "").strip()
        if not rubro:
            continue
        normalized_values: List[str] = []
        for idx in range(projection_years):
            numeric = record.get(f"proj_{idx}", pd.NA)
            normalized_values.append("" if pd.isna(numeric) else _format_whole_amount(numeric))
        safe_rows.append({"rubro": rubro, "proyecciones": normalized_values})
    store["activo_fijo_compras_json"] = json.dumps(safe_rows, ensure_ascii=False)
    saldos_payload = load_activo_fijo_saldos_editor_from_store({**store, "activo_fijo_compras_json": json.dumps(safe_rows, ensure_ascii=False)})
    if_rows = _parse_json_value(store.get("ifb_rows_json", ""), [])
    row_targets = {
        "Propiedades, mobiliario y equipo": 23,
        "Terrenos": 24,
        "Construcciones": 25,
        "Equipo de transporte": 26,
        "Equipo de cómputo": 27,
        "Mobiliario": 28,
        "Adaptaciones y mejoras": 29,
    }
    periods = get_if_period_columns(store)
    if isinstance(if_rows, list):
        for saldo_row in saldos_payload.get("rows", []):
            if not isinstance(saldo_row, dict):
                continue
            row_index = row_targets.get(str(saldo_row.get("rubro") or "").strip())
            if not row_index or row_index > len(if_rows):
                continue
            target = if_rows[row_index - 1]
            if not isinstance(target, dict):
                continue
            values = target.get("values", {}) if isinstance(target.get("values"), dict) else {}
            saldo_values = saldo_row.get("values") if isinstance(saldo_row.get("values"), list) else []
            for idx, period in enumerate(periods):
                key = str(period.get("key", ""))
                if key.lstrip("-").isdigit() and int(key) >= 0:
                    values[key] = str(saldo_values[idx] or "").strip() if idx < len(saldo_values) else ""
            target["values"] = values
        store["ifb_rows_json"] = normalize_ifb_rows_json(json.dumps(if_rows, ensure_ascii=False))
    save_datos_preliminares_store(store)
    return load_activo_fijo_compras_editor()


def load_activo_fijo_saldos_editor_from_store(store: Dict[str, str]) -> Dict[str, Any]:
    periods = get_if_period_columns(store)
    if_rows = _parse_json_value(store.get("ifb_rows_json", ""), [])
    compras = load_activo_fijo_compras_editor_from_store(store)
    compras_rows = compras.get("rows", []) if isinstance(compras, dict) else []
    compras_map = {
        str(item.get("rubro") or "").strip(): (item.get("proyecciones") if isinstance(item.get("proyecciones"), list) else [])
        for item in compras_rows
        if isinstance(item, dict)
    }
    row_map_by_index: Dict[int, Dict[str, Any]] = {}
    if isinstance(if_rows, list):
        for idx, row in enumerate(if_rows, start=1):
            if isinstance(row, dict):
                row_map_by_index[idx] = row

    rubros = [
        ("Propiedades, mobiliario y equipo", 23),
        ("Terrenos", 24),
        ("Construcciones", 25),
        ("Equipo de transporte", 26),
        ("Equipo de cómputo", 27),
        ("Mobiliario", 28),
        ("Adaptaciones y mejoras", 29),
    ]
    computed_amounts: Dict[str, List[float | None]] = {}
    detail_rubros = [item for item in rubros if item[0] != "Propiedades, mobiliario y equipo"]

    for label, row_index in detail_rubros:
        row = row_map_by_index.get(row_index, {})
        values = row.get("values", {}) if isinstance(row, dict) and isinstance(row.get("values"), dict) else {}
        projections = compras_map.get(label, [])
        rendered_amounts: List[float | None] = []
        proj_pos = 0
        previous_amount: float | None = None
        for period in periods:
            key = str(period.get("key", ""))
            if key.lstrip("-").isdigit() and int(key) >= 0:
                compra_raw = projections[proj_pos] if proj_pos < len(projections) else ""
                compra_amount = _float_or_none(_series_to_numeric(pd.Series([compra_raw])).iloc[0])
                saldo_amount: float | None = None
                if previous_amount is not None:
                    saldo_amount = previous_amount + (0.0 if compra_amount is None else float(compra_amount))
                elif compra_amount is not None:
                    saldo_amount = float(compra_amount)
                rendered_amounts.append(saldo_amount)
                if saldo_amount is not None:
                    previous_amount = saldo_amount
                proj_pos += 1
            else:
                hist_amount = _float_or_none(_series_to_numeric(pd.Series([values.get(key) or ""])).iloc[0])
                rendered_amounts.append(hist_amount)
                if hist_amount is not None:
                    previous_amount = hist_amount
        computed_amounts[label] = rendered_amounts

    total_values: List[float | None] = []
    for idx in range(len(periods)):
        values_for_period = [
            row_values[idx]
            for row_values in computed_amounts.values()
            if idx < len(row_values) and row_values[idx] is not None
        ]
        total_values.append(sum(values_for_period) if values_for_period else None)

    rows_out: List[Dict[str, Any]] = [
        {"rubro": "Propiedades, mobiliario y equipo", "values": [_format_whole_amount(value) if value is not None else "" for value in total_values]}
    ]
    for label, _ in detail_rubros:
        row_values = computed_amounts.get(label, [])
        rows_out.append({"rubro": label, "values": [_format_whole_amount(value) if value is not None else "" for value in row_values]})
    return {"periods": [{"key": str(period["key"]), "label": str(period["label"])} for period in periods], "rows": rows_out}


def load_activo_fijo_saldos_editor() -> Dict[str, Any]:
    return load_activo_fijo_saldos_editor_from_store(load_datos_preliminares_store())


def load_activo_fijo_revaluaciones_editor() -> Dict[str, Any]:
    store = load_datos_preliminares_store()
    periods = get_if_period_columns(store)
    if_rows = _parse_json_value(store.get("ifb_rows_json", ""), [])
    row_map_by_index: Dict[int, Dict[str, Any]] = {}
    if isinstance(if_rows, list):
        for idx, row in enumerate(if_rows, start=1):
            if isinstance(row, dict):
                row_map_by_index[idx] = row
    rubros = [("Terrenos", 31), ("Construcciones", 32), ("Equipo de cómputo", 33), ("Mobiliario", 34), ("Adaptaciones y mejoras", 35)]
    rows_out: List[Dict[str, Any]] = []
    for label, row_index in rubros:
        row = row_map_by_index.get(row_index, {})
        values = row.get("values", {}) if isinstance(row, dict) and isinstance(row.get("values"), dict) else {}
        rendered_values: List[str] = []
        for period in periods:
            amount = _float_or_none(_series_to_numeric(pd.Series([values.get(str(period.get("key", "")), "")])).iloc[0])
            rendered_values.append(_format_whole_amount(amount) if amount is not None else "")
        rows_out.append({"rubro": label, "values": rendered_values})
    return {"periods": [{"key": str(period["key"]), "label": str(period["label"])} for period in periods], "rows": rows_out}


def load_activo_fijo_depreciacion_editor() -> Dict[str, Any]:
    store = load_datos_preliminares_store()
    periods = get_if_period_columns(store)
    if_rows = _parse_json_value(store.get("ifb_rows_json", ""), [])
    row_map_by_index: Dict[int, Dict[str, Any]] = {}
    if isinstance(if_rows, list):
        for idx, row in enumerate(if_rows, start=1):
            if isinstance(row, dict):
                row_map_by_index[idx] = row
    rubros = [
        ("Propiedades, mobiliario y equipo", 36),
        ("Terrenos", None),
        ("Construcciones", 37),
        ("Equipo de transporte", 38),
        ("Equipo de cómputo", 39),
        ("Mobiliario", 40),
        ("Adaptaciones y mejoras", 41),
    ]
    rows_out: List[Dict[str, Any]] = []
    for label, row_index in rubros:
        rendered_values: List[str] = []
        if row_index is None:
            rendered_values = ["" for _ in periods]
        else:
            row = row_map_by_index.get(row_index, {})
            values = row.get("values", {}) if isinstance(row, dict) and isinstance(row.get("values"), dict) else {}
            for period in periods:
                amount = _float_or_none(_series_to_numeric(pd.Series([values.get(str(period.get("key", "")), "")])).iloc[0])
                rendered_values.append(_format_whole_amount(amount) if amount is not None else "")
        rows_out.append({"rubro": label, "values": rendered_values})
    return {"periods": [{"key": str(period["key"]), "label": str(period["label"])} for period in periods], "rows": rows_out}


def load_gastos_resumen() -> Dict[str, Any]:
    store = load_datos_preliminares_store()
    projection_years = _get_projection_years(store)
    rows = _parse_json_value(store.get("gastos_rows_json", ""), [])
    gastos_df = pd.DataFrame(rows if isinstance(rows, list) else [])
    if gastos_df.empty:
        return {"rows": [], "projection_years": projection_years, "summary": {"total": 0, "niveles": "", "capturados": 0}}
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
        "summary": {"total": int(len(output_rows)), "niveles": ", ".join(str(level) for level in niveles), "capturados": int(captured_mask.sum())},
    }
