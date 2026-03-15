from __future__ import annotations

from typing import Any
import re

from fastapi_modulo.modulos.brujula.modelos.enums import AnalysisFormatKind, AnalysisFormulaKind
from fastapi_modulo.modulos.brujula.servicios.projection_service import (
    build_financial_indicator_context,
    safe_growth,
)


def format_indicator_percent(value: float | None) -> str:
    if value is None:
        return ""
    return f"{float(value):,.2f}%"


def format_indicator_amount(value: float | None) -> str:
    if value is None:
        return ""
    rounded = round(float(value), 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return f"{int(round(rounded)):,}"
    return f"{rounded:,.2f}"


def format_indicator_number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{int(round(float(value))):,}"


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or abs(float(denominator)) < 1e-9:
        return None
    return float(numerator) / float(denominator)


def coalesce_numeric(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return float(value)
    return None


def sum_numeric(*values: float | None) -> float | None:
    present = [float(value) for value in values if value is not None]
    if not present:
        return None
    return sum(present)


def average_numeric(*values: float | None) -> float | None:
    present = [float(value) for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def percent_value(numerator: float | None, denominator: float | None) -> float | None:
    ratio = safe_divide(numerator, denominator)
    if ratio is None:
        return None
    return ratio * 100.0


def difference_value(left: float | None, right: float | None) -> float | None:
    if left is None and right is None:
        return None
    return float(left or 0.0) - float(right or 0.0)


def parse_meta_rule(meta: str | None) -> dict[str, float] | None:
    raw = str(meta or "").strip()
    if not raw or raw.lower() == "n/a":
        return None
    match = re.match(r"^(>=|<=|>|<|=)?\s*(-?\d+(?:\.\d+)?)\s*%?$", raw)
    if not match:
        return None
    return {
        "operator": str(match.group(1) or ">="),
        "target": float(match.group(2)),
    }


def evaluate_indicator_status(value: str | None, meta: str | None) -> str:
    numeric_value = parse_number_like(value)
    rule = parse_meta_rule(meta)
    if numeric_value is None or rule is None:
        return "na"
    operator = str(rule["operator"])
    target = float(rule["target"])
    if operator == ">=":
        return "ok" if numeric_value >= target else "fail"
    if operator == "<=":
        return "ok" if numeric_value <= target else "fail"
    if operator == ">":
        return "ok" if numeric_value > target else "fail"
    if operator == "<":
        return "ok" if numeric_value < target else "fail"
    return "ok" if numeric_value == target else "fail"


def parse_number_like(value: str | float | int | None) -> float | None:
    raw = str(value or "").replace(",", "").replace("%", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def calculate_brujula_indicator_values(
    periods: list[dict],
    fixed_indicator_names: list[str],
    store: dict[str, str] | None = None,
) -> dict[str, dict[str, str]]:
    context = build_financial_indicator_context(periods, store)
    get_value = context["get_value"]
    period_keys = context["period_keys"]
    calculated: dict[str, dict[str, str]] = {name: {key: "" for key in period_keys} for name in fixed_indicator_names}

    def assign_percent(name: str, resolver) -> None:
        for period_key in period_keys:
            calculated[name][period_key] = format_indicator_percent(resolver(period_key))

    def assign_amount(name: str, resolver) -> None:
        for period_key in period_keys:
            calculated[name][period_key] = format_indicator_amount(resolver(period_key))

    def assign_number(name: str, resolver) -> None:
        for period_key in period_keys:
            calculated[name][period_key] = format_indicator_number(resolver(period_key))

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
        return sum_numeric(cartera_vigente(period_key), cartera_vencida(period_key))

    def cartera_neta(period_key: str) -> float | None:
        return difference_value(cartera_total(period_key), estimacion_crediticia(period_key))

    def depositos_ahorro(period_key: str) -> float | None:
        return get_value("201-00-00-00-00-000", period_key)

    def depositos_vista(period_key: str) -> float | None:
        return coalesce_numeric(get_value("201-01-00-00-00-000", period_key), depositos_ahorro(period_key))

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
        return coalesce_numeric(get_value("501-00-00-00-00-000", period_key), gastos_total(period_key))

    def gastos_administracion(period_key: str) -> float | None:
        return get_value("505-00-00-00-00-000", period_key)

    def resultado_neto(period_key: str) -> float | None:
        return get_value("__resultado__", period_key)

    def socios(period_key: str) -> float | None:
        return get_value("__metric_socios__", period_key)

    def empleados(period_key: str) -> float | None:
        return get_value("__metric_empleados__", period_key)

    def activos_improductivos(period_key: str) -> float | None:
        return sum_numeric(
            get_value("107-00-00-00-00-000", period_key),
            get_value("108-00-00-00-00-000", period_key),
            get_value("109-00-00-00-00-000", period_key),
            get_value("110-00-00-00-00-000", period_key),
            get_value("113-00-00-00-00-000", period_key),
        )

    def liquidez_inmediata(period_key: str) -> float | None:
        return sum_numeric(disponibilidades(period_key), inversiones(period_key))

    def previous_period_value(series_resolver, period_key: str) -> float | None:
        try:
            index = period_keys.index(period_key)
        except ValueError:
            return None
        if index <= 0:
            return None
        return series_resolver(period_keys[index - 1])

    assign_percent("C2 - Indice de capitalizacion", lambda key: percent_value(capital_contable(key), activo_total(key)))
    assign_percent("C3 - Solvencia", lambda key: percent_value(cartera_neta(key), activo_total(key)))
    assign_percent("C4 - Credito neto en riesgo", lambda key: percent_value(cartera_vencida(key), cartera_total(key)))
    assign_percent("C5 - Cobertura de morosidad", lambda key: percent_value(estimacion_crediticia(key), cartera_vencida(key)))
    assign_percent("C6 - Cobertura de obligaciones a la vista", lambda key: percent_value(liquidez_inmediata(key), depositos_vista(key)))
    assign_percent("C7 - Fondeo de activos improductivos", lambda key: percent_value(activos_improductivos(key), capital_contable(key)))
    assign_percent("C8 - Cobertura de gastos con ingresos", lambda key: percent_value(ingresos(key), gastos_total(key)))
    assign_percent("C9 - Autosuficiencia operativa", lambda key: percent_value(gastos_administracion(key), ingresos(key)))
    assign_percent("C10 - ROA", lambda key: percent_value(resultado_neto(key), activo_total(key)))
    assign_amount("C11 - Margen financiero bruto", lambda key: difference_value(ingresos(key), gastos_financieros(key)))

    assign_percent("O1 - Inversiones sobre activo total", lambda key: percent_value(inversiones(key), activo_total(key)))
    assign_percent("O2 - Financiamiento externo sobre activo total", lambda key: percent_value(prestamos_externos(key), activo_total(key)))
    assign_percent("O3 - Depositos de ahorro sobre activo total", lambda key: percent_value(depositos_ahorro(key), activo_total(key)))
    assign_percent("O4 - Capital social sobre activo total", lambda key: percent_value(capital_social(key), activo_total(key)))
    assign_percent("O5 - Reservas sobre activo total", lambda key: percent_value(reservas(key), activo_total(key)))
    assign_percent("O6 - Reservas sobre capital contable", lambda key: percent_value(reservas(key), capital_contable(key)))
    assign_amount("O7 - Capital no comprometido", capital_contable)
    assign_percent("O9 - Activos improductivos sobre activo total", lambda key: percent_value(activos_improductivos(key), activo_total(key)))

    assign_percent("A1 - Rendimiento sobre cartera promedio", lambda key: percent_value(ingresos(key), average_numeric(cartera_total(key), previous_period_value(cartera_total, key))))
    assign_percent("A3 - Costo financiero sobre depositos promedio", lambda key: percent_value(gastos_financieros(key), average_numeric(depositos_ahorro(key), previous_period_value(depositos_ahorro, key))))
    assign_percent("A4 - Costo financiero por depositos", lambda key: percent_value(gastos_financieros(key), prestamos_externos(key)))
    assign_percent("A5 - Retorno sobre patrimonio", lambda key: percent_value(resultado_neto(key), capital_contable(key)))
    assign_percent("A6 - Cobertura liquida del ahorro", lambda key: percent_value(liquidez_inmediata(key), depositos_ahorro(key)))
    assign_percent("A7 - Cobertura liquida de depositos a la vista", lambda key: percent_value(liquidez_inmediata(key), depositos_vista(key)))
    assign_percent("A8 - Cobertura liquida de financiamiento externo", lambda key: percent_value(liquidez_inmediata(key), prestamos_externos(key)))

    assign_percent("Cr1 - Crecimiento de cartera vigente", lambda key: context["series_growth"]("104-00-00-00-00-000", key))
    assign_percent("Cr2 - Crecimiento de inversiones", lambda key: context["series_growth"]("102-00-00-00-00-000", key))
    assign_percent("Cr3 - Crecimiento de depositos de ahorro", lambda key: context["series_growth"]("201-00-00-00-00-000", key))
    assign_percent("Cr4 - Crecimiento de financiamiento externo", lambda key: context["series_growth"]("202-00-00-00-00-000", key))
    assign_percent("Cr5 - Crecimiento de capital social", lambda key: context["series_growth"]("301-00-00-00-00-000", key))
    assign_percent("Cr6 - Crecimiento de reservas", lambda key: context["series_growth"]("302-00-00-00-00-000", key))
    assign_percent("Cr7 - Crecimiento de socios", lambda key: context["series_growth"]("__metric_socios__", key))
    assign_percent("Cr8 - Crecimiento de activos totales", lambda key: context["series_growth"]("100-00-00-00-00-000", key))

    assign_amount("P2 - Ahorro promedio por socio", lambda key: safe_divide(depositos_ahorro(key), socios(key)))
    assign_number("P5 - Socios por colaborador", lambda key: safe_divide(socios(key), empleados(key)))
    assign_amount("P12 - Resultado neto por colaborador", lambda key: safe_divide(resultado_neto(key), empleados(key)))
    assign_amount("P16 - Gasto por colaborador", lambda key: safe_divide(gastos_total(key), empleados(key)))

    return calculated


def build_brujula_indicator_scenarios(
    periods: list[dict],
    definitions: list[dict],
    store: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    context = build_financial_indicator_context(periods, store)
    get_value = context["get_value"]
    period_keys = context["period_keys"]
    definitions_by_name = {str(item.get("nombre") or "").strip(): item for item in definitions}
    scenarios: list[dict[str, Any]] = []

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
        return sum_numeric(cartera_vigente(period_key), cartera_vencida(period_key))

    def cartera_neta(period_key: str) -> float | None:
        return difference_value(cartera_total(period_key), estimacion_crediticia(period_key))

    def depositos_ahorro(period_key: str) -> float | None:
        return get_value("201-00-00-00-00-000", period_key)

    def depositos_vista(period_key: str) -> float | None:
        return coalesce_numeric(get_value("201-01-00-00-00-000", period_key), depositos_ahorro(period_key))

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
        return coalesce_numeric(get_value("501-00-00-00-00-000", period_key), gastos_total(period_key))

    def gastos_administracion(period_key: str) -> float | None:
        return get_value("505-00-00-00-00-000", period_key)

    def resultado_neto(period_key: str) -> float | None:
        return get_value("__resultado__", period_key)

    def socios(period_key: str) -> float | None:
        return get_value("__metric_socios__", period_key)

    def empleados(period_key: str) -> float | None:
        return get_value("__metric_empleados__", period_key)

    def activos_improductivos(period_key: str) -> float | None:
        return sum_numeric(
            get_value("107-00-00-00-00-000", period_key),
            get_value("108-00-00-00-00-000", period_key),
            get_value("109-00-00-00-00-000", period_key),
            get_value("110-00-00-00-00-000", period_key),
            get_value("113-00-00-00-00-000", period_key),
        )

    def liquidez_inmediata(period_key: str) -> float | None:
        return sum_numeric(disponibilidades(period_key), inversiones(period_key))

    def previous_period_value(series_resolver, period_key: str) -> float | None:
        try:
            index = period_keys.index(period_key)
        except ValueError:
            return None
        if index <= 0:
            return None
        return series_resolver(period_keys[index - 1])

    def scenario_entry(name: str, formula_kind: AnalysisFormulaKind, format_kind: AnalysisFormatKind, inputs_builder, result_builder) -> None:
        meta = str((definitions_by_name.get(name) or {}).get("estandar_meta") or "").strip()
        period_map: dict[str, Any] = {}
        for period_key in period_keys:
            inputs = inputs_builder(period_key)
            raw_result = result_builder(period_key)
            if format_kind == AnalysisFormatKind.PERCENT:
                result = format_indicator_percent(raw_result)
            elif format_kind == AnalysisFormatKind.AMOUNT:
                result = format_indicator_amount(raw_result)
            else:
                result = format_indicator_number(raw_result)
            period_map[period_key] = {"result": result, "raw_result": raw_result, "inputs": inputs}
        scenarios.append(
            {
                "indicador": name,
                "formula_kind": formula_kind,
                "format_kind": format_kind,
                "meta": meta,
                "periods": period_map,
            }
        )

    def ratio_inputs(left_key: str, left_label: str, left_value: float | None, right_key: str, right_label: str, right_value: float | None):
        return [
            {"key": left_key, "label": left_label, "value": left_value, "role": "numerator"},
            {"key": right_key, "label": right_label, "value": right_value, "role": "denominator"},
        ]

    scenario_entry("C2 - Indice de capitalizacion", AnalysisFormulaKind.RATIO, AnalysisFormatKind.PERCENT, lambda key: ratio_inputs("capital_contable", "Capital contable", capital_contable(key), "activo_total", "Activo total", activo_total(key)), lambda key: percent_value(capital_contable(key), activo_total(key)))
    scenario_entry("C3 - Solvencia", AnalysisFormulaKind.RATIO, AnalysisFormatKind.PERCENT, lambda key: ratio_inputs("cartera_neta", "Cartera neta", cartera_neta(key), "activo_total", "Activo total", activo_total(key)), lambda key: percent_value(cartera_neta(key), activo_total(key)))
    scenario_entry("C4 - Credito neto en riesgo", AnalysisFormulaKind.RATIO, AnalysisFormatKind.PERCENT, lambda key: ratio_inputs("cartera_vencida", "Cartera vencida", cartera_vencida(key), "cartera_total", "Cartera total", cartera_total(key)), lambda key: percent_value(cartera_vencida(key), cartera_total(key)))
    scenario_entry("C5 - Cobertura de morosidad", AnalysisFormulaKind.RATIO, AnalysisFormatKind.PERCENT, lambda key: ratio_inputs("estimacion_crediticia", "Estimacion crediticia", estimacion_crediticia(key), "cartera_vencida", "Cartera vencida", cartera_vencida(key)), lambda key: percent_value(estimacion_crediticia(key), cartera_vencida(key)))
    scenario_entry("C6 - Cobertura de obligaciones a la vista", AnalysisFormulaKind.RATIO, AnalysisFormatKind.PERCENT, lambda key: ratio_inputs("liquidez_inmediata", "Liquidez inmediata", liquidez_inmediata(key), "depositos_vista", "Depositos a la vista", depositos_vista(key)), lambda key: percent_value(liquidez_inmediata(key), depositos_vista(key)))
    scenario_entry("C7 - Fondeo de activos improductivos", AnalysisFormulaKind.RATIO, AnalysisFormatKind.PERCENT, lambda key: ratio_inputs("activos_improductivos", "Activos improductivos", activos_improductivos(key), "capital_contable", "Capital contable", capital_contable(key)), lambda key: percent_value(activos_improductivos(key), capital_contable(key)))
    scenario_entry("C8 - Cobertura de gastos con ingresos", AnalysisFormulaKind.RATIO, AnalysisFormatKind.PERCENT, lambda key: ratio_inputs("ingresos", "Ingresos", ingresos(key), "gastos_total", "Gastos total", gastos_total(key)), lambda key: percent_value(ingresos(key), gastos_total(key)))
    scenario_entry("C9 - Autosuficiencia operativa", AnalysisFormulaKind.RATIO, AnalysisFormatKind.PERCENT, lambda key: ratio_inputs("gastos_administracion", "Gastos de administracion", gastos_administracion(key), "ingresos", "Ingresos", ingresos(key)), lambda key: percent_value(gastos_administracion(key), ingresos(key)))
    scenario_entry("C10 - ROA", AnalysisFormulaKind.RATIO, AnalysisFormatKind.PERCENT, lambda key: ratio_inputs("resultado_neto", "Resultado neto", resultado_neto(key), "activo_total", "Activo total", activo_total(key)), lambda key: percent_value(resultado_neto(key), activo_total(key)))
    scenario_entry("C11 - Margen financiero bruto", AnalysisFormulaKind.DIFFERENCE, AnalysisFormatKind.AMOUNT, lambda key: [{"key": "ingresos", "label": "Ingresos", "value": ingresos(key), "role": "minuend"}, {"key": "gastos_financieros", "label": "Gastos financieros", "value": gastos_financieros(key), "role": "subtrahend"}], lambda key: difference_value(ingresos(key), gastos_financieros(key)))

    for name, numerator_label, numerator_resolver, denominator_label, denominator_resolver in (
        ("O1 - Inversiones sobre activo total", "Inversiones", inversiones, "Activo total", activo_total),
        ("O2 - Financiamiento externo sobre activo total", "Prestamos externos", prestamos_externos, "Activo total", activo_total),
        ("O3 - Depositos de ahorro sobre activo total", "Depositos de ahorro", depositos_ahorro, "Activo total", activo_total),
        ("O4 - Capital social sobre activo total", "Capital social", capital_social, "Activo total", activo_total),
        ("O5 - Reservas sobre activo total", "Reservas", reservas, "Activo total", activo_total),
        ("O6 - Reservas sobre capital contable", "Reservas", reservas, "Capital contable", capital_contable),
        ("O9 - Activos improductivos sobre activo total", "Activos improductivos", activos_improductivos, "Activo total", activo_total),
        ("A4 - Costo financiero por depositos", "Gastos financieros", gastos_financieros, "Prestamos externos", prestamos_externos),
        ("A5 - Retorno sobre patrimonio", "Resultado neto", resultado_neto, "Capital contable", capital_contable),
        ("A6 - Cobertura liquida del ahorro", "Liquidez inmediata", liquidez_inmediata, "Depositos de ahorro", depositos_ahorro),
        ("A7 - Cobertura liquida de depositos a la vista", "Liquidez inmediata", liquidez_inmediata, "Depositos a la vista", depositos_vista),
        ("A8 - Cobertura liquida de financiamiento externo", "Liquidez inmediata", liquidez_inmediata, "Prestamos externos", prestamos_externos),
        ("P2 - Ahorro promedio por socio", "Depositos de ahorro", depositos_ahorro, "Socios", socios),
        ("P5 - Socios por colaborador", "Socios", socios, "Empleados", empleados),
        ("P12 - Resultado neto por colaborador", "Resultado neto", resultado_neto, "Empleados", empleados),
        ("P16 - Gasto por colaborador", "Gastos total", gastos_total, "Empleados", empleados),
    ):
        scenario_entry(
            name,
            AnalysisFormulaKind.RATIO,
            AnalysisFormatKind.PERCENT if name.startswith(("O", "A")) else (AnalysisFormatKind.NUMBER if name == "P5 - Socios por colaborador" else AnalysisFormatKind.AMOUNT),
            lambda key, numerator_label=numerator_label, numerator_resolver=numerator_resolver, denominator_label=denominator_label, denominator_resolver=denominator_resolver: ratio_inputs(
                numerator_label.lower().replace(" ", "_"),
                numerator_label,
                numerator_resolver(key),
                denominator_label.lower().replace(" ", "_"),
                denominator_label,
                denominator_resolver(key),
            ),
            lambda key, numerator_resolver=numerator_resolver, denominator_resolver=denominator_resolver, name=name: (percent_value(numerator_resolver(key), denominator_resolver(key)) if name.startswith(("O", "A")) else safe_divide(numerator_resolver(key), denominator_resolver(key))),
        )

    for name, current_label, current_resolver in (
        ("Cr1 - Crecimiento de cartera vigente", "Cartera vigente actual", cartera_vigente),
        ("Cr2 - Crecimiento de inversiones", "Inversiones actuales", inversiones),
        ("Cr3 - Crecimiento de depositos de ahorro", "Depositos de ahorro actuales", depositos_ahorro),
        ("Cr4 - Crecimiento de financiamiento externo", "Prestamos externos actuales", prestamos_externos),
        ("Cr5 - Crecimiento de capital social", "Capital social actual", capital_social),
        ("Cr6 - Crecimiento de reservas", "Reservas actuales", reservas),
        ("Cr7 - Crecimiento de socios", "Socios actuales", socios),
        ("Cr8 - Crecimiento de activos totales", "Activo total actual", activo_total),
    ):
        scenario_entry(
            name,
            AnalysisFormulaKind.GROWTH,
            AnalysisFormatKind.PERCENT,
            lambda key, current_label=current_label, current_resolver=current_resolver: [
                {"key": "current", "label": current_label, "value": current_resolver(key), "role": "current"},
                {"key": "previous", "label": "Periodo anterior", "value": previous_period_value(current_resolver, key), "role": "previous"},
            ],
            lambda key, current_resolver=current_resolver: safe_growth(current_resolver(key), previous_period_value(current_resolver, key)),
        )

    scenario_entry("A1 - Rendimiento sobre cartera promedio", AnalysisFormulaKind.RATIO_AVERAGE, AnalysisFormatKind.PERCENT, lambda key: [{"key": "ingresos", "label": "Ingresos", "value": ingresos(key), "role": "numerator"}, {"key": "cartera_actual", "label": "Cartera total actual", "value": cartera_total(key), "role": "MAIN_current"}, {"key": "cartera_anterior", "label": "Cartera total periodo anterior", "value": previous_period_value(cartera_total, key), "role": "MAIN_previous"}], lambda key: percent_value(ingresos(key), average_numeric(cartera_total(key), previous_period_value(cartera_total, key))))
    scenario_entry("A3 - Costo financiero sobre depositos promedio", AnalysisFormulaKind.RATIO_AVERAGE, AnalysisFormatKind.PERCENT, lambda key: [{"key": "gastos_financieros", "label": "Gastos financieros", "value": gastos_financieros(key), "role": "numerator"}, {"key": "depositos_actuales", "label": "Depositos de ahorro actuales", "value": depositos_ahorro(key), "role": "MAIN_current"}, {"key": "depositos_anteriores", "label": "Depositos de ahorro periodo anterior", "value": previous_period_value(depositos_ahorro, key), "role": "MAIN_previous"}], lambda key: percent_value(gastos_financieros(key), average_numeric(depositos_ahorro(key), previous_period_value(depositos_ahorro, key))))
    scenario_entry("O7 - Capital no comprometido", AnalysisFormulaKind.DIRECT, AnalysisFormatKind.AMOUNT, lambda key: [{"key": "capital_contable", "label": "Capital contable", "value": capital_contable(key), "role": "value"}], capital_contable)

    return scenarios
