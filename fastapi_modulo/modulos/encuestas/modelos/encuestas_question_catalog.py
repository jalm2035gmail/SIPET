from __future__ import annotations

from typing import Any, Dict, List

QUESTION_TYPE_CATALOG: Dict[str, Dict[str, Any]] = {
    "short_text": {
        "label": "Texto corto",
        "requires_options": False,
        "allows_multiple_items": False,
        "input_kind": "text",
        "answer_shape": "string",
        "default_config": {"placeholder": "Respuesta breve", "max_length": 160},
        "default_validation": {"required": False, "max_length": 160},
    },
    "long_text": {
        "label": "Texto largo",
        "requires_options": False,
        "allows_multiple_items": False,
        "input_kind": "textarea",
        "answer_shape": "string",
        "default_config": {"placeholder": "Respuesta abierta", "rows": 4},
        "default_validation": {"required": False, "max_length": 2000},
    },
    "word_cloud": {
        "label": "Mentimeter · Nube de palabras",
        "requires_options": False,
        "allows_multiple_items": False,
        "input_kind": "text",
        "answer_shape": "string",
        "default_config": {"placeholder": "Escribe una palabra o frase corta", "max_length": 80},
        "default_validation": {"required": False, "max_length": 80},
    },
    "single_choice": {
        "label": "Selección única",
        "requires_options": True,
        "allows_multiple_items": False,
        "input_kind": "radio",
        "answer_shape": "string",
        "default_config": {"layout": "vertical"},
        "default_validation": {"required": False, "min_choices": 1, "max_choices": 1},
    },
    "live_poll_single_choice": {
        "label": "Mentimeter · Poll",
        "requires_options": True,
        "allows_multiple_items": False,
        "input_kind": "radio",
        "answer_shape": "string",
        "default_config": {"layout": "vertical", "presentation_mode": "live_poll"},
        "default_validation": {"required": True, "min_choices": 1, "max_choices": 1},
    },
    "multiple_choice": {
        "label": "Selección múltiple",
        "requires_options": True,
        "allows_multiple_items": True,
        "input_kind": "checkbox",
        "answer_shape": "array",
        "default_config": {"layout": "vertical"},
        "default_validation": {"required": False, "min_choices": 1, "max_choices": None},
    },
    "yes_no": {
        "label": "Sí / No",
        "requires_options": True,
        "allows_multiple_items": False,
        "input_kind": "radio",
        "answer_shape": "string",
        "default_options": [
            {"label": "Sí", "value": "yes", "orden": 1},
            {"label": "No", "value": "no", "orden": 2},
        ],
        "default_config": {"layout": "inline"},
        "default_validation": {"required": False, "min_choices": 1, "max_choices": 1},
    },
    "scale_1_5": {
        "label": "Escala 1 a 5",
        "requires_options": True,
        "allows_multiple_items": False,
        "input_kind": "scale",
        "answer_shape": "number",
        "default_options": [
            {"label": "1", "value": "1", "orden": 1, "score_value": 1},
            {"label": "2", "value": "2", "orden": 2, "score_value": 2},
            {"label": "3", "value": "3", "orden": 3, "score_value": 3},
            {"label": "4", "value": "4", "orden": 4, "score_value": 4},
            {"label": "5", "value": "5", "orden": 5, "score_value": 5},
        ],
        "default_config": {"min_label": "Muy bajo", "max_label": "Muy alto"},
        "default_validation": {"required": False, "min_value": 1, "max_value": 5},
    },
    "live_scale_1_5": {
        "label": "Mentimeter · Escala 1 a 5",
        "requires_options": True,
        "allows_multiple_items": False,
        "input_kind": "scale",
        "answer_shape": "number",
        "default_options": [
            {"label": "1", "value": "1", "orden": 1, "score_value": 1},
            {"label": "2", "value": "2", "orden": 2, "score_value": 2},
            {"label": "3", "value": "3", "orden": 3, "score_value": 3},
            {"label": "4", "value": "4", "orden": 4, "score_value": 4},
            {"label": "5", "value": "5", "orden": 5, "score_value": 5},
        ],
        "default_config": {"presentation_mode": "live_scale", "min_label": "Bajo", "max_label": "Alto"},
        "default_validation": {"required": True, "min_value": 1, "max_value": 5},
    },
    "nps_0_10": {
        "label": "NPS 0 a 10",
        "requires_options": True,
        "allows_multiple_items": False,
        "input_kind": "scale",
        "answer_shape": "number",
        "default_options": [
            {"label": str(idx), "value": str(idx), "orden": idx + 1, "score_value": idx}
            for idx in range(11)
        ],
        "default_config": {"min_label": "Nada probable", "max_label": "Muy probable"},
        "default_validation": {"required": False, "min_value": 0, "max_value": 10},
    },
    "quiz_single_choice": {
        "label": "Quiz opción única",
        "requires_options": True,
        "allows_multiple_items": False,
        "input_kind": "radio",
        "answer_shape": "string",
        "default_config": {"layout": "vertical", "shuffle_options": False},
        "default_validation": {"required": True, "min_choices": 1, "max_choices": 1},
    },
    "ranking": {
        "label": "Ordenamiento / Priorización",
        "requires_options": True,
        "allows_multiple_items": True,
        "input_kind": "ranking",
        "answer_shape": "array",
        "default_config": {"layout": "vertical"},
        "default_validation": {"required": False, "min_choices": 1, "max_choices": None},
    },
    "matrix": {
        "label": "Matriz de valoraciones",
        "requires_options": True,
        "allows_multiple_items": True,
        "input_kind": "matrix",
        "answer_shape": "json",
        "default_config": {
            "columns": [
                {"label": "Muy bajo", "value": "1", "score_value": 1},
                {"label": "Bajo", "value": "2", "score_value": 2},
                {"label": "Medio", "value": "3", "score_value": 3},
                {"label": "Alto", "value": "4", "score_value": 4},
                {"label": "Muy alto", "value": "5", "score_value": 5},
            ]
        },
        "default_validation": {"required": False},
    },
    "likert_scale": {
        "label": "Escala de Likert",
        "requires_options": True,
        "allows_multiple_items": True,
        "input_kind": "likert",
        "answer_shape": "json",
        "default_config": {
            "columns": [
                {"label": "Totalmente en desacuerdo", "value": "1", "score_value": 1},
                {"label": "En desacuerdo", "value": "2", "score_value": 2},
                {"label": "Neutral", "value": "3", "score_value": 3},
                {"label": "De acuerdo", "value": "4", "score_value": 4},
                {"label": "Totalmente de acuerdo", "value": "5", "score_value": 5},
            ]
        },
        "default_validation": {"required": False},
    },
    "semantic_differential": {
        "label": "Diferencial semántico",
        "requires_options": True,
        "allows_multiple_items": True,
        "input_kind": "semantic",
        "answer_shape": "json",
        "default_config": {
            "left_label": "Negativo",
            "right_label": "Positivo",
            "columns": [
                {"label": "1", "value": "1", "score_value": 1},
                {"label": "2", "value": "2", "score_value": 2},
                {"label": "3", "value": "3", "score_value": 3},
                {"label": "4", "value": "4", "score_value": 4},
                {"label": "5", "value": "5", "score_value": 5},
            ],
        },
        "default_validation": {"required": False},
    },
    "date": {
        "label": "Fecha",
        "requires_options": False,
        "allows_multiple_items": False,
        "input_kind": "date",
        "answer_shape": "string",
        "default_config": {},
        "default_validation": {"required": False},
    },
    "time": {
        "label": "Hora",
        "requires_options": False,
        "allows_multiple_items": False,
        "input_kind": "time",
        "answer_shape": "string",
        "default_config": {},
        "default_validation": {"required": False},
    },
    "dropdown": {
        "label": "Lista desplegable",
        "requires_options": True,
        "allows_multiple_items": False,
        "input_kind": "select",
        "answer_shape": "string",
        "default_config": {},
        "default_validation": {"required": False},
    },
    "file_upload": {
        "label": "Carga de archivos",
        "requires_options": False,
        "allows_multiple_items": False,
        "input_kind": "file",
        "answer_shape": "json",
        "default_config": {"accept": "*/*", "max_size_mb": 5},
        "default_validation": {"required": False, "max_size_mb": 5},
    },
    "slider": {
        "label": "Control deslizante",
        "requires_options": False,
        "allows_multiple_items": False,
        "input_kind": "slider",
        "answer_shape": "number",
        "default_config": {"min": 0, "max": 10, "step": 1, "min_label": "Mínimo", "max_label": "Máximo"},
        "default_validation": {"required": False, "min_value": 0, "max_value": 10},
    },
    "image_choice": {
        "label": "Selección con imágenes",
        "requires_options": True,
        "allows_multiple_items": False,
        "input_kind": "image_choice",
        "answer_shape": "string",
        "default_config": {"layout": "grid"},
        "default_validation": {"required": False, "min_choices": 1, "max_choices": 1},
    },
    "true_false": {
        "label": "Verdadero / Falso",
        "requires_options": True,
        "allows_multiple_items": False,
        "input_kind": "radio",
        "answer_shape": "string",
        "default_options": [
            {"label": "Verdadero", "value": "true", "orden": 1},
            {"label": "Falso", "value": "false", "orden": 2},
        ],
        "default_config": {"layout": "inline"},
        "default_validation": {"required": False, "min_choices": 1, "max_choices": 1},
    },
}


def list_question_types() -> List[Dict[str, Any]]:
    return [{"key": key, **value} for key, value in QUESTION_TYPE_CATALOG.items()]


def get_question_type_definition(question_type: str) -> Dict[str, Any]:
    key = str(question_type or "").strip()
    if key not in QUESTION_TYPE_CATALOG:
        raise ValueError(f"Tipo de pregunta no soportado: {question_type}")
    return QUESTION_TYPE_CATALOG[key]


def normalize_question_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(data or {})
    definition = get_question_type_definition(payload.get("question_type") or "short_text")

    config = dict(definition.get("default_config") or {})
    config.update(payload.get("config_json") or {})
    validation = dict(definition.get("default_validation") or {})
    validation.update(payload.get("validation_json") or {})

    options = payload.get("options")
    if definition.get("requires_options"):
        if not options:
            options = [dict(option) for option in (definition.get("default_options") or [])]
        if not options:
            raise ValueError(f"El tipo {payload['question_type']} requiere opciones.")
    else:
        options = []

    serialized_answer = {
        "shape": definition.get("answer_shape"),
        "multiple": bool(definition.get("allows_multiple_items", False)),
    }
    validation["serialized_answer"] = serialized_answer

    payload["config_json"] = config
    payload["validation_json"] = validation
    payload["options"] = normalize_options(options, payload["question_type"])
    payload["is_scored"] = bool(payload.get("is_scored", False) or payload["question_type"] in {"quiz_single_choice", "scale_1_5", "nps_0_10"})
    if payload["question_type"] == "quiz_single_choice":
        correct_options = [option for option in payload["options"] if option.get("is_correct")]
        if len(correct_options) != 1:
            payload["options"][0]["is_correct"] = True
            for option in payload["options"][1:]:
                option["is_correct"] = False
        payload["max_score"] = payload.get("max_score") if payload.get("max_score") is not None else 1.0
        payload["min_score"] = payload.get("min_score") if payload.get("min_score") is not None else 0.0
    if payload["question_type"] in {"matrix", "likert_scale", "semantic_differential"}:
        columns = []
        for index, column in enumerate(config.get("columns") or [], start=1):
            label = str(column.get("label") or "").strip()
            value = str(column.get("value") or label or index).strip()
            if not label:
                continue
            score_value = column.get("score_value")
            if score_value is None:
                try:
                    score_value = float(value)
                except (TypeError, ValueError):
                    score_value = None
            columns.append(
                {
                    "label": label,
                    "value": value,
                    "orden": int(column.get("orden") or index),
                    "score_value": score_value,
                }
            )
        config["columns"] = columns
    if payload["question_type"] == "slider":
        try:
            min_value = float(config.get("min", 0))
            max_value = float(config.get("max", 10))
        except (TypeError, ValueError):
            min_value, max_value = 0.0, 10.0
        if max_value < min_value:
            min_value, max_value = max_value, min_value
        config["min"] = min_value
        config["max"] = max_value
        try:
            config["step"] = float(config.get("step", 1))
        except (TypeError, ValueError):
            config["step"] = 1.0
        validation["min_value"] = min_value
        validation["max_value"] = max_value
    return payload


def normalize_options(options: List[Dict[str, Any]], question_type: str) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for index, option in enumerate(options, start=1):
        label = str(option.get("label") or "").strip()
        if not label:
            continue
        value = str(option.get("value") or label).strip()
        normalized.append(
            {
                "label": label,
                "value": value,
                "orden": int(option.get("orden") or index),
                "score_value": option.get("score_value"),
                "is_correct": bool(option.get("is_correct", False)),
                "config_json": option.get("config_json") or {},
            }
        )
    if question_type in {"scale_1_5", "nps_0_10"}:
        for option in normalized:
            if option.get("score_value") is None:
                try:
                    option["score_value"] = float(option["value"])
                except (TypeError, ValueError):
                    option["score_value"] = None
    return normalized
