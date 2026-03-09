import json
from typing import Any, Dict, List

import pandas as pd

from fastapi_modulo.modulos.proyectando.proyectando_store_common import (
    _float_or_none,
    _format_amount,
    _format_percent,
    _format_whole_amount,
    _get_projection_years,
    _humanize_financiamiento_label,
    _parse_json_value,
    _series_to_numeric,
    get_if_period_columns,
    load_datos_preliminares_store,
    save_datos_preliminares_store,
)
from fastapi_modulo.modulos.proyectando.datos_preliminares_store import (
    normalize_ifb_rows_json,
    sync_ifb_activo_total_from_crecimiento,
    sync_ifb_financiamiento_from_crecimiento,
)


def load_crecimiento_general_activo_total_editor(store: Dict[str, str] | None = None) -> Dict[str, Any]:
    current_store = store or load_datos_preliminares_store()
    projection_years = _get_projection_years(current_store)
    start_year = int(get_if_period_columns(current_store)[3]["label"]) if len(get_if_period_columns(current_store)) > 3 else 0
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

    return {"rows": rows_out, "growth_map": {str(key): str(value or "").strip() for key, value in growth_map.items()}, "projection_years": projection_years}


def load_crecimiento_general_resumen() -> Dict[str, List[Dict[str, Any]]]:
    store = load_datos_preliminares_store()
    projection_years = _get_projection_years(store)
    activo_rows = load_crecimiento_general_activo_total_editor(store)["rows"]
    financiamiento_rows = _parse_json_value(store.get("cg_financiamiento_rows_json", ""), {})
    standard_rows = _parse_json_value(store.get("cg_financiamiento_standard_json", ""), {})
    pasivo_pct_rows = _parse_json_value(store.get("cg_financiamiento_pasivo_pct_json", ""), {})
    resultado_pct_rows = _parse_json_value(store.get("cg_financiamiento_resultado_pct_json", ""), {})
    if_periods = get_if_period_columns(store)
    if_rows = _parse_json_value(store.get("ifb_rows_json", ""), [])

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
        activo_df = activo_df[activo_df["offset"].between(-3, projection_years - 1, inclusive="both")]
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

    financiamiento_activo_rows: List[Dict[str, Any]] = []
    pasivo_capital_rows: List[Dict[str, Any]] = []
    capital_detalle_rows: List[Dict[str, Any]] = []
    crecimiento_detalle_rows: List[Dict[str, Any]] = []
    standards_map = {"Pasivo": "80", "Capital": "18", "Resultado": "2"}
    pasivo_pct_map: Dict[str, str] = {}
    resultado_pct_map: Dict[str, str] = {}
    if isinstance(standard_rows, dict):
        for key in ("Pasivo", "Capital", "Resultado"):
            value = standard_rows.get(key, standards_map.get(key, ""))
            numeric = _series_to_numeric(pd.Series([value]), percent=True).iloc[0]
            if not pd.isna(numeric):
                standards_map[key] = str(round(float(numeric), 2)).rstrip("0").rstrip(".")
    if isinstance(pasivo_pct_rows, dict):
        for key, value in pasivo_pct_rows.items():
            numeric = _series_to_numeric(pd.Series([value]), percent=True).iloc[0]
            if not pd.isna(numeric):
                pasivo_pct_map[str(key)] = str(round(float(numeric), 2)).rstrip("0").rstrip(".")
    if isinstance(resultado_pct_rows, dict):
        for key, value in resultado_pct_rows.items():
            numeric = _series_to_numeric(pd.Series([value]), percent=True).iloc[0]
            if not pd.isna(numeric):
                resultado_pct_map[str(key)] = str(round(float(numeric), 2)).rstrip("0").rstrip(".")
    if isinstance(if_rows, list) and if_periods:
        row_map_by_index: Dict[int, Dict[str, Any]] = {}
        row_map_by_cuenta: Dict[str, Dict[str, Any]] = {}
        for idx, row in enumerate(if_rows, start=1):
            if isinstance(row, dict):
                row_map_by_index[idx] = row
                row_map_by_cuenta[str(row.get("cuenta") or "").strip()] = row

        def _row_values(index: int) -> Dict[str, Any]:
            row = row_map_by_index.get(index, {})
            values = row.get("values", {})
            return values if isinstance(values, dict) else {}

        def _amount_for(index: int, period_key: str) -> float | None:
            values = _row_values(index)
            return _float_or_none(_series_to_numeric(pd.Series([values.get(period_key, "")])).iloc[0])

        def _effective_amount(label: str, source_index: int, period_key: str) -> float | None:
            current = _amount_for(source_index, period_key)
            activo_total = _amount_for(1, period_key)
            if label == "Pasivo" and period_key.lstrip("-").isdigit() and int(period_key) >= 0:
                pct_override = pasivo_pct_map.get(period_key, "")
                pct_numeric = _series_to_numeric(pd.Series([pct_override]), percent=True).iloc[0] if pct_override != "" else pd.NA
                if activo_total not in (None, 0) and not pd.isna(pct_numeric):
                    current = float(activo_total) * (float(pct_numeric) / 100.0)
            if label == "Resultado" and period_key.lstrip("-").isdigit() and int(period_key) >= 0:
                pct_override = resultado_pct_map.get(period_key, "")
                pct_numeric = _series_to_numeric(pd.Series([pct_override]), percent=True).iloc[0] if pct_override != "" else pd.NA
                if activo_total not in (None, 0) and not pd.isna(pct_numeric):
                    current = float(activo_total) * (float(pct_numeric) / 100.0)
            if label == "Capital" and period_key.lstrip("-").isdigit() and int(period_key) >= 0:
                pasivo_pct_numeric = _series_to_numeric(pd.Series([pasivo_pct_map.get(period_key, "")]), percent=True).iloc[0]
                resultado_pct_numeric = _series_to_numeric(pd.Series([resultado_pct_map.get(period_key, "")]), percent=True).iloc[0]
                if activo_total not in (None, 0):
                    capital_pct = 100.0 - (0.0 if pd.isna(pasivo_pct_numeric) else float(pasivo_pct_numeric)) - (0.0 if pd.isna(resultado_pct_numeric) else float(resultado_pct_numeric))
                    current = float(activo_total) * (capital_pct / 100.0)
            return current

        def _growth_rows(label: str, source_index: int) -> List[Dict[str, Any]]:
            amount_row: Dict[str, Any] = {"label": label, "kind": "amount", "values": []}
            growth_row: Dict[str, Any] = {"label": "% activo", "kind": "growth", "values": []}
            for period in if_periods:
                period_key = str(period["key"])
                current = _effective_amount(label, source_index, period_key)
                activo_total = _amount_for(1, period["key"])
                amount_row["values"].append(_format_amount(current))
                pct_value: float | None = None
                if activo_total not in (None, 0) and current is not None:
                    pct_value = (current / activo_total) * 100.0
                growth_row["values"].append(_format_percent(pct_value))
            return [amount_row, growth_row]

        financiamiento_activo_rows.extend(_growth_rows("Activo total", 1))
        financiamiento_activo_rows.extend(_growth_rows("Pasivo", 49))
        financiamiento_activo_rows.extend(_growth_rows("Capital", 56))
        financiamiento_activo_rows.extend(_growth_rows("Resultado", 70))

        for growth_label, source_index in (("Activo total", 1), ("Pasivo", 49), ("Capital", 56)):
            growth_values: List[str] = []
            previous_amount: float | None = None
            for period in if_periods:
                period_key = str(period["key"])
                current_amount = _effective_amount(growth_label, source_index, period_key)
                pct_growth: float | None = None
                if previous_amount not in (None, 0) and current_amount is not None:
                    pct_growth = ((current_amount - previous_amount) / previous_amount) * 100.0
                growth_values.append(_format_percent(pct_growth))
                previous_amount = current_amount if current_amount is not None else previous_amount
            crecimiento_detalle_rows.append({"label": growth_label, "kind": "growth", "values": growth_values})

        validacion_amount = {"label": "Validación", "kind": "amount", "values": []}
        for period in if_periods:
            activo = _amount_for(1, period["key"]) or 0.0
            pasivo = _amount_for(49, period["key"]) or 0.0
            capital = _amount_for(56, period["key"]) or 0.0
            resultado = _amount_for(70, period["key"]) or 0.0
            validacion_amount["values"].append(_format_amount(activo - pasivo - capital - resultado))
        financiamiento_activo_rows.append(validacion_amount)

        pasivo_rubros = [
            ("Pasivo", 49),
            ("Captación tradicional", 50),
            ("Prestamos bancarios", 53),
            ("Otras cuentas por pagar", 54),
            ("Crédito diferidos y cobros anticipados", 55),
        ]
        for label, row_index in pasivo_rubros:
            amount_row: Dict[str, Any] = {"label": label, "kind": "amount", "values": []}
            for period in if_periods:
                amount = _amount_for(row_index, str(period["key"]))
                amount_row["values"].append(_format_amount(amount))
            pasivo_capital_rows.append(amount_row)

        capital_rubros = [
            ("Capital contable", 56),
            ("Capital contribuido", 57),
            ("Capital ganado", 58),
            ("Otras cuentas de capital", 59),
        ]
        for label, row_index in capital_rubros:
            amount_row = {"label": label, "kind": "amount", "values": []}
            for period in if_periods:
                amount = _amount_for(row_index, str(period["key"]))
                amount_row["values"].append(_format_amount(amount))
            capital_detalle_rows.append(amount_row)

    return {
        "activo_total": activo_table,
        "pasivo_total": pasivo_table,
        "patrimonio": patrimonio_table,
        "financiamiento_activo": {
            "periods": [{"key": str(period["key"]), "label": str(period["label"])} for period in if_periods],
            "rows": financiamiento_activo_rows,
            "standards": standards_map,
            "pasivo_pct_map": pasivo_pct_map,
            "resultado_pct_map": resultado_pct_map,
        },
        "pasivo_capital_detalle": {"periods": [{"key": str(period["key"]), "label": str(period["label"])} for period in if_periods], "rows": pasivo_capital_rows},
        "capital_detalle": {"periods": [{"key": str(period["key"]), "label": str(period["label"])} for period in if_periods], "rows": capital_detalle_rows},
        "crecimiento_detalle": {"periods": [{"key": str(period["key"]), "label": str(period["label"])} for period in if_periods], "rows": crecimiento_detalle_rows},
    }


def save_crecimiento_general_financiamiento_standards(
    standards_raw: Dict[str, Any],
    pasivo_pct_raw: Dict[str, Any] | None = None,
    resultado_pct_raw: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    store = load_datos_preliminares_store()
    defaults = {"Pasivo": "80", "Capital": "18", "Resultado": "2"}
    normalized: Dict[str, str] = {}
    incoming = standards_raw if isinstance(standards_raw, dict) else {}
    for key, default in defaults.items():
        raw_value = incoming.get(key, default)
        numeric = _series_to_numeric(pd.Series([raw_value]), percent=True).iloc[0]
        normalized[key] = default if pd.isna(numeric) else str(round(float(numeric), 2)).rstrip("0").rstrip(".")
    store["cg_financiamiento_standard_json"] = json.dumps(normalized, ensure_ascii=False)
    normalized_pasivo_pct: Dict[str, str] = {}
    normalized_resultado_pct: Dict[str, str] = {}
    incoming_pasivo = pasivo_pct_raw if isinstance(pasivo_pct_raw, dict) else {}
    incoming_resultado = resultado_pct_raw if isinstance(resultado_pct_raw, dict) else {}
    periods = get_if_period_columns(store)
    if_rows = _parse_json_value(store.get("ifb_rows_json", ""), [])
    row49 = if_rows[48] if isinstance(if_rows, list) and len(if_rows) >= 49 and isinstance(if_rows[48], dict) else None
    row56 = if_rows[55] if isinstance(if_rows, list) and len(if_rows) >= 56 and isinstance(if_rows[55], dict) else None
    row70 = if_rows[69] if isinstance(if_rows, list) and len(if_rows) >= 70 and isinstance(if_rows[69], dict) else None
    row49_values = row49.get("values", {}) if isinstance(row49, dict) and isinstance(row49.get("values"), dict) else {}
    row56_values = row56.get("values", {}) if isinstance(row56, dict) and isinstance(row56.get("values"), dict) else {}
    row70_values = row70.get("values", {}) if isinstance(row70, dict) and isinstance(row70.get("values"), dict) else {}
    for period in periods:
        key = str(period["key"])
        if not key.lstrip("-").isdigit() or int(key) < 0:
            continue
        raw_value = incoming_pasivo.get(key, "")
        numeric = _series_to_numeric(pd.Series([raw_value]), percent=True).iloc[0]
        if not pd.isna(numeric):
            normalized_pasivo_pct[key] = str(round(float(numeric), 2)).rstrip("0").rstrip(".")
        raw_resultado = incoming_resultado.get(key, "")
        resultado_numeric = _series_to_numeric(pd.Series([raw_resultado]), percent=True).iloc[0]
        if not pd.isna(resultado_numeric):
            normalized_resultado_pct[key] = str(round(float(resultado_numeric), 2)).rstrip("0").rstrip(".")
    store["cg_financiamiento_pasivo_pct_json"] = json.dumps(normalized_pasivo_pct, ensure_ascii=False)
    store["cg_financiamiento_resultado_pct_json"] = json.dumps(normalized_resultado_pct, ensure_ascii=False)
    if isinstance(if_rows, list):
        row1 = if_rows[0] if len(if_rows) >= 1 and isinstance(if_rows[0], dict) else None
        row1_values = row1.get("values", {}) if isinstance(row1, dict) and isinstance(row1.get("values"), dict) else {}
        if row49 is not None:
            values49 = dict(row49_values)
            for key, pct_str in normalized_pasivo_pct.items():
                activo = _series_to_numeric(pd.Series([row1_values.get(key, "")])).iloc[0]
                pct_num = _series_to_numeric(pd.Series([pct_str]), percent=True).iloc[0]
                if pd.isna(activo) or pd.isna(pct_num):
                    continue
                values49[key] = _format_whole_amount(float(activo) * (float(pct_num) / 100.0))
            row49["values"] = values49
        if row56 is not None:
            values56 = dict(row56_values)
            for period in periods:
                key = str(period["key"])
                if not key.lstrip("-").isdigit() or int(key) < 0:
                    continue
                activo = _series_to_numeric(pd.Series([row1_values.get(key, "")])).iloc[0]
                pasivo_pct_num = _series_to_numeric(pd.Series([normalized_pasivo_pct.get(key, "")]), percent=True).iloc[0]
                resultado_pct_num = _series_to_numeric(pd.Series([normalized_resultado_pct.get(key, "")]), percent=True).iloc[0]
                if pd.isna(activo):
                    continue
                capital_pct = 100.0 - (0.0 if pd.isna(pasivo_pct_num) else float(pasivo_pct_num)) - (0.0 if pd.isna(resultado_pct_num) else float(resultado_pct_num))
                values56[key] = _format_whole_amount(float(activo) * (capital_pct / 100.0))
            row56["values"] = values56
        if row70 is not None:
            values70 = dict(row70_values)
            for key, pct_str in normalized_resultado_pct.items():
                activo = _series_to_numeric(pd.Series([row1_values.get(key, "")])).iloc[0]
                pct_num = _series_to_numeric(pd.Series([pct_str]), percent=True).iloc[0]
                if pd.isna(activo) or pd.isna(pct_num):
                    continue
                values70[key] = _format_whole_amount(float(activo) * (float(pct_num) / 100.0))
            row70["values"] = values70
        store["ifb_rows_json"] = normalize_ifb_rows_json(json.dumps(if_rows, ensure_ascii=False))
        store = sync_ifb_financiamiento_from_crecimiento(store)
    save_datos_preliminares_store(store)
    return load_crecimiento_general_resumen().get("financiamiento_activo", {})


def save_crecimiento_general_activo_total_growth(growth_map_raw: Dict[str, Any]) -> Dict[str, Any]:
    store = load_datos_preliminares_store()
    projection_years = _get_projection_years(store)
    normalized_growth_map: Dict[str, str] = {}
    for idx in range(projection_years):
        key = str(idx)
        raw_value = "" if growth_map_raw is None else growth_map_raw.get(key, "")
        numeric = _series_to_numeric(pd.Series([raw_value]), percent=True).iloc[0]
        normalized_growth_map[key] = "" if pd.isna(numeric) else str(round(float(numeric), 2)).rstrip("0").rstrip(".")

    editor_payload = load_crecimiento_general_activo_total_editor({**store, "cg_activo_total_growth_json": json.dumps(normalized_growth_map, ensure_ascii=False)})
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
