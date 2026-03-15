from __future__ import annotations

import os
from io import BytesIO, StringIO
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd
import redis as redis_lib
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import text
from sqlalchemy.orm import Session, object_session
from openpyxl.utils import get_column_letter

from fastapi_modulo.db import MAIN, SessionLocal, engine
from fastapi_modulo.modulos.encuestas.modelos.encuestas_question_catalog import (
    QUESTION_TYPE_CATALOG,
    get_question_type_definition,
    normalize_question_payload,
)
from fastapi_modulo.modulos.encuestas.modelos.encuestas_models import (
    SurveyAssignment,
    SurveyAttempt,
    SurveyAudienceGroup,
    SurveyAudienceGroupMember,
    SurveyDispatchLog,
    SurveyEvaluation360,
    SurveyInstance,
    SurveyOption,
    SurveyQuestion,
    SurveyResponse,
    SurveyResponseItem,
    SurveyResult,
    SurveySection,
    SurveyTemplate,
)

_SURVEY_TABLES = [
    SurveyTemplate.__table__,
    SurveyInstance.__table__,
    SurveySection.__table__,
    SurveyQuestion.__table__,
    SurveyOption.__table__,
    SurveyAudienceGroup.__table__,
    SurveyAudienceGroupMember.__table__,
    SurveyAssignment.__table__,
    SurveyResponse.__table__,
    SurveyResponseItem.__table__,
    SurveyResult.__table__,
    SurveyAttempt.__table__,
    SurveyEvaluation360.__table__,
    SurveyDispatchLog.__table__,
]

_SURVEY_SCHEMA_READY = False
_NOTIFICATION_SCHEMA_READY = False

DEFAULT_SURVEY_TEMPLATES: List[Dict[str, Any]] = [
    {
        "nombre": "Encuesta general",
        "slug": "encuesta-general",
        "descripcion": "Plantilla MAIN para levantar percepciones generales.",
        "categoria": "general",
        "survey_type": "general",
        "scoring_mode": "none",
        "settings_json": {},
        "sections": [
            {
                "titulo": "Datos generales",
                "descripcion": "Preguntas abiertas y valoración general.",
                "questions": [
                    {"titulo": "¿Cómo calificarías tu experiencia general?", "question_type": "scale_1_5", "is_required": True},
                    {"titulo": "¿Qué fue lo mejor de la experiencia?", "question_type": "long_text"},
                    {"titulo": "¿Qué deberíamos mejorar?", "question_type": "long_text"},
                ],
            }
        ],
    },
    {
        "nombre": "Satisfacción del cliente",
        "slug": "satisfaccion-del-cliente",
        "descripcion": "Mide satisfacción de servicio y atención recibida.",
        "categoria": "clientes",
        "survey_type": "customer_satisfaction",
        "scoring_mode": "csat",
        "settings_json": {"scoring_mode": "csat"},
        "sections": [
            {
                "titulo": "Atención",
                "questions": [
                    {"titulo": "La atención fue rápida", "question_type": "scale_1_5", "is_required": True},
                    {"titulo": "El trato recibido fue amable", "question_type": "scale_1_5", "is_required": True},
                    {"titulo": "¿Volverías a utilizar el servicio?", "question_type": "yes_no", "is_required": True},
                ],
            }
        ],
    },
    {
        "nombre": "NPS",
        "slug": "nps",
        "descripcion": "Plantilla corta para medir recomendación.",
        "categoria": "clientes",
        "survey_type": "nps",
        "scoring_mode": "nps",
        "settings_json": {"scoring_mode": "nps"},
        "sections": [
            {
                "titulo": "Lealtad",
                "questions": [
                    {"titulo": "¿Qué tan probable es que recomiendes la organización?", "question_type": "nps_0_10", "is_required": True},
                    {"titulo": "¿Cuál es el principal motivo de tu calificación?", "question_type": "long_text"},
                ],
            }
        ],
    },
    {
        "nombre": "Clima laboral corto",
        "slug": "clima-laboral-corto",
        "descripcion": "Pulso rápido de clima laboral interno.",
        "categoria": "talento",
        "survey_type": "employee_climate",
        "scoring_mode": "csat",
        "settings_json": {"scoring_mode": "csat"},
        "sections": [
            {
                "titulo": "Ambiente",
                "questions": [
                    {"titulo": "Me siento motivado en mi trabajo", "question_type": "scale_1_5", "is_required": True},
                    {"titulo": "Tengo claridad sobre mis responsabilidades", "question_type": "scale_1_5", "is_required": True},
                    {"titulo": "Recomendaría esta organización para trabajar", "question_type": "nps_0_10", "is_required": True},
                ],
            }
        ],
    },
    {
        "nombre": "Evaluación 360 básica",
        "slug": "evaluacion-360-basica",
        "descripcion": "Plantilla MAIN para evaluación 360 con anonimato restringido.",
        "categoria": "talento",
        "survey_type": "evaluation_360",
        "scoring_mode": "csat",
        "settings_json": {"scoring_mode": "csat"},
        "anonymity_mode": "restricted",
        "external_entity_type": "evaluation_360",
        "sections": [
            {
                "titulo": "Competencias",
                "questions": [
                    {"titulo": "Demuestra liderazgo en su área", "question_type": "scale_1_5", "is_required": True},
                    {"titulo": "Colabora con el equipo", "question_type": "scale_1_5", "is_required": True},
                    {"titulo": "Comentario cualitativo", "question_type": "long_text"},
                ],
            }
        ],
    },
    {
        "nombre": "Quiz de capacitación",
        "slug": "quiz-de-capacitacion",
        "descripcion": "Evaluación corta de conocimiento posterior a capacitación.",
        "categoria": "capacitacion",
        "survey_type": "quiz",
        "scoring_mode": "quiz",
        "settings_json": {"scoring_mode": "quiz"},
        "sections": [
            {
                "titulo": "Conocimiento",
                "questions": [
                    {
                        "titulo": "¿Cuál es el objetivo principal del curso?",
                        "question_type": "quiz_single_choice",
                        "is_required": True,
                        "options": [
                            {"label": "Actualizar conocimientos", "value": "actualizar", "is_correct": True},
                            {"label": "Realizar una auditoría", "value": "auditoria"},
                            {"label": "Solicitar vacaciones", "value": "vacaciones"},
                        ],
                    },
                    {
                        "titulo": "Selecciona los temas vistos",
                        "question_type": "multiple_choice",
                        "options": [
                            {"label": "Proceso", "value": "proceso", "score_value": 1},
                            {"label": "Políticas", "value": "politicas", "score_value": 1},
                            {"label": "Cafetería", "value": "cafeteria", "score_value": 0},
                        ],
                    },
                ],
            }
        ],
    },
    {
        "nombre": "Mentimeter para capacitación",
        "slug": "mentimeter-capacitacion",
        "descripcion": "Dinámica en vivo para sesiones de capacitación con poll, nube de palabras y escala rápida.",
        "categoria": "capacitacion",
        "survey_type": "live_poll",
        "scoring_mode": "none",
        "settings_json": {"presentation_mode": "mentimeter", "live_session_enabled": True},
        "sections": [
            {
                "titulo": "Participación en vivo",
                "descripcion": "Usa una pregunta por dinámica o duplica la plantilla.",
                "questions": [
                    {
                        "titulo": "¿Qué concepto te resultó más claro?",
                        "question_type": "word_cloud",
                        "is_required": True,
                    },
                    {
                        "titulo": "¿Qué tan claro fue el tema de hoy?",
                        "question_type": "live_scale_1_5",
                        "is_required": True,
                    },
                    {
                        "titulo": "¿Qué actividad quieres reforzar?",
                        "question_type": "live_poll_single_choice",
                        "is_required": True,
                        "options": [
                            {"label": "Ejemplo guiado", "value": "ejemplo_guiado", "orden": 1},
                            {"label": "Práctica", "value": "practica", "orden": 2},
                            {"label": "Preguntas y respuestas", "value": "preguntas_respuestas", "orden": 3},
                        ],
                    },
                ],
            }
        ],
    },
    {
        "nombre": "Encuesta post evento",
        "slug": "encuesta-post-evento",
        "descripcion": "Recoge satisfacción, logística e impacto de un evento.",
        "categoria": "eventos",
        "survey_type": "post_event",
        "scoring_mode": "csat",
        "settings_json": {"scoring_mode": "csat"},
        "sections": [
            {
                "titulo": "Experiencia",
                "questions": [
                    {"titulo": "El evento cumplió tus expectativas", "question_type": "scale_1_5", "is_required": True},
                    {"titulo": "La logística fue adecuada", "question_type": "scale_1_5", "is_required": True},
                    {"titulo": "Comentario final", "question_type": "long_text"},
                ],
            }
        ],
    },
]


def ensure_survey_schema() -> None:
    global _SURVEY_SCHEMA_READY
    if _SURVEY_SCHEMA_READY:
        return
    MAIN.metadata.create_all(bind=engine, tables=_SURVEY_TABLES, checkfirst=True)
    _SURVEY_SCHEMA_READY = True


def get_db() -> Session:
    return SessionLocal()


ensure_survey_schema()


def _dt(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _is_360_payload(survey_type: str = "", external_entity_type: str = "") -> bool:
    survey_value = str(survey_type or "").strip().lower()
    entity_value = str(external_entity_type or "").strip().lower()
    return survey_value in {"360", "evaluation_360", "evaluacion_360"} or "360" in entity_value


def _notification_timestamp() -> str:
    return datetime.utcnow().isoformat()


def _background_runtime_status() -> Dict[str, Any]:
    broker_url = (
        os.environ.get("ENCUESTAS_CELERY_BROKER_URL")
        or os.environ.get("CELERY_BROKER_URL")
        or os.environ.get("REDIS_URL")
        or ""
    ).strip()
    result_backend = (
        os.environ.get("ENCUESTAS_CELERY_RESULT_BACKEND")
        or os.environ.get("CELERY_RESULT_BACKEND")
        or broker_url
    ).strip()
    queue_name = (os.environ.get("ENCUESTAS_CELERY_QUEUE") or "encuestas_automation").strip() or "encuestas_automation"
    configured = bool(broker_url)
    redis_ready = False
    redis_error = ""
    if configured and broker_url.startswith(("redis://", "rediss://")):
        try:
            redis_lib.from_url(broker_url, socket_connect_timeout=0.5, socket_timeout=0.5).ping()
            redis_ready = True
        except Exception as exc:
            redis_error = str(exc)
    return {
        "configured": configured,
        "broker_url": broker_url,
        "result_backend": result_backend,
        "queue_name": queue_name,
        "engine": "celery" if configured else "manual_scheduler",
        "celery_ready": configured,
        "redis_ready": redis_ready,
        "redis_error": redis_error,
    }


def _load_capacitacion_enrollments(curso_id: int) -> List[Dict[str, Any]]:
    try:
        from fastapi_modulo.modulos.capacitacion.modelos.cap_inscripcion_service import list_inscripciones

        return list_inscripciones(curso_id=curso_id)
    except Exception:
        return []


def _load_crm_campaign_contacts(campaign_id: int) -> List[Dict[str, Any]]:
    try:
        from fastapi_modulo.modulos.crm.modelos.crm_store import list_contactos, list_contactos_campania

        links = list_contactos_campania(campaign_id)
        contact_ids = {int(item["contacto_id"]) for item in links if item.get("contacto_id")}
        contacts = {int(item["id"]): item for item in list_contactos()}
        return [contacts[contact_id] for contact_id in sorted(contact_ids) if contact_id in contacts]
    except Exception:
        return []


def _resolve_integration_context(source_app: str = "", external_entity_type: str = "", external_entity_id: str = "") -> Dict[str, Any]:
    source_value = str(source_app or "").strip().lower()
    entity_type = str(external_entity_type or "").strip().lower()
    entity_id = str(external_entity_id or "").strip()
    if not source_value or not entity_type or not entity_id:
        return {}
    if source_value == "capacitacion" and entity_type in {"curso", "course"} and entity_id.isdigit():
        courses = {str(item["id"]): item for item in _load_capacitacion_courses()}
        course = courses.get(entity_id)
        return {"course": course} if course else {}
    if source_value == "crm":
        if entity_type in {"contacto", "contact", "crm_contact"} and entity_id.isdigit():
            contacts = {str(item["id"]): item for item in _load_crm_contacts()}
            contact = contacts.get(entity_id)
            return {"contact": contact} if contact else {}
        if entity_type in {"campania", "campaign", "crm_campaign"} and entity_id.isdigit():
            contacts = _load_crm_campaign_contacts(int(entity_id))
            return {
                "campaign_contacts": contacts,
                "campaign_contacts_count": len(contacts),
            }
    return {}


def _automation_settings(instance: SurveyInstance) -> Dict[str, Any]:
    settings = instance.settings_json or {}
    rules = instance.publication_rules_json or {}
    background = _background_runtime_status()
    return {
        "enabled": bool(rules.get("automation_enabled", True)),
        "reminder_interval_hours": int(rules.get("reminder_interval_hours") or settings.get("reminder_interval_hours") or 24),
        "closing_notice_hours": int(rules.get("closing_notice_hours") or settings.get("closing_notice_hours") or 24),
        "engine": background["engine"],
        "future": {
            "celery_ready": background["celery_ready"],
            "redis_ready": background["redis_ready"],
            "redis_error": background["redis_error"],
            "broker_configured": background["configured"],
            "queue_name": background["queue_name"],
        },
    }


def _assignment_dict(obj: SurveyAssignment) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "instance_id": obj.instance_id,
        "audience_group_id": obj.audience_group_id,
        "assignee_key": obj.assignee_key,
        "assignee_name_snapshot": obj.assignee_name_snapshot,
        "assignee_role_snapshot": obj.assignee_role_snapshot,
        "assignee_area_snapshot": obj.assignee_area_snapshot,
        "assignee_position_snapshot": obj.assignee_position_snapshot,
        "assignee_company_snapshot": obj.assignee_company_snapshot,
        "source_app": obj.source_app,
        "external_entity_type": obj.external_entity_type,
        "external_entity_id": obj.external_entity_id,
        "assignment_type": obj.assignment_type,
        "channel": obj.channel,
        "status": obj.status,
        "due_at": _dt(obj.due_at),
        "first_sent_at": _dt(obj.first_sent_at),
        "last_sent_at": _dt(obj.last_sent_at),
        "response_count": obj.response_count,
        "created_at": _dt(obj.created_at),
        "updated_at": _dt(obj.updated_at),
    }


def _dispatch_log_dict(obj: SurveyDispatchLog) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "instance_id": obj.instance_id,
        "assignment_id": obj.assignment_id,
        "dispatch_type": obj.dispatch_type,
        "dispatch_status": obj.dispatch_status,
        "channel": obj.channel,
        "recipient_key": obj.recipient_key,
        "recipient_name_snapshot": obj.recipient_name_snapshot,
        "message_text": obj.message_text,
        "metadata_json": obj.metadata_json or {},
        "dispatched_at": _dt(obj.dispatched_at),
        "created_at": _dt(obj.created_at),
    }


def _evaluation_360_dict(obj: SurveyEvaluation360) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "instance_id": obj.instance_id,
        "assignment_id": obj.assignment_id,
        "evaluatee_key": obj.evaluatee_key,
        "evaluator_key": obj.evaluator_key,
        "relationship_type": obj.relationship_type,
        "evaluatee_name_snapshot": obj.evaluatee_name_snapshot,
        "evaluatee_role_snapshot": obj.evaluatee_role_snapshot,
        "evaluatee_area_snapshot": obj.evaluatee_area_snapshot,
        "evaluatee_position_snapshot": obj.evaluatee_position_snapshot,
        "evaluatee_company_snapshot": obj.evaluatee_company_snapshot,
        "evaluator_name_snapshot": obj.evaluator_name_snapshot,
        "evaluator_role_snapshot": obj.evaluator_role_snapshot,
        "evaluator_area_snapshot": obj.evaluator_area_snapshot,
        "evaluator_position_snapshot": obj.evaluator_position_snapshot,
        "evaluator_company_snapshot": obj.evaluator_company_snapshot,
        "status": obj.status,
        "source_app": obj.source_app,
        "external_entity_type": obj.external_entity_type,
        "external_entity_id": obj.external_entity_id,
        "created_at": _dt(obj.created_at),
        "updated_at": _dt(obj.updated_at),
    }


def _response_item_dict(obj: SurveyResponseItem) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "question_id": obj.question_id,
        "option_id": obj.option_id,
        "item_index": obj.item_index,
        "answer_text": obj.answer_text,
        "answer_value": obj.answer_value,
        "answer_json": obj.answer_json or {},
        "score_value": obj.score_value,
        "is_correct": obj.is_correct,
    }


def _response_dict(obj: SurveyResponse) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "tenant_id": obj.tenant_id,
        "instance_id": obj.instance_id,
        "assignment_id": obj.assignment_id,
        "respondent_key": obj.respondent_key,
        "respondent_name_snapshot": obj.respondent_name_snapshot,
        "respondent_role_snapshot": obj.respondent_role_snapshot,
        "respondent_area_snapshot": obj.respondent_area_snapshot,
        "respondent_position_snapshot": obj.respondent_position_snapshot,
        "respondent_company_snapshot": obj.respondent_company_snapshot,
        "source_app": obj.source_app,
        "external_entity_type": obj.external_entity_type,
        "external_entity_id": obj.external_entity_id,
        "status": obj.status,
        "submission_channel": obj.submission_channel,
        "evaluation_360_id": int(obj.external_entity_id) if str(obj.external_entity_type or "") == "evaluation_360" and str(obj.external_entity_id or "").isdigit() else None,
        "started_at": _dt(obj.started_at),
        "submitted_at": _dt(obj.submitted_at),
        "last_saved_at": _dt(obj.last_saved_at),
        "completion_pct": obj.completion_pct,
        "total_score": obj.total_score,
        "metrics_json": obj.metrics_json or {},
        "answers_json": obj.answers_json or {},
        "created_at": _dt(obj.created_at),
        "updated_at": _dt(obj.updated_at),
        "items": [_response_item_dict(item) for item in (obj.items or [])],
    }


def _template_dict(obj: SurveyTemplate) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "tenant_id": obj.tenant_id,
        "nombre": obj.nombre,
        "slug": obj.slug,
        "descripcion": obj.descripcion,
        "categoria": obj.categoria,
        "survey_type": obj.survey_type,
        "status": obj.status,
        "version": obj.version,
        "source_app": obj.source_app,
        "external_entity_type": obj.external_entity_type,
        "external_entity_id": obj.external_entity_id,
        "scoring_mode": obj.scoring_mode,
        "settings_json": obj.settings_json or {},
        "validation_rules_json": obj.validation_rules_json or {},
        "created_by": obj.created_by,
        "created_at": _dt(obj.created_at),
        "updated_at": _dt(obj.updated_at),
        "published_at": _dt(obj.published_at),
        "sections_count": len(obj.sections or []),
    }


def _instance_dict(obj: SurveyInstance) -> Dict[str, Any]:
    integration_context = _resolve_integration_context(
        source_app=obj.source_app,
        external_entity_type=obj.external_entity_type,
        external_entity_id=obj.external_entity_id,
    )
    automation_settings = _automation_settings(obj)
    return {
        "id": obj.id,
        "tenant_id": obj.tenant_id,
        "template_id": obj.template_id,
        "template_nombre": obj.template.nombre if obj.template else None,
        "codigo": obj.codigo,
        "nombre": obj.nombre,
        "descripcion": obj.descripcion,
        "status": obj.status,
        "publication_mode": obj.publication_mode,
        "audience_mode": obj.audience_mode,
        "anonymity_mode": obj.anonymity_mode,
        "schedule_start_at": _dt(obj.schedule_start_at),
        "schedule_end_at": _dt(obj.schedule_end_at),
        "is_public_link_enabled": obj.is_public_link_enabled,
        "public_link_token": obj.public_link_token,
        "source_app": obj.source_app,
        "external_entity_type": obj.external_entity_type,
        "external_entity_id": obj.external_entity_id,
        "integration_context": integration_context,
        "automation_settings": automation_settings,
        "settings_json": obj.settings_json or {},
        "publication_rules_json": obj.publication_rules_json or {},
        "created_by": obj.created_by,
        "created_at": _dt(obj.created_at),
        "updated_at": _dt(obj.updated_at),
        "published_at": _dt(obj.published_at),
        "closed_at": _dt(obj.closed_at),
        "assignments_count": len(obj.assignments or []),
        "responses_count": len(obj.responses or []),
    }


def _option_dict(obj: SurveyOption) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "label": obj.label,
        "value": obj.value,
        "orden": obj.orden,
        "score_value": obj.score_value,
        "is_correct": obj.is_correct,
        "config_json": obj.config_json or {},
    }


def _question_dict(obj: SurveyQuestion) -> Dict[str, Any]:
    definition = get_question_type_definition(obj.question_type)
    return {
        "id": obj.id,
        "template_id": obj.template_id,
        "section_id": obj.section_id,
        "question_key": obj.question_key,
        "titulo": obj.titulo,
        "descripcion": obj.descripcion,
        "question_type": obj.question_type,
        "question_type_label": definition.get("label"),
        "input_kind": definition.get("input_kind"),
        "orden": obj.orden,
        "is_required": obj.is_required,
        "is_scored": obj.is_scored,
        "max_score": obj.max_score,
        "min_score": obj.min_score,
        "config_json": obj.config_json or {},
        "validation_json": obj.validation_json or {},
        "logic_json": obj.logic_json or {},
        "options": [_option_dict(option) for option in (obj.options or [])],
    }


def _section_dict(obj: SurveySection) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "template_id": obj.template_id,
        "instance_id": obj.instance_id,
        "titulo": obj.titulo,
        "descripcion": obj.descripcion,
        "orden": obj.orden,
        "is_required": obj.is_required,
        "settings_json": obj.settings_json or {},
        "questions": [_question_dict(question) for question in (obj.questions or [])],
    }


def list_templates(tenant_id: str, status: str = "") -> List[Dict[str, Any]]:
    db = get_db()
    try:
        query = (
            db.query(SurveyTemplate)
            .filter(SurveyTemplate.tenant_id == tenant_id)
            .order_by(SurveyTemplate.updated_at.desc(), SurveyTemplate.id.desc())
        )
        if status:
            query = query.filter(SurveyTemplate.status == status)
        return [_template_dict(row) for row in query.all()]
    finally:
        db.close()


def create_template(data: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    try:
        obj = SurveyTemplate(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _template_dict(obj)
    except IntegrityError:
        db.rollback()
        raise
    finally:
        db.close()


def _create_template_with_structure(db: Session, data: Dict[str, Any]) -> SurveyTemplate:
    payload = dict(data or {})
    sections = payload.pop("sections", [])
    template = SurveyTemplate(**payload)
    db.add(template)
    db.flush()
    for section_index, section_data in enumerate(sections, start=1):
        section = SurveySection(
            tenant_id=template.tenant_id,
            template_id=template.id,
            instance_id=None,
            titulo=str(section_data.get("titulo") or f"Sección {section_index}"),
            descripcion=section_data.get("descripcion"),
            orden=section_index,
            is_required=bool(section_data.get("is_required", False)),
            settings_json=section_data.get("settings_json") or {},
        )
        db.add(section)
        db.flush()
        for question_index, question_data in enumerate(section_data.get("questions") or [], start=1):
            normalized = normalize_question_payload(question_data)
            question = SurveyQuestion(
                tenant_id=template.tenant_id,
                template_id=template.id,
                section_id=section.id,
                question_key=normalized.get("question_key"),
                titulo=str(normalized.get("titulo") or f"Pregunta {question_index}"),
                descripcion=normalized.get("descripcion"),
                question_type=str(normalized.get("question_type") or "short_text"),
                orden=question_index,
                is_required=bool(normalized.get("is_required", False)),
                is_scored=bool(normalized.get("is_scored", False)),
                max_score=normalized.get("max_score"),
                min_score=normalized.get("min_score"),
                config_json=normalized.get("config_json") or {},
                validation_json=normalized.get("validation_json") or {},
                logic_json=normalized.get("logic_json") or {},
            )
            db.add(question)
            db.flush()
            _upsert_question_options(db, question, template.tenant_id, normalized.get("options") or [])
    return template


def ensure_default_templates(tenant_id: str, created_by: Optional[str] = None) -> List[Dict[str, Any]]:
    db = get_db()
    try:
        existing = {
            row.slug: row
            for row in db.query(SurveyTemplate).filter(SurveyTemplate.tenant_id == tenant_id).all()
        }
        for item in DEFAULT_SURVEY_TEMPLATES:
            slug = str(item["slug"])
            if slug in existing:
                continue
            template = _create_template_with_structure(
                db,
                {
                    "tenant_id": tenant_id,
                    "nombre": item["nombre"],
                    "slug": slug,
                    "descripcion": item.get("descripcion"),
                    "categoria": item.get("categoria"),
                    "survey_type": item.get("survey_type") or "general",
                    "status": "published",
                    "version": 1,
                    "source_app": "encuestas",
                    "external_entity_type": item.get("external_entity_type"),
                    "external_entity_id": slug,
                    "scoring_mode": item.get("scoring_mode") or "none",
                    "settings_json": item.get("settings_json") or {},
                    "validation_rules_json": {},
                    "created_by": created_by,
                    "published_at": datetime.utcnow(),
                    "sections": item.get("sections") or [],
                },
            )
            template.status = "published"
            template.published_at = datetime.utcnow()
        db.commit()
        rows = (
            db.query(SurveyTemplate)
            .filter(SurveyTemplate.tenant_id == tenant_id)
            .order_by(SurveyTemplate.updated_at.desc(), SurveyTemplate.id.desc())
            .all()
        )
        return [_template_dict(row) for row in rows]
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_instances(tenant_id: str, status: str = "") -> List[Dict[str, Any]]:
    db = get_db()
    try:
        _refresh_instance_lifecycle(db, tenant_id=tenant_id)
        query = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.tenant_id == tenant_id)
            .order_by(SurveyInstance.updated_at.desc(), SurveyInstance.id.desc())
        )
        if status:
            query = query.filter(SurveyInstance.status == status)
        return [_instance_dict(row) for row in query.all()]
    finally:
        db.close()


def create_instance(data: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    try:
        template_id = data.get("template_id")
        if not template_id:
            template = SurveyTemplate(
                tenant_id=str(data.get("tenant_id") or "default"),
                nombre=str(data.get("nombre") or "Nueva encuesta"),
                slug=str(data.get("codigo") or data.get("nombre") or "encuesta").lower(),
                descripcion=data.get("descripcion"),
                categoria=data.get("categoria"),
                survey_type=str(data.get("survey_type") or "general"),
                status="draft",
                source_app=data.get("source_app"),
                external_entity_type=data.get("external_entity_type"),
                external_entity_id=data.get("external_entity_id"),
                scoring_mode=str((data.get("settings_json") or {}).get("scoring_mode") or "none"),
                settings_json=data.get("settings_json") or {},
                validation_rules_json={},
                created_by=data.get("created_by"),
            )
            db.add(template)
            db.flush()
            template_id = template.id
        obj = SurveyInstance(**{**data, "template_id": template_id})
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _instance_dict(obj)
    except IntegrityError:
        db.rollback()
        raise
    finally:
        db.close()


def create_instance_from_template(
    tenant_id: str,
    template_id: int,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    db = get_db()
    try:
        template = (
            db.query(SurveyTemplate)
            .filter(SurveyTemplate.id == template_id, SurveyTemplate.tenant_id == tenant_id)
            .first()
        )
        if not template:
            raise ValueError("Plantilla no encontrada.")
        payload = dict(data or {})
        payload["tenant_id"] = tenant_id
        payload["template_id"] = template.id
        payload.setdefault("nombre", template.nombre)
        payload.setdefault("descripcion", template.descripcion)
        payload.setdefault("source_app", template.source_app)
        payload.setdefault("external_entity_type", template.external_entity_type)
        payload.setdefault("external_entity_id", template.external_entity_id)
        payload.setdefault("settings_json", template.settings_json or {})
        payload.setdefault("publication_rules_json", {})
        payload.setdefault(
            "anonymity_mode",
            "restricted" if str(template.survey_type or "").strip().lower() in {"360", "evaluation_360", "evaluacion_360"} else "identified",
        )
        instance = SurveyInstance(**payload)
        db.add(instance)
        db.flush()
        for section in template.sections or []:
            new_section = SurveySection(
                tenant_id=tenant_id,
                template_id=template.id,
                instance_id=instance.id,
                titulo=section.titulo,
                descripcion=section.descripcion,
                orden=section.orden,
                is_required=section.is_required,
                settings_json=section.settings_json or {},
            )
            db.add(new_section)
            db.flush()
            for question in section.questions or []:
                cloned = SurveyQuestion(
                    tenant_id=tenant_id,
                    template_id=template.id,
                    section_id=new_section.id,
                    question_key=question.question_key,
                    titulo=question.titulo,
                    descripcion=question.descripcion,
                    question_type=question.question_type,
                    orden=question.orden,
                    is_required=question.is_required,
                    is_scored=question.is_scored,
                    max_score=question.max_score,
                    min_score=question.min_score,
                    config_json=question.config_json or {},
                    validation_json=question.validation_json or {},
                    logic_json=question.logic_json or {},
                )
                db.add(cloned)
                db.flush()
                _upsert_question_options(
                    db,
                    cloned,
                    tenant_id,
                    [
                        {
                            "label": option.label,
                            "value": option.value,
                            "orden": option.orden,
                            "score_value": option.score_value,
                            "is_correct": option.is_correct,
                            "config_json": option.config_json or {},
                        }
                        for option in (question.options or [])
                    ],
                )
        db.commit()
        db.refresh(instance)
        return _instance_dict(instance)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def save_instance_as_template(instance_id: int, tenant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    try:
        instance = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not instance:
            raise ValueError("Encuesta no encontrada.")
        slug = str(data.get("slug") or "").strip()
        if not slug:
            raise ValueError("La plantilla requiere slug.")
        existing = (
            db.query(SurveyTemplate)
            .filter(SurveyTemplate.tenant_id == tenant_id, SurveyTemplate.slug == slug)
            .first()
        )
        if existing:
            raise ValueError("Ya existe una plantilla con ese slug.")
        template = SurveyTemplate(
            tenant_id=tenant_id,
            nombre=str(data.get("nombre") or instance.nombre),
            slug=slug,
            descripcion=data.get("descripcion") or instance.descripcion,
            categoria=data.get("categoria"),
            survey_type=str(data.get("survey_type") or (instance.template.survey_type if instance.template else "general")),
            status="published",
            version=1,
            source_app=instance.source_app or "encuestas",
            external_entity_type=data.get("external_entity_type"),
            external_entity_id=data.get("external_entity_id") or f"saved_template:{instance.id}",
            scoring_mode=str((instance.settings_json or {}).get("scoring_mode") or "none"),
            settings_json=instance.settings_json or {},
            validation_rules_json=instance.publication_rules_json or {},
            created_by=data.get("created_by"),
            published_at=datetime.utcnow(),
        )
        db.add(template)
        db.flush()
        for section in instance.sections or []:
            new_section = SurveySection(
                tenant_id=tenant_id,
                template_id=template.id,
                instance_id=None,
                titulo=section.titulo,
                descripcion=section.descripcion,
                orden=section.orden,
                is_required=section.is_required,
                settings_json=section.settings_json or {},
            )
            db.add(new_section)
            db.flush()
            for question in section.questions or []:
                cloned = SurveyQuestion(
                    tenant_id=tenant_id,
                    template_id=template.id,
                    section_id=new_section.id,
                    question_key=question.question_key,
                    titulo=question.titulo,
                    descripcion=question.descripcion,
                    question_type=question.question_type,
                    orden=question.orden,
                    is_required=question.is_required,
                    is_scored=question.is_scored,
                    max_score=question.max_score,
                    min_score=question.min_score,
                    config_json=question.config_json or {},
                    validation_json=question.validation_json or {},
                    logic_json=question.logic_json or {},
                )
                db.add(cloned)
                db.flush()
                _upsert_question_options(
                    db,
                    cloned,
                    tenant_id,
                    [
                        {
                            "label": option.label,
                            "value": option.value,
                            "orden": option.orden,
                            "score_value": option.score_value,
                            "is_correct": option.is_correct,
                            "config_json": option.config_json or {},
                        }
                        for option in (question.options or [])
                    ],
                )
        db.commit()
        db.refresh(template)
        return _template_dict(template)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def get_instance(instance_id: int, tenant_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        _refresh_instance_lifecycle(db, instance_id=instance_id, tenant_id=tenant_id)
        obj = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        return _instance_dict(obj) if obj else None
    finally:
        db.close()


def get_instance_builder(instance_id: int, tenant_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        _refresh_instance_lifecycle(db, instance_id=instance_id, tenant_id=tenant_id)
        obj = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not obj:
            return None
        payload = _instance_dict(obj)
        payload["sections"] = [_section_dict(section) for section in (obj.sections or [])]
        payload["publish_validation"] = validate_instance_for_publish_db(obj)
        payload["assignments"] = [_assignment_dict(assignment) for assignment in (obj.assignments or [])]
        return payload
    finally:
        db.close()


def update_instance_draft(instance_id: int, tenant_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        obj = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not obj:
            return None
        if obj.status not in {"draft", "archived"}:
            raise ValueError("Solo se puede editar una encuesta en borrador o archivada.")
        if not obj.template_id:
            template = SurveyTemplate(
                tenant_id=tenant_id,
                nombre=str(data.get("nombre") or obj.nombre or "Nueva encuesta"),
                slug=str(obj.codigo or obj.nombre or f"encuesta_{obj.id}").lower(),
                descripcion=data.get("descripcion") if "descripcion" in data else obj.descripcion,
                survey_type="general",
                status="draft",
                source_app=data.get("source_app") if "source_app" in data else obj.source_app,
                external_entity_type=data.get("external_entity_type") if "external_entity_type" in data else obj.external_entity_type,
                external_entity_id=data.get("external_entity_id") if "external_entity_id" in data else obj.external_entity_id,
                scoring_mode=str((data.get("settings_json") or obj.settings_json or {}).get("scoring_mode") or "none"),
                settings_json=data.get("settings_json") if "settings_json" in data else (obj.settings_json or {}),
                validation_rules_json={},
                created_by=obj.created_by,
            )
            db.add(template)
            db.flush()
            obj.template_id = template.id
        for key, value in data.items():
            if value is not None:
                setattr(obj, key, value)
        if obj.template:
            template = obj.template
            template.nombre = obj.nombre
            template.descripcion = obj.descripcion
            template.source_app = obj.source_app
            template.external_entity_type = obj.external_entity_type
            template.external_entity_id = obj.external_entity_id
            template.scoring_mode = str((obj.settings_json or {}).get("scoring_mode") or template.scoring_mode or "none")
            template.settings_json = obj.settings_json or {}
            template.updated_at = datetime.utcnow()
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return _instance_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def publish_instance(instance_id: int, tenant_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        obj = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not obj:
            return None
        if obj.status == "closed":
            raise ValueError("No se puede publicar una encuesta cerrada.")
        now = datetime.utcnow()
        if obj.schedule_start_at and obj.schedule_start_at > now:
            obj.status = "scheduled"
        else:
            obj.status = "published"
            obj.published_at = now
        if obj.template:
            obj.template.status = obj.status
            obj.template.published_at = obj.published_at
            obj.template.updated_at = now
        if obj.status in {"published", "scheduled"} and obj.assignments:
            has_sent_notifications = any(assignment.first_sent_at for assignment in (obj.assignments or []))
            _send_assignment_notifications(
                db,
                obj,
                list(obj.assignments or []),
                notification_kind="reminder" if has_sent_notifications else "invitation",
            )
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return _instance_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def close_instance(instance_id: int, tenant_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        obj = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not obj:
            return None
        obj.status = "closed"
        obj.closed_at = datetime.utcnow()
        if obj.template:
            obj.template.status = "closed"
            obj.template.updated_at = datetime.utcnow()
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return _instance_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def archive_or_delete_instance(instance_id: int, tenant_id: str, hard_delete: bool = False) -> bool:
    db = get_db()
    try:
        obj = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not obj:
            return False
        if hard_delete:
            if obj.template and len(obj.template.instances or []) <= 1:
                db.delete(obj.template)
            db.delete(obj)
        else:
            obj.status = "archived"
            if obj.template:
                obj.template.status = "archived"
                obj.template.updated_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def _next_section_order(db: Session, template_id: int) -> int:
    section = (
        db.query(SurveySection)
        .filter(SurveySection.template_id == template_id)
        .order_by(SurveySection.orden.desc(), SurveySection.id.desc())
        .first()
    )
    return int(section.orden or 0) + 1 if section else 1


def _next_question_order(db: Session, section_id: int) -> int:
    question = (
        db.query(SurveyQuestion)
        .filter(SurveyQuestion.section_id == section_id)
        .order_by(SurveyQuestion.orden.desc(), SurveyQuestion.id.desc())
        .first()
    )
    return int(question.orden or 0) + 1 if question else 1


def _upsert_question_options(
    db: Session,
    question: SurveyQuestion,
    tenant_id: str,
    options: List[Dict[str, Any]],
) -> None:
    db.query(SurveyOption).filter(SurveyOption.question_id == question.id).delete(synchronize_session=False)
    for index, option in enumerate(options, start=1):
        db.add(
            SurveyOption(
                tenant_id=tenant_id,
                question_id=question.id,
                label=str(option.get("label") or f"Opcion {index}"),
                value=str(option.get("value") or option.get("label") or f"option_{index}"),
                orden=int(option.get("orden") or index),
                score_value=option.get("score_value"),
                is_correct=bool(option.get("is_correct", False)),
                config_json=option.get("config_json") or {},
            )
        )


def create_section(instance_id: int, tenant_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        instance = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not instance:
            return None
        if instance.status not in {"draft", "archived"}:
            raise ValueError("Solo se pueden agregar secciones en encuestas editables.")
        section = SurveySection(
            tenant_id=tenant_id,
            template_id=instance.template_id,
            instance_id=instance.id,
            titulo=str(data.get("titulo") or "Nueva seccion"),
            descripcion=data.get("descripcion"),
            orden=int(data.get("orden") or _next_section_order(db, instance.template_id)),
            is_required=bool(data.get("is_required", False)),
            settings_json=data.get("settings_json") or {},
        )
        db.add(section)
        instance.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(section)
        return _section_dict(section)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_section(instance_id: int, section_id: int, tenant_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        section = (
            db.query(SurveySection)
            .join(SurveyInstance, SurveySection.instance_id == SurveyInstance.id)
            .filter(
                SurveySection.id == section_id,
                SurveySection.instance_id == instance_id,
                SurveySection.tenant_id == tenant_id,
                SurveyInstance.tenant_id == tenant_id,
            )
            .first()
        )
        if not section:
            return None
        if section.instance and section.instance.status not in {"draft", "archived"}:
            raise ValueError("Solo se pueden editar secciones en encuestas editables.")
        for key, value in data.items():
            if value is not None:
                setattr(section, key, value)
        section.updated_at = datetime.utcnow()
        if section.instance:
            section.instance.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(section)
        return _section_dict(section)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def reorder_sections(instance_id: int, tenant_id: str, section_ids: List[int]) -> bool:
    db = get_db()
    try:
        total = (
            db.query(SurveySection.id)
            .filter(
                SurveySection.instance_id == instance_id,
                SurveySection.tenant_id == tenant_id,
                SurveySection.id.in_(section_ids),
            )
            .count()
        )
        if total != len(section_ids):
            return False
        temp_offset = len(section_ids) + 1000
        for index, section_id in enumerate(section_ids, start=1):
            db.query(SurveySection).filter(SurveySection.id == section_id).update(
                {"orden": temp_offset + index, "updated_at": datetime.utcnow()},
                synchronize_session=False,
            )
        db.commit()
        for index, section_id in enumerate(section_ids, start=1):
            db.query(SurveySection).filter(SurveySection.id == section_id).update(
                {"orden": index, "updated_at": datetime.utcnow()},
                synchronize_session=False,
            )
        instance = db.query(SurveyInstance).filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id).first()
        if instance:
            instance.updated_at = datetime.utcnow()
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def create_question(instance_id: int, section_id: int, tenant_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        section = (
            db.query(SurveySection)
            .join(SurveyInstance, SurveySection.instance_id == SurveyInstance.id)
            .filter(
                SurveySection.id == section_id,
                SurveySection.instance_id == instance_id,
                SurveySection.tenant_id == tenant_id,
                SurveyInstance.tenant_id == tenant_id,
            )
            .first()
        )
        if not section:
            return None
        if section.instance and section.instance.status not in {"draft", "archived"}:
            raise ValueError("Solo se pueden agregar preguntas en encuestas editables.")
        payload = normalize_question_payload(data)
        question = SurveyQuestion(
            tenant_id=tenant_id,
            template_id=section.template_id,
            section_id=section.id,
            question_key=payload.get("question_key"),
            titulo=str(payload.get("titulo") or "Nueva pregunta"),
            descripcion=payload.get("descripcion"),
            question_type=str(payload.get("question_type") or "short_text"),
            orden=int(payload.get("orden") or _next_question_order(db, section.id)),
            is_required=bool(payload.get("is_required", False)),
            is_scored=bool(payload.get("is_scored", False)),
            max_score=payload.get("max_score"),
            min_score=payload.get("min_score"),
            config_json=payload.get("config_json") or {},
            validation_json=payload.get("validation_json") or {},
            logic_json=payload.get("logic_json") or {},
        )
        db.add(question)
        db.flush()
        _upsert_question_options(db, question, tenant_id, payload.get("options") or [])
        if section.instance:
            section.instance.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(question)
        return _question_dict(question)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_question(instance_id: int, question_id: int, tenant_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        question = (
            db.query(SurveyQuestion)
            .join(SurveySection, SurveyQuestion.section_id == SurveySection.id)
            .join(SurveyInstance, SurveySection.instance_id == SurveyInstance.id)
            .filter(
                SurveyQuestion.id == question_id,
                SurveySection.instance_id == instance_id,
                SurveyQuestion.tenant_id == tenant_id,
                SurveyInstance.tenant_id == tenant_id,
            )
            .first()
        )
        if not question:
            return None
        if question.section and question.section.instance and question.section.instance.status not in {"draft", "archived"}:
            raise ValueError("Solo se pueden editar preguntas en encuestas editables.")
        merged_payload = {
            "question_key": question.question_key,
            "titulo": question.titulo,
            "descripcion": question.descripcion,
            "question_type": question.question_type,
            "orden": question.orden,
            "is_required": question.is_required,
            "is_scored": question.is_scored,
            "max_score": question.max_score,
            "min_score": question.min_score,
            "config_json": question.config_json or {},
            "validation_json": question.validation_json or {},
            "logic_json": question.logic_json or {},
            "options": [
                {
                    "label": option.label,
                    "value": option.value,
                    "orden": option.orden,
                    "score_value": option.score_value,
                    "is_correct": option.is_correct,
                    "config_json": option.config_json or {},
                }
                for option in (question.options or [])
            ],
        }
        merged_payload.update(data)
        payload = normalize_question_payload(merged_payload)
        options = payload.pop("options", None)
        for key, value in payload.items():
            if value is not None:
                setattr(question, key, value)
        question.updated_at = datetime.utcnow()
        if options is not None:
            _upsert_question_options(db, question, tenant_id, options)
        if question.section and question.section.instance:
            question.section.instance.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(question)
        return _question_dict(question)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def duplicate_question(instance_id: int, question_id: int, tenant_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        question = (
            db.query(SurveyQuestion)
            .join(SurveySection, SurveyQuestion.section_id == SurveySection.id)
            .join(SurveyInstance, SurveySection.instance_id == SurveyInstance.id)
            .filter(
                SurveyQuestion.id == question_id,
                SurveySection.instance_id == instance_id,
                SurveyQuestion.tenant_id == tenant_id,
                SurveyInstance.tenant_id == tenant_id,
            )
            .first()
        )
        if not question:
            return None
        cloned = SurveyQuestion(
            tenant_id=tenant_id,
            template_id=question.template_id,
            section_id=question.section_id,
            question_key=(f"{question.question_key}_copy" if question.question_key else None),
            titulo=f"{question.titulo} (copia)",
            descripcion=question.descripcion,
            question_type=question.question_type,
            orden=_next_question_order(db, question.section_id),
            is_required=question.is_required,
            is_scored=question.is_scored,
            max_score=question.max_score,
            min_score=question.min_score,
            config_json=question.config_json or {},
            validation_json=question.validation_json or {},
            logic_json=question.logic_json or {},
        )
        db.add(cloned)
        db.flush()
        _upsert_question_options(
            db,
            cloned,
            tenant_id,
            [
                {
                    "label": option.label,
                    "value": option.value,
                    "orden": option.orden,
                    "score_value": option.score_value,
                    "is_correct": option.is_correct,
                    "config_json": option.config_json or {},
                }
                for option in (question.options or [])
            ],
        )
        if question.section and question.section.instance:
            question.section.instance.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(cloned)
        return _question_dict(cloned)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def reorder_questions(instance_id: int, section_id: int, tenant_id: str, question_ids: List[int]) -> bool:
    db = get_db()
    try:
        total = (
            db.query(SurveyQuestion.id)
            .join(SurveySection, SurveyQuestion.section_id == SurveySection.id)
            .filter(
                SurveySection.instance_id == instance_id,
                SurveySection.id == section_id,
                SurveyQuestion.tenant_id == tenant_id,
                SurveyQuestion.id.in_(question_ids),
            )
            .count()
        )
        if total != len(question_ids):
            return False
        temp_offset = len(question_ids) + 1000
        for index, question_id in enumerate(question_ids, start=1):
            db.query(SurveyQuestion).filter(SurveyQuestion.id == question_id).update(
                {"orden": temp_offset + index, "updated_at": datetime.utcnow()},
                synchronize_session=False,
            )
        db.commit()
        for index, question_id in enumerate(question_ids, start=1):
            db.query(SurveyQuestion).filter(SurveyQuestion.id == question_id).update(
                {"orden": index, "updated_at": datetime.utcnow()},
                synchronize_session=False,
            )
        instance = db.query(SurveyInstance).filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id).first()
        if instance:
            instance.updated_at = datetime.utcnow()
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def validate_instance_for_publish(instance_id: int, tenant_id: str) -> Dict[str, Any]:
    db = get_db()
    try:
        obj = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not obj:
            return {"ok": False, "errors": ["Encuesta no encontrada."]}
        return validate_instance_for_publish_db(obj)
    finally:
        db.close()


def validate_instance_for_publish_db(obj: SurveyInstance) -> Dict[str, Any]:
    errors: List[str] = []
    sections = obj.sections or []
    if not str(obj.nombre or "").strip():
        errors.append("La encuesta requiere nombre.")
    if not sections:
        errors.append("La encuesta debe tener al menos una sección.")
    if sections and not any((section.questions or []) for section in sections):
        errors.append("La encuesta debe tener al menos una pregunta.")
    if obj.audience_mode != "public_link" and len(obj.assignments or []) == 0:
        errors.append("La encuesta requiere al menos una asignación materializada o enlace público.")
    for section in sections:
        if not str(section.titulo or "").strip():
            errors.append("Todas las secciones deben tener título.")
        for question in section.questions or []:
            if not str(question.titulo or "").strip():
                errors.append("Todas las preguntas deben tener enunciado.")
            definition = get_question_type_definition(question.question_type)
            if definition.get("requires_options") and len(question.options or []) == 0:
                errors.append(f"La pregunta '{question.titulo}' requiere opciones.")
            if question.question_type == "quiz_single_choice":
                correct_count = sum(1 for option in (question.options or []) if option.is_correct)
                if correct_count != 1:
                    errors.append(f"La pregunta '{question.titulo}' requiere exactamente una opción correcta.")
    return {"ok": len(errors) == 0, "errors": errors}


def _refresh_instance_lifecycle(
    db: Session,
    instance_id: Optional[int] = None,
    tenant_id: Optional[str] = None,
) -> None:
    now = datetime.utcnow()
    query = db.query(SurveyInstance)
    if tenant_id:
        query = query.filter(SurveyInstance.tenant_id == tenant_id)
    if instance_id is not None:
        query = query.filter(SurveyInstance.id == instance_id)
    changed = False
    for obj in query.all():
        next_status = obj.status
        published_at = obj.published_at
        closed_at = obj.closed_at
        if obj.status in {"draft", "scheduled"} and obj.schedule_start_at and obj.schedule_start_at > now:
            next_status = "scheduled"
        elif obj.status == "scheduled" and obj.schedule_start_at and obj.schedule_start_at <= now:
            next_status = "published"
            published_at = published_at or now
        if obj.status in {"published", "scheduled"} and obj.schedule_end_at and obj.schedule_end_at <= now:
            if obj.status != "closed":
                _record_dispatch_log(
                    db,
                    obj,
                    dispatch_type="auto_close",
                    dispatch_status="applied",
                    message_text=f"Cierre automático ejecutado para la encuesta '{obj.nombre}'.",
                    metadata_json={"schedule_end_at": _dt(obj.schedule_end_at)},
                )
            next_status = "closed"
            closed_at = closed_at or now
        if next_status != obj.status or published_at != obj.published_at or closed_at != obj.closed_at:
            obj.status = next_status
            obj.published_at = published_at
            obj.closed_at = closed_at
            obj.updated_at = now
            changed = True
    if changed:
        db.commit()


def _load_user_directory() -> List[Dict[str, Any]]:
    db = get_db()
    try:
        rows = db.execute(
            text(
                """
                SELECT
                    id,
                    full_name AS nombre,
                    username AS usuario,
                    role,
                    departamento,
                    puesto,
                    jefe_inmediato_id,
                    jefe
                FROM users
                WHERE is_active = 1
                ORDER BY full_name ASC, username ASC, id ASC
                """
            )
        ).mappings().all()
        names_by_id = {int(row["id"]): (str(row["nombre"] or row["usuario"] or "")).strip() for row in rows}
        payload = []
        for user in rows:
            payload.append(
                {
                    "user_id": int(user["id"]),
                    "user_key": str(user["id"]),
                    "nombre": (str(user["nombre"] or user["usuario"] or "")).strip(),
                    "usuario": (str(user["usuario"] or "")).strip(),
                    "role": (str(user["role"] or "")).strip(),
                    "departamento": (str(user["departamento"] or "")).strip(),
                    "puesto": (str(user["puesto"] or "")).strip(),
                    "jefe_inmediato_id": user["jefe_inmediato_id"],
                    "jefe": names_by_id.get(user["jefe_inmediato_id"], "") or (str(user["jefe"] or "")).strip(),
                    "empresa": "default",
                }
            )
        return payload
    finally:
        db.close()


def _load_capacitacion_courses() -> List[Dict[str, Any]]:
    try:
        from fastapi_modulo.modulos.capacitacion.cap_store import list_cursos

        rows = list_cursos()
        return [
            {
                "course_id": item.get("id"),
                "nombre": item.get("nombre"),
                "categoria": item.get("categoria_nombre") or item.get("categoria"),
                "nivel": item.get("nivel"),
                "estado": item.get("estado"),
            }
            for item in (rows or [])
        ]
    except Exception:
        return []


def _load_crm_contacts() -> List[Dict[str, Any]]:
    try:
        from fastapi_modulo.modulos.crm.modelos.crm_store import list_contactos

        rows = list_contactos()
        return [
            {
                "contact_id": item.get("id"),
                "nombre": item.get("nombre"),
                "email": item.get("email"),
                "telefono": item.get("telefono"),
                "empresa": item.get("empresa") or "",
                "puesto": item.get("puesto") or "",
                "tipo": item.get("tipo") or "prospecto",
            }
            for item in (rows or [])
        ]
    except Exception:
        return []


def list_integration_sources() -> Dict[str, Any]:
    users = _load_user_directory()
    departments = sorted({item["departamento"] for item in users if item.get("departamento")})
    positions = sorted({item["puesto"] for item in users if item.get("puesto")})
    roles = sorted({item["role"] for item in users if item.get("role")})
    managers = [item for item in users if item.get("jefe_inmediato_id")]
    return {
        "empleados": {
            "users": users,
            "departments": departments,
            "positions": positions,
            "roles": roles,
            "hierarchy_ready": bool(managers),
        },
        "capacitacion": {
            "courses": _load_capacitacion_courses(),
        },
        "crm": {
            "contacts": _load_crm_contacts(),
        },
    }


def _group_members_payload(members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    seen = set()
    for member in members:
        key = str(member.get("user_id") or member.get("user_key") or member.get("value") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "user_id": key,
                "nombre": str(member.get("nombre") or member.get("label") or key).strip(),
                "role": str(member.get("role") or "").strip(),
                "departamento": str(member.get("departamento") or "").strip(),
                "puesto": str(member.get("puesto") or "").strip(),
                "empresa": str(member.get("empresa") or "default").strip(),
            }
        )
    return normalized


def list_assignable_users() -> List[Dict[str, Any]]:
    return _load_user_directory()


def list_assignments(instance_id: int, tenant_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    try:
        rows = (
            db.query(SurveyAssignment)
            .filter(SurveyAssignment.instance_id == instance_id, SurveyAssignment.tenant_id == tenant_id)
            .order_by(SurveyAssignment.assignment_type.asc(), SurveyAssignment.assignee_name_snapshot.asc())
            .all()
        )
        return [_assignment_dict(row) for row in rows]
    finally:
        db.close()


def list_results(instance_id: int, tenant_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    try:
        rows = (
            db.query(SurveyResult)
            .filter(SurveyResult.instance_id == instance_id, SurveyResult.tenant_id == tenant_id)
            .order_by(SurveyResult.segment_type.asc(), SurveyResult.segment_key.asc(), SurveyResult.metric_key.asc())
            .all()
        )
        return [
            {
                "id": row.id,
                "instance_id": row.instance_id,
                "segment_type": row.segment_type,
                "segment_key": row.segment_key,
                "metric_key": row.metric_key,
                "metric_label": row.metric_label,
                "value_numeric": row.value_numeric,
                "value_text": row.value_text,
                "sample_size": row.sample_size,
                "result_json": row.result_json or {},
                "computed_at": _dt(row.computed_at),
            }
            for row in rows
        ]
    finally:
        db.close()


def list_dispatch_logs(instance_id: int, tenant_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    try:
        rows = (
            db.query(SurveyDispatchLog)
            .filter(SurveyDispatchLog.instance_id == instance_id, SurveyDispatchLog.tenant_id == tenant_id)
            .order_by(SurveyDispatchLog.dispatched_at.desc(), SurveyDispatchLog.id.desc())
            .all()
        )
        return [_dispatch_log_dict(row) for row in rows]
    finally:
        db.close()


def list_live_course_surveys(curso_id: int, tenant_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    try:
        rows = (
            db.query(SurveyInstance)
            .filter(
                SurveyInstance.tenant_id == tenant_id,
                SurveyInstance.source_app == "capacitacion",
                SurveyInstance.external_entity_type.in_(["curso", "course"]),
                SurveyInstance.external_entity_id == str(curso_id),
                SurveyInstance.status.in_(["published", "scheduled"]),
            )
            .order_by(SurveyInstance.updated_at.desc(), SurveyInstance.id.desc())
            .all()
        )
        payload = []
        for row in rows:
            instance_payload = _instance_dict(row)
            settings = instance_payload.get("settings_json") or {}
            payload.append(
                {
                    **instance_payload,
                    "is_live": bool(
                        settings.get("presentation_mode") == "mentimeter"
                        or settings.get("live_session_enabled")
                        or str(row.survey_type if row.template else "").strip().lower() in {"live", "live_poll", "mentimeter"}
                    ),
                }
            )
        return payload
    finally:
        db.close()


def _response_table_row(response: SurveyResponse) -> Dict[str, Any]:
    return {
        "response_id": response.id,
        "assignment_id": response.assignment_id,
        "respondent_key": response.respondent_key,
        "respondent_name": response.respondent_name_snapshot or "Sin identificar",
        "role": response.respondent_role_snapshot or "",
        "department": response.respondent_area_snapshot or "",
        "position": response.respondent_position_snapshot or "",
        "company": response.respondent_company_snapshot or "",
        "channel": response.submission_channel,
        "status": response.status,
        "completion_pct": response.completion_pct,
        "total_score": response.total_score,
        "started_at": _dt(response.started_at),
        "submitted_at": _dt(response.submitted_at),
        "last_saved_at": _dt(response.last_saved_at),
        "answers_json": response.answers_json or {},
        "metrics_json": response.metrics_json or {},
    }


def _question_report(instance: SurveyInstance, responses: List[SurveyResponse]) -> List[Dict[str, Any]]:
    items_by_question: Dict[int, List[SurveyResponseItem]] = {}
    for response in responses:
        for item in response.items or []:
            items_by_question.setdefault(item.question_id, []).append(item)

    report: List[Dict[str, Any]] = []
    for section in instance.sections or []:
        for question in section.questions or []:
            items = items_by_question.get(question.id, [])
            entry: Dict[str, Any] = {
                "question_id": question.id,
                "section_id": section.id,
                "section_title": section.titulo,
                "question_title": question.titulo,
                "question_type": question.question_type,
                "responses_count": len({item.response_id for item in items}),
                "avg_score": None,
                "options": [],
                "sample_answers": [],
            }
            score_values = [float(item.score_value) for item in items if item.score_value is not None]
            if score_values:
                entry["avg_score"] = round(sum(score_values) / len(score_values), 2)
            if question.question_type in {"single_choice", "live_poll_single_choice", "multiple_choice", "yes_no", "true_false", "quiz_single_choice", "scale_1_5", "live_scale_1_5", "nps_0_10", "dropdown", "image_choice"}:
                counts: Dict[str, Dict[str, Any]] = {}
                for option in question.options or []:
                    counts[str(option.value)] = {
                        "value": option.value,
                        "label": option.label,
                        "count": 0,
                    }
                for item in items:
                    key = str(item.answer_value or "")
                    if key in counts:
                        counts[key]["count"] += 1
                entry["options"] = list(counts.values())
            elif question.question_type == "ranking":
                samples = []
                for response_id in sorted({item.response_id for item in items}):
                    ranked = [
                        item.answer_text or item.answer_value
                        for item in sorted(
                            [candidate for candidate in items if candidate.response_id == response_id],
                            key=lambda candidate: candidate.item_index,
                        )
                    ]
                    if ranked:
                        samples.append(" > ".join(str(value) for value in ranked if str(value).strip()))
                    if len(samples) >= 5:
                        break
                entry["sample_answers"] = samples
            elif question.question_type in {"matrix", "likert_scale", "semantic_differential"}:
                samples = []
                for item in items[:10]:
                    text = str(item.answer_text or "").strip()
                    if text:
                        samples.append(text)
                entry["sample_answers"] = samples[:5]
            elif question.question_type == "word_cloud":
                cloud: Dict[str, int] = {}
                samples = []
                for item in items:
                    text = str(item.answer_text or item.answer_value or "").strip()
                    if not text:
                        continue
                    samples.append(text)
                    for token in text.lower().replace(",", " ").replace(".", " ").split():
                        clean = token.strip()
                        if len(clean) < 2:
                            continue
                        cloud[clean] = cloud.get(clean, 0) + 1
                entry["word_cloud"] = [
                    {"token": token, "count": count}
                    for token, count in sorted(cloud.items(), key=lambda item: (-item[1], item[0]))[:20]
                ]
                entry["sample_answers"] = samples[:5]
            else:
                samples = []
                for item in items:
                    if question.question_type == "file_upload":
                        payload = item.answer_json or {}
                        text = str(payload.get("name") or item.answer_text or item.answer_value or "").strip()
                    else:
                        text = str(item.answer_text or item.answer_value or "").strip()
                    if text:
                        samples.append(text)
                    if len(samples) >= 5:
                        break
                entry["sample_answers"] = samples
            report.append(entry)
    return report


def _segment_report(responses: List[SurveyResponse], field_name: str, label: str) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}
    for response in responses:
        key = str(getattr(response, field_name) or "Sin dato").strip() or "Sin dato"
        bucket = buckets.setdefault(
            key,
            {"segment": key, "label": label, "responses": 0, "completion_values": [], "score_values": []},
        )
        bucket["responses"] += 1
        bucket["completion_values"].append(float(response.completion_pct or 0))
        if response.total_score is not None:
            bucket["score_values"].append(float(response.total_score))
    return [
        {
            "segment": key,
            "label": payload["label"],
            "responses": payload["responses"],
            "completion_pct_avg": round(sum(payload["completion_values"]) / len(payload["completion_values"]), 2) if payload["completion_values"] else None,
            "score_avg": round(sum(payload["score_values"]) / len(payload["score_values"]), 2) if payload["score_values"] else None,
        }
        for key, payload in sorted(buckets.items(), key=lambda item: (-item[1]["responses"], item[0]))
    ]


def _quiz_ranking(instance: SurveyInstance) -> List[Dict[str, Any]]:
    quiz = _quiz_settings(instance)
    if not quiz["is_quiz"]:
        return []
    ranking: List[Dict[str, Any]] = []
    for assignment in instance.assignments or []:
        attempts = [attempt for attempt in (assignment.attempts or []) if attempt.status == "submitted"]
        best_attempt = _best_attempt_payload(attempts, quiz["attempt_strategy"])
        if not best_attempt:
            continue
        evaluation_status = (best_attempt.get("result_json") or {}).get("evaluation_status")
        ranking.append(
            {
                "assignee_key": assignment.assignee_key,
                "assignee_name": assignment.assignee_name_snapshot or assignment.assignee_key,
                "score_value": best_attempt["score_value"],
                "attempt_number": best_attempt["attempt_number"],
                "elapsed_seconds": best_attempt["elapsed_seconds"],
                "submitted_at": best_attempt["submitted_at"],
                "evaluation_status": evaluation_status,
            }
        )
    ranking.sort(
        key=lambda item: (
            -float(item.get("score_value") or 0),
            float(item.get("elapsed_seconds") or 10**9),
            item.get("assignee_name") or "",
        )
    )
    for index, item in enumerate(ranking, start=1):
        item["rank"] = index
    return ranking


def _report_360(instance: SurveyInstance) -> Dict[str, Any]:
    if not _is_360_instance(instance):
        return {"enabled": False, "links": [], "by_relationship": [], "by_competency": [], "by_evaluatee": []}
    submitted_responses = [
        response for response in (instance.responses or [])
        if response.status == "submitted" and str(response.external_entity_type or "") == "evaluation_360"
    ]
    links = [_evaluation_360_dict(row) for assignment in (instance.assignments or []) for row in (assignment.evaluations_360 or [])]
    relationship_buckets: Dict[str, Dict[str, Any]] = {}
    competency_buckets: Dict[str, Dict[str, Any]] = {}
    evaluatee_buckets: Dict[str, Dict[str, Any]] = {}
    for response in submitted_responses:
        evaluation_id = str(response.external_entity_id or "").strip()
        evaluation = next((row for row in links if str(row["id"]) == evaluation_id), None)
        if not evaluation:
            continue
        rel_key = str(evaluation.get("relationship_type") or "unknown")
        rel_bucket = relationship_buckets.setdefault(rel_key, {"relationship_type": rel_key, "responses": 0, "scores": []})
        rel_bucket["responses"] += 1
        if response.total_score is not None:
            rel_bucket["scores"].append(float(response.total_score))

        evaluatee_key = str(evaluation.get("evaluatee_key") or "unknown")
        eval_bucket = evaluatee_buckets.setdefault(
            evaluatee_key,
            {
                "evaluatee_key": evaluatee_key,
                "evaluatee_name": evaluation.get("evaluatee_name_snapshot") or evaluatee_key,
                "responses": 0,
                "scores": [],
            },
        )
        eval_bucket["responses"] += 1
        if response.total_score is not None:
            eval_bucket["scores"].append(float(response.total_score))

        for competency in (response.metrics_json or {}).get("competency_scores", {}).values():
            comp_key = str(competency.get("competency_key") or "general")
            comp_bucket = competency_buckets.setdefault(
                comp_key,
                {
                    "competency_key": comp_key,
                    "competency_label": competency.get("competency_label") or comp_key,
                    "responses": 0,
                    "scores": [],
                },
            )
            comp_bucket["responses"] += 1
            if competency.get("score_avg") is not None:
                comp_bucket["scores"].append(float(competency["score_avg"]))
    return {
        "enabled": True,
        "links": links,
        "by_relationship": [
            {
                "relationship_type": key,
                "responses": payload["responses"],
                "score_avg": round(sum(payload["scores"]) / len(payload["scores"]), 2) if payload["scores"] else None,
            }
            for key, payload in sorted(relationship_buckets.items())
        ],
        "by_competency": [
            {
                "competency_key": key,
                "competency_label": payload["competency_label"],
                "responses": payload["responses"],
                "score_avg": round(sum(payload["scores"]) / len(payload["scores"]), 2) if payload["scores"] else None,
            }
            for key, payload in sorted(competency_buckets.items())
        ],
        "by_evaluatee": [
            {
                "evaluatee_key": key,
                "evaluatee_name": payload["evaluatee_name"],
                "responses": payload["responses"],
                "score_avg": round(sum(payload["scores"]) / len(payload["scores"]), 2) if payload["scores"] else None,
            }
            for key, payload in sorted(evaluatee_buckets.items(), key=lambda item: item[1]["evaluatee_name"])
        ],
    }


def _responses_metrics_frame(response_rows: List[Dict[str, Any]]) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []
    for row in response_rows:
        metrics = row.get("metrics_json") or {}
        records.append(
            {
                "response_id": row.get("response_id"),
                "department": row.get("department") or "Sin dato",
                "role": row.get("role") or "Sin dato",
                "company": row.get("company") or "Sin dato",
                "status": row.get("status") or "",
                "completion_pct": float(row.get("completion_pct") or 0),
                "total_score": float(row["total_score"]) if row.get("total_score") is not None else None,
                "quiz_approval_pct": float(metrics.get("quiz_approval_pct") or 0),
                "nps_score": float(metrics.get("nps_score") or 0),
                "csat_score": float(metrics.get("csat_score") or 0),
                "ces_score": float(metrics.get("ces_score") or 0),
                "evaluation_status": str(metrics.get("evaluation_status") or ""),
            }
        )
    return pd.DataFrame(
        records,
        columns=[
            "response_id",
            "department",
            "role",
            "company",
            "status",
            "completion_pct",
            "total_score",
            "quiz_approval_pct",
            "nps_score",
            "csat_score",
            "ces_score",
            "evaluation_status",
        ],
    )


def _filter_options_from_frame(frame: pd.DataFrame) -> Dict[str, List[str]]:
    if frame.empty:
        return {"departments": [], "roles": [], "companies": []}
    return {
        "departments": sorted({str(value).strip() for value in frame["department"].dropna().tolist() if str(value).strip()}),
        "roles": sorted({str(value).strip() for value in frame["role"].dropna().tolist() if str(value).strip()}),
        "companies": sorted({str(value).strip() for value in frame["company"].dropna().tolist() if str(value).strip()}),
    }


def _apply_dashboard_filters(frame: pd.DataFrame, filters: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    filtered = frame.copy()
    criteria = filters or {}
    for key in ("department", "role", "company"):
        value = str(criteria.get(key) or "").strip()
        if value and not filtered.empty:
            filtered = filtered[filtered[key].fillna("Sin dato") == value]
    return filtered


def _summary_from_frame(frame: pd.DataFrame) -> Dict[str, Any]:
    if frame.empty:
        return {
            "responses_count": 0,
            "completion_pct_avg": 0,
            "total_score_avg": None,
            "quiz_approval_pct": 0,
            "approved_count": 0,
            "failed_count": 0,
            "nps_score": 0,
            "csat_score": 0,
            "ces_score": 0,
        }
    approved = int((frame["evaluation_status"] == "approved").sum()) if "evaluation_status" in frame else 0
    failed = int((frame["evaluation_status"] == "failed").sum()) if "evaluation_status" in frame else 0
    return {
        "responses_count": int(len(frame.index)),
        "completion_pct_avg": round(float(frame["completion_pct"].fillna(0).mean()), 2),
        "total_score_avg": round(float(frame["total_score"].dropna().mean()), 2) if frame["total_score"].dropna().size else None,
        "quiz_approval_pct": round(float(frame["quiz_approval_pct"].fillna(0).mean()), 2),
        "approved_count": approved,
        "failed_count": failed,
        "nps_score": round(float(frame["nps_score"].fillna(0).mean()), 2),
        "csat_score": round(float(frame["csat_score"].fillna(0).mean()), 2),
        "ces_score": round(float(frame["ces_score"].fillna(0).mean()), 2),
    }


def _segment_report_from_frame(frame: pd.DataFrame, field_name: str, label: str) -> List[Dict[str, Any]]:
    if frame.empty:
        return []
    grouped = (
        frame.assign(**{field_name: frame[field_name].fillna("Sin dato")})
        .groupby(field_name, dropna=False)
        .agg(
            responses=("response_id", "count"),
            completion_pct_avg=("completion_pct", "mean"),
            score_avg=("total_score", "mean"),
        )
        .reset_index()
        .sort_values(by=["responses", field_name], ascending=[False, True])
    )
    rows: List[Dict[str, Any]] = []
    for _, row in grouped.iterrows():
        rows.append(
            {
                "segment": str(row[field_name] or "Sin dato"),
                "label": label,
                "responses": int(row["responses"]),
                "completion_pct_avg": round(float(row["completion_pct_avg"]), 2) if pd.notna(row["completion_pct_avg"]) else None,
                "score_avg": round(float(row["score_avg"]), 2) if pd.notna(row["score_avg"]) else None,
            }
        )
    return rows


def _comparison_report_from_frame(frame: pd.DataFrame, segment_by: str) -> List[Dict[str, Any]]:
    if frame.empty or segment_by not in {"department", "role", "company"}:
        return []
    grouped = (
        frame.assign(**{segment_by: frame[segment_by].fillna("Sin dato")})
        .groupby(segment_by, dropna=False)
        .agg(
            responses=("response_id", "count"),
            completion_pct_avg=("completion_pct", "mean"),
            total_score_avg=("total_score", "mean"),
            nps_score=("nps_score", "mean"),
            csat_score=("csat_score", "mean"),
            ces_score=("ces_score", "mean"),
        )
        .reset_index()
        .sort_values(by=["responses", segment_by], ascending=[False, True])
    )
    output: List[Dict[str, Any]] = []
    for _, row in grouped.iterrows():
        output.append(
            {
                "segment_by": segment_by,
                "segment": str(row[segment_by] or "Sin dato"),
                "responses": int(row["responses"]),
                "completion_pct_avg": round(float(row["completion_pct_avg"]), 2) if pd.notna(row["completion_pct_avg"]) else None,
                "total_score_avg": round(float(row["total_score_avg"]), 2) if pd.notna(row["total_score_avg"]) else None,
                "nps_score": round(float(row["nps_score"]), 2) if pd.notna(row["nps_score"]) else None,
                "csat_score": round(float(row["csat_score"]), 2) if pd.notna(row["csat_score"]) else None,
                "ces_score": round(float(row["ces_score"]), 2) if pd.notna(row["ces_score"]) else None,
            }
        )
    return output


def get_results_dashboard(
    instance_id: int,
    tenant_id: str,
    filters: Optional[Dict[str, str]] = None,
    segment_by: str = "department",
) -> Dict[str, Any]:
    db = get_db()
    try:
        instance = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not instance:
            raise ValueError("Encuesta no encontrada.")
        submitted_responses = [
            response for response in (instance.responses or [])
            if response.status == "submitted"
        ]
        all_response_rows = [_response_table_row(response) for response in submitted_responses]
        metrics_frame = _responses_metrics_frame(all_response_rows)
        filtered_frame = _apply_dashboard_filters(metrics_frame, filters=filters)
        selected_ids = {int(value) for value in filtered_frame["response_id"].tolist()} if not filtered_frame.empty else set()
        filtered_responses = [response for response in submitted_responses if response.id in selected_ids] if filters else submitted_responses
        response_rows = [row for row in all_response_rows if row["response_id"] in selected_ids] if filters else all_response_rows
        general_results = list_results(instance_id, tenant_id)
        ranking = _quiz_ranking(instance)
        report_360 = _report_360(instance)
        return {
            "instance": _instance_dict(instance),
            "summary": _summary_from_frame(filtered_frame if filters else metrics_frame),
            "quiz": {
                "settings": _quiz_settings(instance),
                "ranking": ranking[:20],
            },
            "report_360": report_360,
            "question_report": _question_report(instance, filtered_responses),
            "segment_report": {
                "department": _segment_report_from_frame(filtered_frame if filters else metrics_frame, "department", "Departamento"),
                "role": _segment_report_from_frame(filtered_frame if filters else metrics_frame, "role", "Rol"),
                "company": _segment_report_from_frame(filtered_frame if filters else metrics_frame, "company", "Empresa"),
            },
            "comparison_report": _comparison_report_from_frame(filtered_frame if filters else metrics_frame, segment_by),
            "available_filters": _filter_options_from_frame(metrics_frame),
            "applied_filters": {
                "department": str((filters or {}).get("department") or "").strip(),
                "role": str((filters or {}).get("role") or "").strip(),
                "company": str((filters or {}).get("company") or "").strip(),
                "segment_by": segment_by,
            },
            "responses_table": response_rows,
            "results": general_results,
        }
    finally:
        db.close()


def _question_export_columns(dashboard: Dict[str, Any]) -> List[Dict[str, str]]:
    columns: List[Dict[str, str]] = []
    for item in dashboard.get("question_report", []):
        question_id = str(item.get("question_id") or "").strip()
        if not question_id:
            continue
        label = str(item.get("question_title") or f"Pregunta {question_id}").strip()
        section = str(item.get("section_title") or "").strip()
        header = f"[{question_id}] {section} · {label}" if section else f"[{question_id}] {label}"
        columns.append({"question_id": question_id, "header": header})
    return columns


def _responses_export_dataframe(dashboard: Dict[str, Any]) -> pd.DataFrame:
    MAIN_columns = [
        "response_id",
        "respondent_name",
        "role",
        "department",
        "position",
        "company",
        "channel",
        "status",
        "completion_pct",
        "total_score",
        "started_at",
        "submitted_at",
    ]
    question_columns = _question_export_columns(dashboard)
    rows: List[Dict[str, Any]] = []
    for row in dashboard.get("responses_table", []):
        payload = {key: row.get(key, "") for key in MAIN_columns}
        answers = row.get("answers_json") or {}
        for item in question_columns:
            value = answers.get(item["question_id"])
            if isinstance(value, list):
                payload[item["header"]] = ", ".join(str(part) for part in value)
            else:
                payload[item["header"]] = value if value is not None else ""
        rows.append(payload)
    ordered_columns = MAIN_columns + [item["header"] for item in question_columns]
    return pd.DataFrame(rows, columns=ordered_columns)


def _results_frames(dashboard: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    summary_df = pd.DataFrame(
        [{"metric": key, "value": value} for key, value in (dashboard.get("summary") or {}).items()],
        columns=["metric", "value"],
    )
    questions_df = pd.DataFrame(
        [
            {
                "section_title": row.get("section_title"),
                "question_title": row.get("question_title"),
                "question_type": row.get("question_type"),
                "responses_count": row.get("responses_count"),
                "avg_score": row.get("avg_score"),
                "options_or_samples": str(row.get("options") or row.get("sample_answers") or row.get("word_cloud") or []),
            }
            for row in dashboard.get("question_report", [])
        ],
        columns=["section_title", "question_title", "question_type", "responses_count", "avg_score", "options_or_samples"],
    )
    segment_rows: List[Dict[str, Any]] = []
    for segment_type, rows in (dashboard.get("segment_report") or {}).items():
        for row in rows or []:
            segment_rows.append(
                {
                    "segment_type": segment_type,
                    "label": row.get("label"),
                    "segment": row.get("segment"),
                    "responses": row.get("responses"),
                    "completion_pct_avg": row.get("completion_pct_avg"),
                    "score_avg": row.get("score_avg"),
                }
            )
    segments_df = pd.DataFrame(
        segment_rows,
        columns=["segment_type", "label", "segment", "responses", "completion_pct_avg", "score_avg"],
    )
    return {
        "summary": summary_df,
        "questions": questions_df,
        "segments": segments_df,
        "responses": _responses_export_dataframe(dashboard),
    }


def export_results_csv(instance_id: int, tenant_id: str, dashboard: Optional[Dict[str, Any]] = None) -> str:
    dashboard = dashboard or get_results_dashboard(instance_id, tenant_id)
    output = StringIO()
    _results_frames(dashboard)["responses"].to_csv(output, index=False)
    return output.getvalue()


def export_results_excel(instance_id: int, tenant_id: str, dashboard: Optional[Dict[str, Any]] = None) -> bytes:
    dashboard = dashboard or get_results_dashboard(instance_id, tenant_id)
    frames = _results_frames(dashboard)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frames["summary"].to_excel(writer, index=False, sheet_name="Resumen")
        frames["questions"].to_excel(writer, index=False, sheet_name="Preguntas")
        frames["segments"].to_excel(writer, index=False, sheet_name="Segmentos")
        frames["responses"].to_excel(writer, index=False, sheet_name="Respuestas")
        for sheet_name, ws in writer.sheets.items():
            ws.freeze_panes = "A2"
            for idx, column_cells in enumerate(ws.columns, start=1):
                values = [str(cell.value or "") for cell in column_cells[:100]]
                width = min(max((len(value) for value in values), default=12) + 2, 42)
                ws.column_dimensions[get_column_letter(idx)].width = width
    return buffer.getvalue()


def export_results_pdf(instance_id: int, tenant_id: str, dashboard: Optional[Dict[str, Any]] = None) -> bytes:
    dashboard = dashboard or get_results_dashboard(instance_id, tenant_id)
    frames = _results_frames(dashboard)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"Encuesta: {dashboard.get('instance', {}).get('nombre', 'Resultados')}", styles["Title"]),
        Paragraph("Exportación PDF de resultados básicos", styles["Normal"]),
        Spacer(1, 12),
    ]
    applied_filters = dashboard.get("applied_filters") or {}
    active_filters = [
        f"Departamento: {applied_filters.get('department')}" if applied_filters.get("department") else "",
        f"Rol: {applied_filters.get('role')}" if applied_filters.get("role") else "",
        f"Empresa: {applied_filters.get('company')}" if applied_filters.get("company") else "",
        f"Comparativo por: {applied_filters.get('segment_by')}" if applied_filters.get("segment_by") else "",
    ]
    active_filters = [item for item in active_filters if item]
    if active_filters:
        story.extend([
            Paragraph("Filtros aplicados", styles["Heading2"]),
            Paragraph(" · ".join(active_filters), styles["Normal"]),
            Spacer(1, 12),
        ])

    summary_table = Table(
        [["Métrica", "Valor"]] + [
            [str(row["metric"]), str(row["value"] if row["value"] is not None else "")]
            for _, row in frames["summary"].iterrows()
        ],
        repeatRows=1,
    )
    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f8fafc")]),
        ])
    )
    story.extend([Paragraph("Resumen", styles["Heading2"]), summary_table, Spacer(1, 12)])

    question_rows = [["Sección", "Pregunta", "Tipo", "Resp.", "Score", "Detalle"]]
    for _, row in frames["questions"].head(20).iterrows():
        question_rows.append([
            str(row["section_title"] or ""),
            str(row["question_title"] or ""),
            str(row["question_type"] or ""),
            str(row["responses_count"] or 0),
            str(row["avg_score"] if row["avg_score"] is not None else ""),
            str(row["options_or_samples"] or "")[:110],
        ])
    question_table = Table(question_rows, repeatRows=1, colWidths=[110, 180, 90, 50, 60, 250])
    question_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    story.extend([Paragraph("Preguntas", styles["Heading2"]), question_table, Spacer(1, 12)])

    if not frames["segments"].empty:
        segment_rows = [["Tipo", "Etiqueta", "Segmento", "Respuestas", "Finalización", "Score"]]
        for _, row in frames["segments"].head(20).iterrows():
            segment_rows.append([
                str(row["segment_type"] or ""),
                str(row["label"] or ""),
                str(row["segment"] or ""),
                str(row["responses"] or 0),
                str(row["completion_pct_avg"] if row["completion_pct_avg"] is not None else ""),
                str(row["score_avg"] if row["score_avg"] is not None else ""),
            ])
        segment_table = Table(segment_rows, repeatRows=1, colWidths=[90, 90, 160, 70, 90, 70])
        segment_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c2410c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ])
        )
        story.extend([Paragraph("Segmentos", styles["Heading2"]), segment_table])
    comparison_rows = dashboard.get("comparison_report") or []
    if comparison_rows:
        comparison_table = Table(
            [["Segmento", "Respuestas", "Finalización", "Score", "NPS", "CSAT", "CES"]] + [
                [
                    str(row.get("segment") or ""),
                    str(row.get("responses") or 0),
                    str(row.get("completion_pct_avg") if row.get("completion_pct_avg") is not None else ""),
                    str(row.get("total_score_avg") if row.get("total_score_avg") is not None else ""),
                    str(row.get("nps_score") if row.get("nps_score") is not None else ""),
                    str(row.get("csat_score") if row.get("csat_score") is not None else ""),
                    str(row.get("ces_score") if row.get("ces_score") is not None else ""),
                ]
                for row in comparison_rows[:20]
            ],
            repeatRows=1,
            colWidths=[180, 70, 90, 70, 60, 60, 60],
        )
        comparison_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7c3aed")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ])
        )
        story.extend([Spacer(1, 12), Paragraph("Comparativo", styles["Heading2"]), comparison_table])

    doc.build(story)
    return buffer.getvalue()


def _ensure_notification_schema(db: Session) -> None:
    global _NOTIFICATION_SCHEMA_READY
    if _NOTIFICATION_SCHEMA_READY:
        return
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS conversation_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_username TEXT NOT NULL,
                to_usernames TEXT NOT NULL DEFAULT '[]',
                message_text TEXT NOT NULL DEFAULT '',
                scope TEXT NOT NULL DEFAULT 'conversation',
                conversation_id TEXT NOT NULL DEFAULT '',
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
    )
    _NOTIFICATION_SCHEMA_READY = True
    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_cn_to_read
            ON conversation_notifications(to_usernames, is_read, created_at)
            """
        )
    )


def _record_dispatch_log(
    db: Session,
    instance: SurveyInstance,
    dispatch_type: str,
    dispatch_status: str,
    assignment: Optional[SurveyAssignment] = None,
    message_text: str = "",
    metadata_json: Optional[Dict[str, Any]] = None,
) -> None:
    db.add(
        SurveyDispatchLog(
            tenant_id=instance.tenant_id,
            instance_id=instance.id,
            assignment_id=assignment.id if assignment else None,
            dispatch_type=dispatch_type,
            dispatch_status=dispatch_status,
            channel=str((assignment.channel if assignment else "system") or "system"),
            recipient_key=assignment.assignee_key if assignment else None,
            recipient_name_snapshot=assignment.assignee_name_snapshot if assignment else None,
            message_text=message_text,
            metadata_json=metadata_json or {},
            dispatched_at=datetime.utcnow(),
        )
    )


def _survey_backendhook_settings(instance: SurveyInstance) -> Dict[str, Any]:
    settings = instance.settings_json or {}
    rules = instance.publication_rules_json or {}
    backendhook_url = str(rules.get("backendhook_url") or settings.get("backendhook_url") or "").strip()
    events = rules.get("backendhook_events") or settings.get("backendhook_events") or ["response_submitted"]
    if not isinstance(events, list):
        events = [str(events)]
    timeout = float(rules.get("backendhook_timeout_seconds") or settings.get("backendhook_timeout_seconds") or 5)
    return {
        "enabled": bool(backendhook_url),
        "url": backendhook_url,
        "events": [str(event).strip() for event in events if str(event).strip()],
        "timeout_seconds": max(1.0, min(timeout, 15.0)),
    }


def _dispatch_survey_backendhook(
    db: Session,
    instance: SurveyInstance,
    event_name: str,
    payload: Dict[str, Any],
    assignment: Optional[SurveyAssignment] = None,
) -> None:
    config = _survey_backendhook_settings(instance)
    if not config["enabled"] or event_name not in config["events"]:
        return
    metadata = {
        "event": event_name,
        "backendhook_url": config["url"],
    }
    try:
        with httpx.Client(timeout=config["timeout_seconds"], follow_redirects=True) as client:
            response = client.post(
                config["url"],
                json={
                    "event": event_name,
                    "instance": {
                        "id": instance.id,
                        "nombre": instance.nombre,
                        "tenant_id": instance.tenant_id,
                    },
                    "payload": payload,
                    "sent_at": _dt(datetime.utcnow()),
                },
            )
        metadata["status_code"] = response.status_code
        metadata["response_text"] = (response.text or "")[:500]
        _record_dispatch_log(
            db,
            instance,
            dispatch_type=f"backendhook:{event_name}",
            dispatch_status="sent" if response.is_success else "failed",
            assignment=assignment,
            message_text=f"backendhook {event_name} enviado a {config['url']}.",
            metadata_json=metadata,
        )
        db.commit()
    except Exception as exc:
        metadata["error"] = str(exc)
        _record_dispatch_log(
            db,
            instance,
            dispatch_type=f"backendhook:{event_name}",
            dispatch_status="error",
            assignment=assignment,
            message_text=f"backendhook {event_name} falló para {config['url']}.",
            metadata_json=metadata,
        )
        db.commit()


def dispatch_backendhook_event(
    tenant_id: str,
    instance_id: int,
    event_name: str,
    payload: Dict[str, Any],
    assignment_id: Optional[int] = None,
) -> Dict[str, Any]:
    db = get_db()
    try:
        instance = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not instance:
            raise ValueError("Encuesta no encontrada.")
        assignment = None
        if assignment_id is not None:
            assignment = (
                db.query(SurveyAssignment)
                .filter(
                    SurveyAssignment.id == assignment_id,
                    SurveyAssignment.instance_id == instance_id,
                    SurveyAssignment.tenant_id == tenant_id,
                )
                .first()
            )
        _dispatch_survey_backendhook(db, instance, event_name, payload, assignment=assignment)
        return {
            "queued": False,
            "processed": True,
            "event": event_name,
            "instance_id": instance_id,
        }
    finally:
        db.close()


def _enqueue_celery_task(task_name: str, kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    runtime = _background_runtime_status()
    if not runtime["configured"]:
        return None
    try:
        from fastapi_modulo.modulos.encuestas.modelos.encuestas_tasks import get_celery_app

        task = get_celery_app().send_task(task_name, kwargs=kwargs, queue=runtime["queue_name"])
        return {
            "queued": True,
            "task_id": task.id,
            "queue_name": runtime["queue_name"],
            "engine": "celery",
        }
    except Exception:
        return None


def queue_automation_job(tenant_id: str, instance_id: Optional[int] = None) -> Dict[str, Any]:
    queued = _enqueue_celery_task(
        "encuestas.run_automation_jobs",
        {"tenant_id": tenant_id, "instance_id": instance_id},
    )
    if queued:
        return {
            **queued,
            "processed": False,
            "summary": None,
        }
    return {
        "queued": False,
        "processed": True,
        "engine": "manual_scheduler",
        "summary": run_automation_jobs(tenant_id, instance_id=instance_id),
    }


def queue_backendhook_event(
    tenant_id: str,
    instance_id: int,
    event_name: str,
    payload: Dict[str, Any],
    assignment_id: Optional[int] = None,
) -> Dict[str, Any]:
    queued = _enqueue_celery_task(
        "encuestas.dispatch_backendhook",
        {
            "tenant_id": tenant_id,
            "instance_id": instance_id,
            "event_name": event_name,
            "payload": payload,
            "assignment_id": assignment_id,
        },
    )
    if queued:
        return {
            **queued,
            "processed": False,
            "event": event_name,
            "instance_id": instance_id,
        }
    return dispatch_backendhook_event(
        tenant_id=tenant_id,
        instance_id=instance_id,
        event_name=event_name,
        payload=payload,
        assignment_id=assignment_id,
    )


def _send_assignment_notifications(
    db: Session,
    instance: SurveyInstance,
    assignments: List[SurveyAssignment],
    notification_kind: str = "invitation",
) -> int:
    internal_assignments = [
        assignment
        for assignment in assignments
        if str(assignment.channel or "").strip().lower() == "internal" and assignment.assignee_key
    ]
    if not internal_assignments:
        return 0
    _ensure_notification_schema(db)
    sent = 0
    ts = _notification_timestamp()
    for assignment in internal_assignments:
        if assignment.status == "completed":
            continue
        message = (
            f"Aviso de cierre: la encuesta '{instance.nombre}' está por cerrar. Responde cuanto antes."
            if notification_kind == "closing_soon"
            else
            f"Recordatorio: tienes pendiente responder la encuesta '{instance.nombre}'."
            if notification_kind == "reminder"
            else f"Tienes una nueva invitacion para responder la encuesta '{instance.nombre}'."
        )
        db.execute(
            text(
                """
                INSERT INTO conversation_notifications
                (from_username, to_usernames, message_text, scope, conversation_id, is_read, created_at)
                VALUES (:from_u, :to_u, :msg, :scope, :conv, 0, :ts)
                """
            ),
            {
                "from_u": str(instance.created_by or "sistema").strip().lower(),
                "to_u": f"[\"{str(assignment.assignee_key).strip().lower()}\"]",
                "msg": message,
                "scope": "survey",
                "conv": f"survey:{instance.id}",
                "ts": ts,
            },
        )
        now = datetime.utcnow()
        if not assignment.first_sent_at:
            assignment.first_sent_at = now
        assignment.last_sent_at = now
        _record_dispatch_log(
            db,
            instance,
            dispatch_type=notification_kind,
            dispatch_status="sent",
            assignment=assignment,
            message_text=message,
            metadata_json={
                "scope": "survey",
                "conversation_id": f"survey:{instance.id}",
            },
        )
        sent += 1
    return sent


def _should_send_closing_notice(instance: SurveyInstance, now: datetime) -> bool:
    if not instance.schedule_end_at:
        return False
    automation = _automation_settings(instance)
    hours = max(1, int(automation["closing_notice_hours"]))
    remaining_seconds = (instance.schedule_end_at - now).total_seconds()
    if remaining_seconds <= 0 or remaining_seconds > hours * 3600:
        return False
    return True


def _last_dispatch_for_type(
    db: Session,
    instance_id: int,
    tenant_id: str,
    dispatch_type: str,
) -> Optional[SurveyDispatchLog]:
    return (
        db.query(SurveyDispatchLog)
        .filter(
            SurveyDispatchLog.instance_id == instance_id,
            SurveyDispatchLog.tenant_id == tenant_id,
            SurveyDispatchLog.dispatch_type == dispatch_type,
        )
        .order_by(SurveyDispatchLog.dispatched_at.desc(), SurveyDispatchLog.id.desc())
        .first()
    )


def run_automation_jobs(tenant_id: str, instance_id: Optional[int] = None) -> Dict[str, Any]:
    db = get_db()
    try:
        now = datetime.utcnow()
        background = _background_runtime_status()
        query = db.query(SurveyInstance).filter(SurveyInstance.tenant_id == tenant_id)
        if instance_id is not None:
            query = query.filter(SurveyInstance.id == instance_id)
        instances = query.all()
        summary = {
            "processed_instances": 0,
            "invitations_sent": 0,
            "reminders_sent": 0,
            "closing_notices_sent": 0,
            "auto_closed": 0,
            "engine": background["engine"],
            "future": {
                "celery_ready": background["celery_ready"],
                "redis_ready": background["redis_ready"],
                "redis_error": background["redis_error"],
                "broker_configured": background["configured"],
                "queue_name": background["queue_name"],
            },
        }
        for instance in instances:
            automation = _automation_settings(instance)
            if not automation["enabled"]:
                continue
            summary["processed_instances"] += 1
            if instance.status in {"published", "scheduled"} and instance.schedule_end_at and instance.schedule_end_at <= now:
                if instance.status != "closed":
                    instance.status = "closed"
                    instance.closed_at = instance.closed_at or now
                    instance.updated_at = now
                    _record_dispatch_log(
                        db,
                        instance,
                        dispatch_type="auto_close",
                        dispatch_status="applied",
                        message_text=f"Cierre automático ejecutado para la encuesta '{instance.nombre}'.",
                        metadata_json={"schedule_end_at": _dt(instance.schedule_end_at)},
                    )
                    summary["auto_closed"] += 1
                continue
            if instance.status not in {"published", "scheduled"}:
                continue
            assignments = list(instance.assignments or [])
            pending_assignments = [assignment for assignment in assignments if assignment.status != "completed"]
            if pending_assignments and not any(assignment.first_sent_at for assignment in pending_assignments):
                summary["invitations_sent"] += _send_assignment_notifications(
                    db,
                    instance,
                    pending_assignments,
                    notification_kind="invitation",
                )
            reminder_due = []
            for assignment in pending_assignments:
                if assignment.first_sent_at and assignment.status in {"pending", "in_progress"}:
                    last_touch = assignment.last_sent_at or assignment.first_sent_at
                    elapsed_hours = (now - last_touch).total_seconds() / 3600 if last_touch else 0
                    if elapsed_hours >= max(1, int(automation["reminder_interval_hours"])):
                        reminder_due.append(assignment)
            if reminder_due:
                summary["reminders_sent"] += _send_assignment_notifications(
                    db,
                    instance,
                    reminder_due,
                    notification_kind="reminder",
                )
            if pending_assignments and _should_send_closing_notice(instance, now):
                last_notice = _last_dispatch_for_type(db, instance.id, tenant_id, "closing_soon")
                notice_recent = False
                if last_notice and last_notice.dispatched_at:
                    notice_recent = (now - last_notice.dispatched_at).total_seconds() < max(1, int(automation["closing_notice_hours"])) * 3600
                if not notice_recent:
                    summary["closing_notices_sent"] += _send_assignment_notifications(
                        db,
                        instance,
                        pending_assignments,
                        notification_kind="closing_soon",
                    )
        db.commit()
        return summary
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def _sync_evaluations_360(
    db: Session,
    instance: SurveyInstance,
    assignments: List[SurveyAssignment],
    users_by_id: Dict[str, Dict[str, Any]],
) -> None:
    if not _is_360_payload(instance.template.survey_type if instance.template else "", instance.external_entity_type or ""):
        return
    db.query(SurveyEvaluation360).filter(
        SurveyEvaluation360.instance_id == instance.id,
        SurveyEvaluation360.tenant_id == instance.tenant_id,
    ).delete(synchronize_session=False)

    assignments_by_key = {str(item.assignee_key): item for item in assignments if item.assignee_key}
    subordinates_by_manager: Dict[str, List[Dict[str, Any]]] = {}
    for user in users_by_id.values():
        manager_key = str(user.get("jefe_inmediato_id") or "").strip()
        if manager_key:
            subordinates_by_manager.setdefault(manager_key, []).append(user)

    links: set[tuple[str, str, str]] = set()

    def add_link(evaluator_key: str, evaluatee_key: str, relationship_type: str) -> None:
        evaluator = users_by_id.get(evaluator_key)
        evaluatee = users_by_id.get(evaluatee_key)
        assignment = assignments_by_key.get(evaluator_key)
        if not evaluator or not evaluatee or not assignment:
            return
        link_key = (evaluatee_key, evaluator_key, relationship_type)
        if link_key in links:
            return
        links.add(link_key)
        db.add(
            SurveyEvaluation360(
                tenant_id=instance.tenant_id,
                instance_id=instance.id,
                assignment_id=assignment.id,
                evaluatee_key=evaluatee_key,
                evaluator_key=evaluator_key,
                relationship_type=relationship_type,
                evaluatee_name_snapshot=evaluatee.get("nombre"),
                evaluatee_role_snapshot=evaluatee.get("role"),
                evaluatee_area_snapshot=evaluatee.get("departamento"),
                evaluatee_position_snapshot=evaluatee.get("puesto"),
                evaluatee_company_snapshot=evaluatee.get("empresa"),
                evaluator_name_snapshot=evaluator.get("nombre"),
                evaluator_role_snapshot=evaluator.get("role"),
                evaluator_area_snapshot=evaluator.get("departamento"),
                evaluator_position_snapshot=evaluator.get("puesto"),
                evaluator_company_snapshot=evaluator.get("empresa"),
                status="pending",
                source_app="empleados",
                external_entity_type="hierarchy_360",
                external_entity_id=f"{instance.id}:{relationship_type}:{evaluatee_key}:{evaluator_key}",
            )
        )

    for evaluator_key in assignments_by_key:
        add_link(evaluator_key, evaluator_key, "self")
        manager_key = str((users_by_id.get(evaluator_key) or {}).get("jefe_inmediato_id") or "").strip()
        if manager_key:
            add_link(evaluator_key, manager_key, "subordinate")
        for subordinate in subordinates_by_manager.get(evaluator_key, []):
            subordinate_key = str(subordinate.get("user_id") or "").strip()
            if subordinate_key:
                add_link(evaluator_key, subordinate_key, "manager")


def sync_assignments(instance_id: int, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    try:
        instance = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not instance:
            raise ValueError("Encuesta no encontrada.")
        user_directory = _load_user_directory()
        crm_contacts = _load_crm_contacts()
        users_by_id = {str(item["user_id"]): item for item in user_directory}
        crm_contacts_by_id = {str(item["id"]): item for item in crm_contacts}
        users_by_role: Dict[str, List[Dict[str, Any]]] = {}
        users_by_department: Dict[str, List[Dict[str, Any]]] = {}
        users_by_position: Dict[str, List[Dict[str, Any]]] = {}
        for item in user_directory:
            if item["role"]:
                users_by_role.setdefault(item["role"].lower(), []).append(item)
            if item["departamento"]:
                users_by_department.setdefault(item["departamento"].lower(), []).append(item)
            if item["puesto"]:
                users_by_position.setdefault(item["puesto"].lower(), []).append(item)

        due_at = payload.get("due_at")
        due_at_value = due_at if isinstance(due_at, datetime) else None
        rules = payload.get("assignment_rules") or {}
        entries = list(payload.get("assignments") or [])
        if (
            str(instance.source_app or "").strip().lower() == "capacitacion"
            and str(instance.external_entity_type or "").strip().lower() in {"curso", "course"}
            and str(instance.external_entity_id or "").strip().isdigit()
            and not entries
        ):
            enrollments = _load_capacitacion_enrollments(int(str(instance.external_entity_id)))
            enrolled_keys = [str(item.get("colaborador_key") or "").strip() for item in enrollments if item.get("colaborador_key")]
            if enrolled_keys:
                entries.append({"type": "user", "values": enrolled_keys})
        if (
            str(instance.source_app or "").strip().lower() == "crm"
            and str(instance.external_entity_type or "").strip().lower() in {"campania", "campaign", "crm_campaign"}
            and str(instance.external_entity_id or "").strip().isdigit()
            and not entries
        ):
            contacts = _load_crm_campaign_contacts(int(str(instance.external_entity_id)))
            contact_ids = [str(item["id"]) for item in contacts if item.get("id")]
            if contact_ids:
                entries.append({"type": "crm_contact", "values": contact_ids})
        if (
            str(instance.source_app or "").strip().lower() == "crm"
            and str(instance.external_entity_type or "").strip().lower() in {"contacto", "contact", "crm_contact"}
            and str(instance.external_entity_id or "").strip()
            and not entries
        ):
            entries.append({"type": "crm_contact", "values": [str(instance.external_entity_id)]})
        db.query(SurveyAssignment).filter(
            SurveyAssignment.instance_id == instance_id,
            SurveyAssignment.tenant_id == tenant_id,
        ).delete(synchronize_session=False)

        manual_groups = rules.get("manual_groups") or []
        groups_created: List[Dict[str, Any]] = []
        for group in manual_groups:
            group_name = str(group.get("name") or "").strip()
            members = _group_members_payload(group.get("members") or [])
            if not group_name or not members:
                continue
            audience_group = SurveyAudienceGroup(
                tenant_id=tenant_id,
                nombre=group_name,
                descripcion=str(group.get("description") or "").strip() or "Grupo manual de encuesta",
                source_app="encuestas",
                external_entity_type="manual_group",
                external_entity_id=f"{instance_id}:{group_name.lower().replace(' ', '-')}",
                filters_json={"source": "manual_group", "instance_id": instance_id},
                is_dynamic=False,
                created_by=instance.created_by,
            )
            db.add(audience_group)
            db.flush()
            groups_created.append({"group_id": audience_group.id, "members": members})
            for member in members:
                db.add(
                    SurveyAudienceGroupMember(
                        tenant_id=tenant_id,
                        group_id=audience_group.id,
                        member_key=str(member["user_id"]),
                        member_name_snapshot=member["nombre"],
                        member_role_snapshot=member["role"],
                        member_area_snapshot=member["departamento"],
                        member_position_snapshot=member["puesto"],
                        member_company_snapshot=member["empresa"],
                        source_app="encuestas",
                        external_entity_type="manual_group",
                        external_entity_id=str(audience_group.id),
                    )
                )

        materialized: Dict[str, Dict[str, Any]] = {}

        def add_candidate(
            candidate_payload: Dict[str, Any],
            assignment_type: str,
            audience_group_id: Optional[int] = None,
            source_app: str = "encuestas",
            external_entity_type: str = "user",
            external_entity_id: Optional[str] = None,
            channel: Optional[str] = None,
        ):
            key = str(candidate_payload.get("user_id") or candidate_payload.get("assignee_key") or candidate_payload.get("id") or "").strip()
            if not key:
                return
            materialized[key] = {
                "audience_group_id": audience_group_id,
                "assignee_key": key,
                "assignee_name_snapshot": candidate_payload.get("nombre") or candidate_payload.get("assignee_name_snapshot") or key,
                "assignee_role_snapshot": candidate_payload.get("role") or candidate_payload.get("assignee_role_snapshot") or "",
                "assignee_area_snapshot": candidate_payload.get("departamento") or candidate_payload.get("assignee_area_snapshot") or "",
                "assignee_position_snapshot": candidate_payload.get("puesto") or candidate_payload.get("assignee_position_snapshot") or "",
                "assignee_company_snapshot": candidate_payload.get("empresa") or candidate_payload.get("assignee_company_snapshot") or "",
                "assignment_type": assignment_type,
                "source_app": source_app,
                "external_entity_type": external_entity_type,
                "external_entity_id": external_entity_id or key,
                "channel": channel or ("public_link" if instance.audience_mode == "public_link" else "internal"),
            }

        for entry in entries:
            entry_type = str(entry.get("type") or "").strip().lower()
            values = entry.get("values") or []
            if entry_type == "user":
                for value in values:
                    user = users_by_id.get(str(value))
                    if user:
                        add_candidate(user, "user")
            elif entry_type == "role":
                for value in values:
                    for user in users_by_role.get(str(value).lower(), []):
                        add_candidate(user, "role")
            elif entry_type == "department":
                for value in values:
                    for user in users_by_department.get(str(value).lower(), []):
                        add_candidate(user, "department")
            elif entry_type == "position":
                for value in values:
                    for user in users_by_position.get(str(value).lower(), []):
                        add_candidate(user, "position")
            elif entry_type == "crm_contact":
                for value in values:
                    contact = crm_contacts_by_id.get(str(value))
                    if not contact:
                        continue
                    add_candidate(
                        {
                            "user_id": f"crm:{contact['id']}",
                            "nombre": contact.get("nombre") or f"Contacto {contact['id']}",
                            "puesto": contact.get("puesto") or "",
                            "empresa": contact.get("empresa") or "",
                        },
                        "crm_contact",
                        source_app="crm",
                        external_entity_type="crm_contact",
                        external_entity_id=str(contact["id"]),
                        channel="public_link",
                    )
            elif entry_type == "crm_campaign":
                for value in values:
                    if not str(value).isdigit():
                        continue
                    for contact in _load_crm_campaign_contacts(int(str(value))):
                        add_candidate(
                            {
                                "user_id": f"crm:{contact['id']}",
                                "nombre": contact.get("nombre") or f"Contacto {contact['id']}",
                                "puesto": contact.get("puesto") or "",
                                "empresa": contact.get("empresa") or "",
                            },
                            "crm_campaign",
                            source_app="crm",
                            external_entity_type="crm_campaign",
                            external_entity_id=str(value),
                            channel="public_link",
                        )

        for group in groups_created:
            for member in group["members"]:
                user = users_by_id.get(str(member["user_id"]))
                if user:
                    add_candidate(user, "manual_group", audience_group_id=group["group_id"])
                else:
                    add_candidate(member, "manual_group", audience_group_id=group["group_id"])

        persisted_assignments: List[SurveyAssignment] = []
        for candidate in materialized.values():
            assignment = SurveyAssignment(
                tenant_id=tenant_id,
                instance_id=instance_id,
                audience_group_id=candidate["audience_group_id"],
                assignee_key=candidate["assignee_key"],
                assignee_name_snapshot=candidate["assignee_name_snapshot"],
                assignee_role_snapshot=candidate["assignee_role_snapshot"],
                assignee_area_snapshot=candidate["assignee_area_snapshot"],
                assignee_position_snapshot=candidate["assignee_position_snapshot"],
                assignee_company_snapshot=candidate["assignee_company_snapshot"],
                source_app=candidate["source_app"],
                external_entity_type=candidate["external_entity_type"],
                external_entity_id=candidate["external_entity_id"],
                assignment_type=candidate["assignment_type"],
                channel=candidate["channel"],
                status="pending",
                due_at=due_at_value or instance.schedule_end_at,
            )
            db.add(assignment)
            persisted_assignments.append(assignment)

        db.flush()
        _sync_evaluations_360(db, instance, persisted_assignments, users_by_id)
        notifications_sent = 0
        if instance.status in {"published", "scheduled"}:
            notifications_sent = _send_assignment_notifications(
                db,
                instance,
                persisted_assignments,
                notification_kind="invitation",
            )
        instance.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(instance)
        return {
            "count": len(materialized),
            "notifications_sent": notifications_sent,
            "assignments": list_assignments(instance_id, tenant_id),
        }
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def _ensure_instance_available_for_response(instance: SurveyInstance, access_mode: str) -> None:
    now = datetime.utcnow()
    if instance.status in {"draft", "archived"}:
        raise ValueError("La encuesta aún no está publicada.")
    if instance.status == "scheduled" and instance.schedule_start_at and instance.schedule_start_at > now:
        raise ValueError("La encuesta aún no está disponible.")
    if instance.status == "closed":
        raise ValueError("La encuesta ya fue cerrada.")
    if access_mode == "public" and _is_360_instance(instance):
        raise ValueError("Las evaluaciones 360 requieren acceso autenticado interno.")
    if access_mode == "public" and (not instance.is_public_link_enabled or not instance.public_link_token):
        raise ValueError("El enlace público no está habilitado para esta encuesta.")


def _find_existing_response(
    db: Session,
    instance_id: int,
    tenant_id: str,
    assignment_id: Optional[int] = None,
    respondent_key: str = "",
    external_entity_type: str = "",
    external_entity_id: str = "",
) -> Optional[SurveyResponse]:
    query = (
        db.query(SurveyResponse)
        .filter(SurveyResponse.instance_id == instance_id, SurveyResponse.tenant_id == tenant_id)
        .order_by(SurveyResponse.updated_at.desc(), SurveyResponse.id.desc())
    )
    entity_type = str(external_entity_type or "").strip()
    entity_id = str(external_entity_id or "").strip()
    if entity_type and entity_id:
        query = query.filter(
            SurveyResponse.external_entity_type == entity_type,
            SurveyResponse.external_entity_id == entity_id,
        )
    if assignment_id is not None:
        response = query.filter(SurveyResponse.assignment_id == assignment_id).first()
        if response:
            return response
    if respondent_key:
        return query.filter(SurveyResponse.respondent_key == respondent_key).first()
    return None


def _find_or_create_attempt(
    db: Session,
    tenant_id: str,
    instance_id: int,
    assignment_id: Optional[int],
    response_id: int,
    attempt_number: Optional[int] = None,
) -> Optional[SurveyAttempt]:
    if not assignment_id:
        return None
    query = (
        db.query(SurveyAttempt)
        .filter(
            SurveyAttempt.tenant_id == tenant_id,
            SurveyAttempt.instance_id == instance_id,
            SurveyAttempt.assignment_id == assignment_id,
        )
        .order_by(SurveyAttempt.attempt_number.desc(), SurveyAttempt.id.desc())
    )
    attempt = query.first()
    if attempt_number is not None:
        attempt = query.filter(SurveyAttempt.attempt_number == attempt_number).first()
    if attempt:
        if attempt.response_id is None:
            attempt.response_id = response_id
        if attempt.started_at is None:
            attempt.started_at = datetime.utcnow()
        return attempt
    attempt = SurveyAttempt(
        tenant_id=tenant_id,
        instance_id=instance_id,
        assignment_id=assignment_id,
        response_id=response_id,
        attempt_number=attempt_number or 1,
        status="in_progress",
        started_at=datetime.utcnow(),
    )
    db.add(attempt)
    return attempt


def _quiz_settings(instance: SurveyInstance) -> Dict[str, Any]:
    instance_settings = instance.settings_json or {}
    template_settings = instance.template.settings_json if instance.template and instance.template.settings_json else {}
    scoring_mode = str(
        instance_settings.get("scoring_mode")
        or template_settings.get("scoring_mode")
        or (instance.template.scoring_mode if instance.template else "")
        or "none"
    ).strip().lower()
    is_quiz = scoring_mode == "quiz" or "quiz" in str(instance.external_entity_type or "").strip().lower()
    max_attempts = int(instance_settings.get("max_attempts") or template_settings.get("max_attempts") or 1)
    timer_seconds = int(instance_settings.get("timer_seconds") or template_settings.get("timer_seconds") or 0)
    attempt_strategy = str(instance_settings.get("attempt_strategy") or template_settings.get("attempt_strategy") or "best").strip().lower()
    passing_score = instance_settings.get("passing_score")
    if passing_score is None:
        passing_score = template_settings.get("passing_score")
    if passing_score is None:
        integration = _resolve_integration_context(
            source_app=instance.source_app,
            external_entity_type=instance.external_entity_type,
            external_entity_id=instance.external_entity_id,
        )
        course = integration.get("course") or {}
        if course.get("puntaje_aprobacion") is not None:
            passing_score = float(course["puntaje_aprobacion"])
    return {
        "is_quiz": is_quiz,
        "max_attempts": max(1, max_attempts),
        "timer_seconds": max(0, timer_seconds),
        "attempt_strategy": attempt_strategy if attempt_strategy in {"best", "last"} else "best",
        "passing_score": float(passing_score) if passing_score is not None else None,
    }


def _assignment_attempts(db: Session, tenant_id: str, instance_id: int, assignment_id: Optional[int]) -> List[SurveyAttempt]:
    if not assignment_id:
        return []
    return (
        db.query(SurveyAttempt)
        .filter(
            SurveyAttempt.tenant_id == tenant_id,
            SurveyAttempt.instance_id == instance_id,
            SurveyAttempt.assignment_id == assignment_id,
        )
        .order_by(SurveyAttempt.attempt_number.asc(), SurveyAttempt.id.asc())
        .all()
    )


def _best_attempt_payload(attempts: List[SurveyAttempt], strategy: str = "best") -> Optional[Dict[str, Any]]:
    submitted = [attempt for attempt in attempts if attempt.status == "submitted"]
    if not submitted:
        return None
    if strategy == "last":
        selected = submitted[-1]
    else:
        selected = max(submitted, key=lambda item: (float(item.score_value or 0), -(int(item.attempt_number or 0))))
    return {
        "attempt_number": int(selected.attempt_number or 1),
        "score_value": float(selected.score_value or 0),
        "elapsed_seconds": selected.elapsed_seconds,
        "submitted_at": _dt(selected.submitted_at),
        "status": selected.status,
        "result_json": selected.result_json or {},
    }


def _evaluation_status(total_score: Optional[float], passing_score: Optional[float]) -> Optional[str]:
    if total_score is None or passing_score is None:
        return None
    return "aprobado" if float(total_score) >= float(passing_score) else "reprobado"


def _response_attempt_context(db: Session, instance: SurveyInstance, response: SurveyResponse) -> Dict[str, Any]:
    quiz = _quiz_settings(instance)
    attempts = _assignment_attempts(db, instance.tenant_id, instance.id, response.assignment_id)
    current_attempt = next((attempt for attempt in attempts if attempt.response_id == response.id), None)
    attempts_used = len([attempt for attempt in attempts if attempt.status == "submitted"])
    remaining_attempts = max(0, quiz["max_attempts"] - attempts_used)
    if current_attempt and current_attempt.status != "submitted" and remaining_attempts > 0:
        remaining_attempts -= 1
    return {
        "is_quiz": quiz["is_quiz"],
        "current_attempt_number": int(current_attempt.attempt_number or 1) if current_attempt else 1,
        "attempts_used": attempts_used,
        "max_attempts": quiz["max_attempts"],
        "remaining_attempts": max(0, remaining_attempts),
        "attempt_strategy": quiz["attempt_strategy"],
        "timer_seconds": quiz["timer_seconds"],
        "passing_score": quiz["passing_score"],
        "best_attempt": _best_attempt_payload(attempts, quiz["attempt_strategy"]),
        "can_retry": bool(
            quiz["is_quiz"]
            and response.assignment_id
            and response.status == "submitted"
            and attempts_used < quiz["max_attempts"]
        ),
    }


def _is_360_instance(instance: SurveyInstance) -> bool:
    return _is_360_payload(instance.template.survey_type if instance.template else "", instance.external_entity_type or "")


def _response_evaluation_context(db: Session, instance: SurveyInstance, response: SurveyResponse) -> Dict[str, Any]:
    if not _is_360_instance(instance):
        return {"is_360": False, "current": None, "pending": [], "completed": 0, "total": 0}
    rows = (
        db.query(SurveyEvaluation360)
        .filter(
            SurveyEvaluation360.instance_id == instance.id,
            SurveyEvaluation360.tenant_id == instance.tenant_id,
            SurveyEvaluation360.assignment_id == response.assignment_id,
        )
        .order_by(SurveyEvaluation360.id.asc())
        .all()
    )
    current = None
    current_id = str(response.external_entity_id or "").strip()
    for row in rows:
        if current_id and str(row.id) == current_id:
            current = row
            break
    pending = [_evaluation_360_dict(row) for row in rows if row.status != "completed"]
    completed = len([row for row in rows if row.status == "completed"])
    return {
        "is_360": True,
        "current": _evaluation_360_dict(current) if current else None,
        "pending": pending,
        "completed": completed,
        "total": len(rows),
    }


def _response_summary(instance: SurveyInstance, response: SurveyResponse, access_mode: str) -> Dict[str, Any]:
    normalized_access_mode = "public" if access_mode in {"public", "public_link"} else "internal"
    sections = [_section_dict(section) for section in (instance.sections or [])]
    db = object_session(response) or object_session(instance)
    attempt_context = _response_attempt_context(db, instance, response) if db else {
        "is_quiz": False,
        "current_attempt_number": 1,
        "attempts_used": 0,
        "max_attempts": 1,
        "remaining_attempts": 0,
        "attempt_strategy": "best",
        "timer_seconds": 0,
        "passing_score": None,
        "best_attempt": None,
        "can_retry": False,
    }
    evaluation_context = _response_evaluation_context(db, instance, response) if db else {
        "is_360": False,
        "current": None,
        "pending": [],
        "completed": 0,
        "total": 0,
    }
    return {
        "instance": {
            "id": instance.id,
            "nombre": instance.nombre,
            "descripcion": instance.descripcion,
            "status": instance.status,
            "schedule_start_at": _dt(instance.schedule_start_at),
            "schedule_end_at": _dt(instance.schedule_end_at),
            "anonymity_mode": instance.anonymity_mode,
            "audience_mode": instance.audience_mode,
        },
        "response": _response_dict(response),
        "assignment": _assignment_dict(response.assignment) if response.assignment else None,
        "access_mode": normalized_access_mode,
        "draft_exists": response.status == "draft" and bool(response.answers_json),
        "quiz": attempt_context,
        "evaluation_360": evaluation_context,
        "sections": sections,
        "question_types": [{"key": key, **value} for key, value in QUESTION_TYPE_CATALOG.items()],
    }


def _is_answer_present(value: Any) -> bool:
    if isinstance(value, list):
        return any(_is_answer_present(item) for item in value)
    if isinstance(value, dict):
        return bool(value)
    if value is None:
        return False
    return bool(str(value).strip())


def _coerce_answer(question: SurveyQuestion, raw_value: Any) -> Dict[str, Any]:
    definition = get_question_type_definition(question.question_type)
    shape = definition.get("answer_shape")
    options = {str(option.value): option for option in (question.options or [])}
    if shape == "array":
        values = raw_value if isinstance(raw_value, list) else ([] if raw_value is None else [raw_value])
        normalized = [str(item).strip() for item in values if str(item).strip()]
        return {"value": normalized, "items": normalized}
    if shape == "number":
        if raw_value is None or str(raw_value).strip() == "":
            return {"value": None, "items": []}
        text = str(raw_value).strip()
        option = options.get(text)
        return {"value": text, "items": [option.value if option else text]}
    if shape == "json":
        if question.question_type in {"matrix", "likert_scale", "semantic_differential"}:
            rows = {str(option.value): option for option in (question.options or [])}
            columns = {
                str(column.get("value")): column
                for column in ((question.config_json or {}).get("columns") or [])
                if str(column.get("value") or "").strip()
            }
            payload = raw_value if isinstance(raw_value, dict) else {}
            normalized: Dict[str, str] = {}
            for row_key in rows:
                value = str(payload.get(row_key) or "").strip()
                if value and value in columns:
                    normalized[row_key] = value
            return {"value": normalized, "items": list(normalized.values())}
        if question.question_type == "file_upload":
            payload = raw_value if isinstance(raw_value, dict) else {}
            file_name = str(payload.get("name") or "").strip()
            if not file_name:
                return {"value": {}, "items": []}
            return {
                "value": {
                    "name": file_name,
                    "type": str(payload.get("type") or "").strip(),
                    "size": int(payload.get("size") or 0),
                    "data_url": str(payload.get("data_url") or "").strip(),
                },
                "items": [file_name],
            }
        if raw_value is None:
            return {"value": {}, "items": []}
        return {"value": raw_value if isinstance(raw_value, dict) else {}, "items": []}
    if shape == "string":
        if raw_value is None:
            return {"value": "", "items": []}
        text = str(raw_value).strip()
        return {"value": text, "items": [text] if text else []}
    return {"value": raw_value, "items": [raw_value] if raw_value is not None else []}


def _validate_answers_payload(instance: SurveyInstance, answers: Dict[str, Any], require_all: bool) -> List[str]:
    errors: List[str] = []
    for section in instance.sections or []:
        for question in section.questions or []:
            key = str(question.id)
            raw_value = answers.get(key)
            coerced = _coerce_answer(question, raw_value)
            validation = question.validation_json or {}
            required = bool(question.is_required or validation.get("required"))
            if require_all and required and not _is_answer_present(coerced["value"]):
                errors.append(f"La pregunta '{question.titulo}' es obligatoria.")
                continue
            if not _is_answer_present(coerced["value"]):
                continue
            if question.question_type in {"single_choice", "live_poll_single_choice", "yes_no", "true_false", "quiz_single_choice", "scale_1_5", "live_scale_1_5", "nps_0_10", "dropdown", "image_choice"}:
                option_values = {str(option.value) for option in (question.options or [])}
                if str(coerced["value"]) not in option_values:
                    errors.append(f"La respuesta de '{question.titulo}' no es válida.")
            elif question.question_type in {"multiple_choice", "ranking"}:
                option_values = {str(option.value) for option in (question.options or [])}
                for item in coerced["value"]:
                    if str(item) not in option_values:
                        errors.append(f"La respuesta de '{question.titulo}' contiene opciones inválidas.")
                        break
                if question.question_type == "ranking" and len(set(coerced["value"])) != len(coerced["value"]):
                    errors.append(f"La respuesta de '{question.titulo}' contiene valores duplicados.")
                min_choices = validation.get("min_choices")
                max_choices = validation.get("max_choices")
                if min_choices is not None and len(coerced["value"]) < int(min_choices):
                    errors.append(f"La pregunta '{question.titulo}' requiere al menos {int(min_choices)} selección(es).")
                if max_choices is not None and len(coerced["value"]) > int(max_choices):
                    errors.append(f"La pregunta '{question.titulo}' permite máximo {int(max_choices)} selección(es).")
            elif question.question_type in {"short_text", "long_text", "word_cloud"}:
                max_length = validation.get("max_length")
                if max_length is not None and len(str(coerced["value"])) > int(max_length):
                    errors.append(f"La respuesta de '{question.titulo}' excede la longitud permitida.")
            elif question.question_type in {"matrix", "likert_scale", "semantic_differential"}:
                row_values = coerced["value"] if isinstance(coerced["value"], dict) else {}
                valid_rows = {str(option.value) for option in (question.options or [])}
                valid_cols = {
                    str(column.get("value"))
                    for column in ((question.config_json or {}).get("columns") or [])
                    if str(column.get("value") or "").strip()
                }
                for row_key, col_value in row_values.items():
                    if row_key not in valid_rows or str(col_value) not in valid_cols:
                        errors.append(f"La respuesta de '{question.titulo}' contiene valores inválidos.")
                        break
                if required and require_all and len(row_values) < len(valid_rows):
                    errors.append(f"La pregunta '{question.titulo}' requiere responder todas las filas.")
            elif question.question_type == "slider":
                try:
                    slider_value = float(coerced["value"])
                except (TypeError, ValueError):
                    errors.append(f"La respuesta de '{question.titulo}' no es numérica.")
                    continue
                min_value = validation.get("min_value")
                max_value = validation.get("max_value")
                if min_value is not None and slider_value < float(min_value):
                    errors.append(f"La respuesta de '{question.titulo}' es menor al mínimo permitido.")
                if max_value is not None and slider_value > float(max_value):
                    errors.append(f"La respuesta de '{question.titulo}' excede el máximo permitido.")
            elif question.question_type == "file_upload":
                payload = coerced["value"] if isinstance(coerced["value"], dict) else {}
                max_size_mb = validation.get("max_size_mb") or (question.config_json or {}).get("max_size_mb")
                size_bytes = int(payload.get("size") or 0)
                if max_size_mb is not None and size_bytes > int(float(max_size_mb) * 1024 * 1024):
                    errors.append(f"El archivo de '{question.titulo}' excede el tamaño permitido.")
    return errors


def _upsert_response_items(db: Session, response: SurveyResponse, instance: SurveyInstance, answers: Dict[str, Any]) -> Dict[str, Any]:
    db.query(SurveyResponseItem).filter(SurveyResponseItem.response_id == response.id).delete(synchronize_session=False)
    normalized_answers: Dict[str, Any] = {}
    total_questions = 0
    answered_questions = 0
    total_score = 0.0
    score_has_value = False
    question_scores: Dict[str, Dict[str, Any]] = {}
    section_scores: Dict[str, Dict[str, Any]] = {}
    competency_scores: Dict[str, Dict[str, Any]] = {}
    nps_values: List[float] = []
    csat_values: List[float] = []
    ces_values: List[float] = []
    survey_scoring_mode = str((instance.settings_json or {}).get("scoring_mode") or "").strip().lower()

    for section in instance.sections or []:
        section_total = 0.0
        section_scored_questions = 0
        section_answered_questions = 0
        for question in section.questions or []:
            total_questions += 1
            key = str(question.id)
            raw_value = answers.get(key)
            coerced = _coerce_answer(question, raw_value)
            value = coerced["value"]
            normalized_answers[key] = value
            if not _is_answer_present(value):
                continue
            answered_questions += 1
            section_answered_questions += 1
            question_score_total = 0.0
            question_score_has_value = False
            correct_count = 0
            answer_count = 0
            if question.question_type in {"multiple_choice", "ranking"}:
                selected_values = [str(item) for item in value]
                options_map = {str(option.value): option for option in (question.options or [])}
                for index, item in enumerate(selected_values):
                    option = options_map.get(item)
                    score_value = option.score_value if option and option.score_value is not None else None
                    is_correct = option.is_correct if option else None
                    db.add(
                        SurveyResponseItem(
                            tenant_id=response.tenant_id,
                            response_id=response.id,
                            question_id=question.id,
                            option_id=option.id if option else None,
                            item_index=index,
                            answer_text=option.label if option else item,
                            answer_value=item,
                            answer_json={"value": item},
                            score_value=score_value,
                            is_correct=is_correct,
                        )
                    )
                    if score_value is not None:
                        total_score += float(score_value)
                        question_score_total += float(score_value)
                        score_has_value = True
                        question_score_has_value = True
                    if is_correct:
                        correct_count += 1
                    answer_count += 1
            elif question.question_type in {"matrix", "likert_scale", "semantic_differential"}:
                selected_map = value if isinstance(value, dict) else {}
                row_map = {str(option.value): option for option in (question.options or [])}
                column_map = {
                    str(column.get("value")): column
                    for column in ((question.config_json or {}).get("columns") or [])
                    if str(column.get("value") or "").strip()
                }
                for index, (row_key, col_value) in enumerate(selected_map.items()):
                    row_option = row_map.get(str(row_key))
                    column = column_map.get(str(col_value))
                    score_value = column.get("score_value") if column and column.get("score_value") is not None else None
                    answer_text = f"{row_option.label if row_option else row_key}: {column.get('label') if column else col_value}"
                    db.add(
                        SurveyResponseItem(
                            tenant_id=response.tenant_id,
                            response_id=response.id,
                            question_id=question.id,
                            option_id=row_option.id if row_option else None,
                            item_index=index,
                            answer_text=answer_text,
                            answer_value=str(col_value),
                            answer_json={"row": row_key, "value": str(col_value)},
                            score_value=score_value,
                            is_correct=None,
                        )
                    )
                    if score_value is not None:
                        total_score += float(score_value)
                        question_score_total += float(score_value)
                        score_has_value = True
                        question_score_has_value = True
                    answer_count += 1
            elif question.question_type == "file_upload":
                file_payload = value if isinstance(value, dict) else {}
                file_name = str(file_payload.get("name") or "").strip()
                db.add(
                    SurveyResponseItem(
                        tenant_id=response.tenant_id,
                        response_id=response.id,
                        question_id=question.id,
                        option_id=None,
                        item_index=0,
                        answer_text=file_name,
                        answer_value=file_name,
                        answer_json=file_payload,
                        score_value=None,
                        is_correct=None,
                    )
                )
                answer_count = 1
            else:
                text_value = str(value).strip() if value is not None else ""
                option = None
                if question.question_type in {"single_choice", "live_poll_single_choice", "yes_no", "true_false", "quiz_single_choice", "scale_1_5", "live_scale_1_5", "nps_0_10", "dropdown", "image_choice"}:
                    for candidate in question.options or []:
                        if str(candidate.value) == text_value:
                            option = candidate
                            break
                score_value = option.score_value if option and option.score_value is not None else None
                is_correct = option.is_correct if option else None
                answer_text = option.label if option else text_value
                answer_json = {"value": value}
                db.add(
                    SurveyResponseItem(
                        tenant_id=response.tenant_id,
                        response_id=response.id,
                        question_id=question.id,
                        option_id=option.id if option else None,
                        item_index=0,
                        answer_text=answer_text,
                        answer_value=text_value,
                        answer_json=answer_json,
                        score_value=score_value,
                        is_correct=is_correct,
                    )
                )
                if score_value is not None:
                    total_score += float(score_value)
                    question_score_total += float(score_value)
                    score_has_value = True
                    question_score_has_value = True
                if is_correct:
                    correct_count = 1
                answer_count = 1

            metric_kind = str((question.config_json or {}).get("metric_kind") or "").strip().lower()
            if question.question_type == "nps_0_10" and value is not None:
                try:
                    nps_values.append(float(value))
                except (TypeError, ValueError):
                    pass
            if question.question_type in {"scale_1_5", "live_scale_1_5", "slider"}:
                try:
                    scale_value = float(value)
                except (TypeError, ValueError):
                    scale_value = None
                if scale_value is not None:
                    if survey_scoring_mode == "ces" or metric_kind == "ces":
                        ces_values.append(scale_value)
                    if survey_scoring_mode in {"", "csat"} and metric_kind != "ces":
                        csat_values.append(scale_value)

            question_score = question_score_total if question_score_has_value else None
            if question_score is not None:
                section_total += question_score
                section_scored_questions += 1
            question_scores[key] = {
                "question_id": question.id,
                "question_type": question.question_type,
                "score": question_score,
                "max_score": question.max_score,
                "min_score": question.min_score,
                "is_correct": bool(correct_count) if question.question_type == "quiz_single_choice" else None,
                "correct_answers": correct_count if question.question_type == "quiz_single_choice" else None,
                "answer_count": answer_count,
            }
            competency_meta = section.settings_json or {}
            question_meta = question.config_json or {}
            competency_key = str(
                question_meta.get("competency_key")
                or competency_meta.get("competency_key")
                or section.id
            )
            competency_label = str(
                question_meta.get("competency_label")
                or competency_meta.get("competency_label")
                or section.titulo
            )
            bucket = competency_scores.setdefault(
                competency_key,
                {
                    "competency_key": competency_key,
                    "competency_label": competency_label,
                    "question_scores": [],
                    "answered_questions": 0,
                    "total_questions": 0,
                },
            )
            bucket["total_questions"] += 1
            if _is_answer_present(value):
                bucket["answered_questions"] += 1
            if question_score is not None:
                bucket["question_scores"].append(float(question_score))

        section_key = str(section.id)
        section_scores[section_key] = {
            "section_id": section.id,
            "titulo": section.titulo,
            "answered_questions": section_answered_questions,
            "total_questions": len(section.questions or []),
            "score_total": section_total if section_scored_questions else None,
            "score_avg": round(section_total / section_scored_questions, 2) if section_scored_questions else None,
        }

    completion_pct = round((answered_questions / total_questions) * 100, 2) if total_questions else 0.0
    quiz_questions = [
        payload for payload in question_scores.values() if payload.get("question_type") == "quiz_single_choice"
    ]
    quiz_answered = [payload for payload in quiz_questions if payload.get("is_correct") is not None]
    quiz_correct = sum(1 for payload in quiz_answered if payload.get("is_correct"))
    quiz_approval_pct = round((quiz_correct / len(quiz_answered)) * 100, 2) if quiz_answered else None
    nps_score = None
    if nps_values:
        promoters = sum(1 for value in nps_values if value >= 9)
        detractors = sum(1 for value in nps_values if value <= 6)
        nps_score = round(((promoters / len(nps_values)) * 100) - ((detractors / len(nps_values)) * 100), 2)
    csat_score = round((sum(1 for value in csat_values if value >= 4) / len(csat_values)) * 100, 2) if csat_values else None
    ces_score = round(sum(ces_values) / len(ces_values), 2) if ces_values else None
    return {
        "answers_json": normalized_answers,
        "completion_pct": completion_pct,
        "total_score": total_score if score_has_value else None,
        "answered_questions": answered_questions,
        "total_questions": total_questions,
        "question_scores": question_scores,
        "section_scores": section_scores,
        "competency_scores": {
            key: {
                "competency_key": payload["competency_key"],
                "competency_label": payload["competency_label"],
                "score_avg": round(sum(payload["question_scores"]) / len(payload["question_scores"]), 2) if payload["question_scores"] else None,
                "answered_questions": payload["answered_questions"],
                "total_questions": payload["total_questions"],
            }
            for key, payload in competency_scores.items()
        },
        "quiz_approval_pct": quiz_approval_pct,
        "nps_score": nps_score,
        "csat_score": csat_score,
        "ces_score": ces_score,
    }


def _upsert_result_metric(
    db: Session,
    tenant_id: str,
    instance_id: int,
    segment_type: str,
    segment_key: str,
    metric_key: str,
    metric_label: str,
    value_numeric: Optional[float],
    sample_size: int,
    result_json: Optional[Dict[str, Any]] = None,
) -> None:
    row = (
        db.query(SurveyResult)
        .filter(
            SurveyResult.tenant_id == tenant_id,
            SurveyResult.instance_id == instance_id,
            SurveyResult.segment_key == segment_key,
            SurveyResult.metric_key == metric_key,
        )
        .first()
    )
    if not row:
        row = SurveyResult(
            tenant_id=tenant_id,
            instance_id=instance_id,
            segment_type=segment_type,
            segment_key=segment_key,
            metric_key=metric_key,
        )
        db.add(row)
    row.segment_type = segment_type
    row.metric_label = metric_label
    row.value_numeric = value_numeric
    row.value_text = None if value_numeric is not None else ""
    row.sample_size = sample_size
    row.result_json = result_json or {}
    row.computed_at = datetime.utcnow()


def _refresh_instance_results(db: Session, instance: SurveyInstance) -> None:
    responses = [response for response in (instance.responses or []) if response.status == "submitted"]
    tenant_id = instance.tenant_id
    instance_id = instance.id
    db.query(SurveyResult).filter(
        SurveyResult.tenant_id == tenant_id,
        SurveyResult.instance_id == instance_id,
    ).delete(synchronize_session=False)
    if not responses:
        return
    quiz = _quiz_settings(instance)
    if quiz["is_quiz"]:
        responses_by_id = {response.id: response for response in responses}
        selected_responses: List[SurveyResponse] = []
        for assignment in instance.assignments or []:
            attempts = [attempt for attempt in (assignment.attempts or []) if attempt.status == "submitted" and attempt.response_id in responses_by_id]
            if not attempts:
                continue
            best_attempt = _best_attempt_payload(attempts, quiz["attempt_strategy"])
            if not best_attempt:
                continue
            selected = next(
                (attempt for attempt in attempts if int(attempt.attempt_number or 1) == int(best_attempt["attempt_number"])),
                None,
            )
            if selected and selected.response_id in responses_by_id:
                selected_responses.append(responses_by_id[selected.response_id])
        if selected_responses:
            responses = selected_responses

    total_scores = [float(response.total_score) for response in responses if response.total_score is not None]
    completion_values = [float(response.completion_pct or 0) for response in responses]
    nps_values: List[float] = []
    csat_values: List[float] = []
    ces_values: List[float] = []
    quiz_values: List[float] = []
    evaluation_statuses: List[str] = []
    section_buckets: Dict[str, Dict[str, Any]] = {}

    for response in responses:
        metrics = response.metrics_json or {}
        if metrics.get("nps_score") is not None:
            nps_values.append(float(metrics["nps_score"]))
        if metrics.get("csat_score") is not None:
            csat_values.append(float(metrics["csat_score"]))
        if metrics.get("ces_score") is not None:
            ces_values.append(float(metrics["ces_score"]))
        if metrics.get("quiz_approval_pct") is not None:
            quiz_values.append(float(metrics["quiz_approval_pct"]))
        if metrics.get("evaluation_status"):
            evaluation_statuses.append(str(metrics["evaluation_status"]))
        for section_id, payload in (metrics.get("section_scores") or {}).items():
            bucket = section_buckets.setdefault(
                str(section_id),
                {"score_values": [], "completion_values": [], "titulo": payload.get("titulo") or f"Sección {section_id}"},
            )
            if payload.get("score_avg") is not None:
                bucket["score_values"].append(float(payload["score_avg"]))
            total_questions = int(payload.get("total_questions") or 0)
            answered_questions = int(payload.get("answered_questions") or 0)
            if total_questions:
                bucket["completion_values"].append(round((answered_questions / total_questions) * 100, 2))

    _upsert_result_metric(
        db, tenant_id, instance_id, "general", "general", "responses_count", "Respuestas enviadas",
        float(len(responses)), len(responses), {"responses_count": len(responses)}
    )
    _upsert_result_metric(
        db, tenant_id, instance_id, "general", "general", "completion_pct_avg", "Promedio de finalización",
        round(sum(completion_values) / len(completion_values), 2) if completion_values else None,
        len(responses),
        {"values": completion_values},
    )
    if total_scores:
        _upsert_result_metric(
            db, tenant_id, instance_id, "general", "general", "total_score_avg", "Score promedio total",
            round(sum(total_scores) / len(total_scores), 2),
            len(total_scores),
            {"values": total_scores},
        )
    if quiz_values:
        _upsert_result_metric(
            db, tenant_id, instance_id, "general", "general", "quiz_approval_pct", "Aprobación de quiz",
            round(sum(quiz_values) / len(quiz_values), 2),
            len(quiz_values),
            {"values": quiz_values},
        )
    if evaluation_statuses:
        approved = len([item for item in evaluation_statuses if item == "aprobado"])
        failed = len([item for item in evaluation_statuses if item == "reprobado"])
        _upsert_result_metric(
            db, tenant_id, instance_id, "general", "general", "approved_count", "Aprobados",
            float(approved),
            len(evaluation_statuses),
            {"approved_count": approved},
        )
        _upsert_result_metric(
            db, tenant_id, instance_id, "general", "general", "failed_count", "Reprobados",
            float(failed),
            len(evaluation_statuses),
            {"failed_count": failed},
        )
    if nps_values:
        _upsert_result_metric(
            db, tenant_id, instance_id, "general", "general", "nps_score", "NPS",
            round(sum(nps_values) / len(nps_values), 2),
            len(nps_values),
            {"values": nps_values},
        )
    if csat_values:
        _upsert_result_metric(
            db, tenant_id, instance_id, "general", "general", "csat_score", "CSAT",
            round(sum(csat_values) / len(csat_values), 2),
            len(csat_values),
            {"values": csat_values},
        )
    if ces_values:
        _upsert_result_metric(
            db, tenant_id, instance_id, "general", "general", "ces_score", "CES",
            round(sum(ces_values) / len(ces_values), 2),
            len(ces_values),
            {"values": ces_values},
        )
    for section_id, bucket in section_buckets.items():
        if bucket["score_values"]:
            _upsert_result_metric(
                db,
                tenant_id,
                instance_id,
                "section",
                section_id,
                "section_score_avg",
                f"Score promedio · {bucket['titulo']}",
                round(sum(bucket["score_values"]) / len(bucket["score_values"]), 2),
                len(bucket["score_values"]),
                {"values": bucket["score_values"], "titulo": bucket["titulo"]},
            )
        if bucket["completion_values"]:
            _upsert_result_metric(
                db,
                tenant_id,
                instance_id,
                "section",
                section_id,
                "section_completion_pct",
                f"Finalización · {bucket['titulo']}",
                round(sum(bucket["completion_values"]) / len(bucket["completion_values"]), 2),
                len(bucket["completion_values"]),
                {"values": bucket["completion_values"], "titulo": bucket["titulo"]},
            )
    if _is_360_instance(instance):
        report_360 = _report_360(instance)
        for row in report_360.get("by_relationship") or []:
            _upsert_result_metric(
                db,
                tenant_id,
                instance_id,
                "evaluation_360_relationship",
                str(row["relationship_type"]),
                "score_avg",
                f"Promedio 360 · {row['relationship_type']}",
                row.get("score_avg"),
                int(row.get("responses") or 0),
                row,
            )
        for row in report_360.get("by_competency") or []:
            _upsert_result_metric(
                db,
                tenant_id,
                instance_id,
                "evaluation_360_competency",
                str(row["competency_key"]),
                "score_avg",
                f"Competencia 360 · {row['competency_label']}",
                row.get("score_avg"),
                int(row.get("responses") or 0),
                row,
            )


def _apply_response_anonymity(instance: SurveyInstance, response: SurveyResponse) -> None:
    mode = str(instance.anonymity_mode or "identified").strip().lower()
    if mode == "anonymous":
        response.respondent_key = None
        response.respondent_name_snapshot = "Anónimo"
        response.respondent_role_snapshot = None
        response.respondent_area_snapshot = None
        response.respondent_position_snapshot = None
        response.respondent_company_snapshot = None
        response.external_entity_id = None
    elif mode == "restricted":
        response.respondent_name_snapshot = response.respondent_name_snapshot or "Restringido"


def _active_attempt_for_response(db: Session, tenant_id: str, response: SurveyResponse) -> Optional[SurveyAttempt]:
    return (
        db.query(SurveyAttempt)
        .filter(SurveyAttempt.tenant_id == tenant_id, SurveyAttempt.response_id == response.id)
        .order_by(SurveyAttempt.attempt_number.desc(), SurveyAttempt.id.desc())
        .first()
    )


def _enforce_quiz_attempt_constraints(db: Session, response: SurveyResponse) -> Dict[str, Any]:
    instance = response.instance
    quiz = _quiz_settings(instance)
    if not quiz["is_quiz"] or not response.assignment_id:
        return quiz
    attempt = _active_attempt_for_response(db, response.tenant_id, response)
    if not attempt:
        return quiz
    if attempt.status == "submitted":
        raise ValueError("El intento actual ya fue enviado.")
    if quiz["timer_seconds"] and attempt.started_at:
        elapsed = max(0, int((datetime.utcnow() - attempt.started_at).total_seconds()))
        if elapsed > quiz["timer_seconds"]:
            raise ValueError("El tiempo del intento ya expiró.")
    return quiz


def start_internal_response(instance_id: int, tenant_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    try:
        _refresh_instance_lifecycle(db, instance_id=instance_id, tenant_id=tenant_id)
        instance = (
            db.query(SurveyInstance)
            .filter(SurveyInstance.id == instance_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not instance:
            raise ValueError("Encuesta no encontrada.")
        _ensure_instance_available_for_response(instance, "internal")
        user_id = str(user.get("user_id") or user.get("user_key") or "").strip()
        assignment = None
        if user_id:
            assignment = (
                db.query(SurveyAssignment)
                .filter(
                    SurveyAssignment.instance_id == instance_id,
                    SurveyAssignment.tenant_id == tenant_id,
                    SurveyAssignment.assignee_key == user_id,
                )
                .first()
            )
        if not assignment and instance.audience_mode != "public_link":
            raise ValueError("No tienes una asignación activa para esta encuesta.")
        now = datetime.utcnow()
        quiz = _quiz_settings(instance)
        evaluation_row = None
        if assignment and _is_360_instance(instance):
            evaluation_rows = (
                db.query(SurveyEvaluation360)
                .filter(
                    SurveyEvaluation360.instance_id == instance.id,
                    SurveyEvaluation360.tenant_id == tenant_id,
                    SurveyEvaluation360.assignment_id == assignment.id,
                )
                .order_by(SurveyEvaluation360.status.asc(), SurveyEvaluation360.id.asc())
                .all()
            )
            for row in evaluation_rows:
                response_for_row = _find_existing_response(
                    db,
                    instance_id=instance_id,
                    tenant_id=tenant_id,
                    assignment_id=assignment.id,
                    respondent_key=user_id,
                    external_entity_type="evaluation_360",
                    external_entity_id=str(row.id),
                )
                if response_for_row and response_for_row.status != "submitted":
                    evaluation_row = row
                    break
            if evaluation_row is None:
                evaluation_row = next((row for row in evaluation_rows if row.status != "completed"), None)
            if evaluation_row is None and evaluation_rows:
                evaluation_row = evaluation_rows[0]
        response = None
        if assignment:
            attempts = _assignment_attempts(db, tenant_id, instance.id, assignment.id)
            current_attempt = attempts[-1] if attempts else None
            if current_attempt and current_attempt.status != "submitted" and current_attempt.response_id and not evaluation_row:
                response = (
                    db.query(SurveyResponse)
                    .filter(SurveyResponse.id == current_attempt.response_id, SurveyResponse.tenant_id == tenant_id)
                    .first()
                )
            elif quiz["is_quiz"] and current_attempt and current_attempt.status == "submitted":
                submitted_attempts = len([attempt for attempt in attempts if attempt.status == "submitted"])
                if submitted_attempts < quiz["max_attempts"]:
                    response = SurveyResponse(
                        tenant_id=tenant_id,
                        instance_id=instance.id,
                        assignment_id=assignment.id,
                        respondent_key=user_id or None,
                        respondent_name_snapshot=user.get("nombre"),
                        respondent_role_snapshot=user.get("role"),
                        respondent_area_snapshot=user.get("departamento"),
                        respondent_position_snapshot=user.get("puesto"),
                        respondent_company_snapshot=user.get("empresa"),
                        source_app="encuestas",
                        external_entity_type="internal_user",
                        external_entity_id=user_id or None,
                        status="draft",
                        submission_channel="internal",
                        started_at=now,
                        last_saved_at=now,
                        answers_json={},
                        metrics_json={},
                    )
                    db.add(response)
                    db.flush()
                    _find_or_create_attempt(
                        db,
                        tenant_id,
                        instance.id,
                        assignment.id,
                        response.id,
                        attempt_number=submitted_attempts + 1,
                    )
                elif current_attempt.response_id:
                    response = (
                        db.query(SurveyResponse)
                        .filter(SurveyResponse.id == current_attempt.response_id, SurveyResponse.tenant_id == tenant_id)
                        .first()
                    )
            if response is None:
                response = _find_existing_response(
                    db,
                    instance_id=instance_id,
                    tenant_id=tenant_id,
                    assignment_id=assignment.id if assignment else None,
                    respondent_key=user_id,
                    external_entity_type="evaluation_360" if evaluation_row else "",
                    external_entity_id=str(evaluation_row.id) if evaluation_row else "",
                )
        else:
            response = _find_existing_response(
                db,
                instance_id=instance_id,
                tenant_id=tenant_id,
                assignment_id=None,
                respondent_key=user_id,
            )
        if not response:
            response = SurveyResponse(
                tenant_id=tenant_id,
                instance_id=instance.id,
                assignment_id=assignment.id if assignment else None,
                respondent_key=user_id or None,
                respondent_name_snapshot=user.get("nombre"),
                respondent_role_snapshot=user.get("role"),
                respondent_area_snapshot=user.get("departamento"),
                respondent_position_snapshot=user.get("puesto"),
                respondent_company_snapshot=user.get("empresa"),
                source_app="encuestas",
                external_entity_type="evaluation_360" if evaluation_row else "internal_user",
                external_entity_id=str(evaluation_row.id) if evaluation_row else (user_id or None),
                status="draft",
                submission_channel="internal",
                started_at=now,
                last_saved_at=now,
                answers_json={},
                metrics_json={},
            )
            db.add(response)
            db.flush()
        if evaluation_row:
            response.external_entity_type = "evaluation_360"
            response.external_entity_id = str(evaluation_row.id)
            response.metrics_json = {
                **(response.metrics_json or {}),
                "evaluation_360": {
                    "evaluation_id": evaluation_row.id,
                    "evaluatee_key": evaluation_row.evaluatee_key,
                    "evaluatee_name_snapshot": evaluation_row.evaluatee_name_snapshot,
                    "relationship_type": evaluation_row.relationship_type,
                },
            }
        if assignment:
            assignment.status = "in_progress" if response.status == "draft" else assignment.status
            assignment.updated_at = now
        if assignment:
            existing_attempt = (
                db.query(SurveyAttempt)
                .filter(SurveyAttempt.tenant_id == tenant_id, SurveyAttempt.response_id == response.id)
                .first()
            )
            if not existing_attempt:
                _find_or_create_attempt(db, tenant_id, instance.id, assignment.id if assignment else None, response.id)
        db.commit()
        db.refresh(response)
        return _response_summary(instance, response, "internal")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def start_public_response(public_token: str, tenant_id: str, response_key: str = "") -> Dict[str, Any]:
    db = get_db()
    try:
        token = str(public_token or "").strip()
        _refresh_instance_lifecycle(db, tenant_id=tenant_id)
        instance = (
            db.query(SurveyInstance)
            .filter(
                SurveyInstance.tenant_id == tenant_id,
                SurveyInstance.public_link_token == token,
            )
            .first()
        )
        if not instance:
            raise ValueError("Encuesta no encontrada.")
        _ensure_instance_available_for_response(instance, "public")
        respondent_key = str(response_key or "").strip()
        if not respondent_key:
            respondent_key = f"public:{instance.id}:{uuid4().hex}"
        response = _find_existing_response(
            db,
            instance_id=instance.id,
            tenant_id=tenant_id,
            respondent_key=respondent_key,
        )
        now = datetime.utcnow()
        if not response:
            response = SurveyResponse(
                tenant_id=tenant_id,
                instance_id=instance.id,
                assignment_id=None,
                respondent_key=respondent_key,
                respondent_name_snapshot="Participante externo",
                source_app="encuestas",
                external_entity_type="public_link",
                external_entity_id=token,
                status="draft",
                submission_channel="public_link",
                started_at=now,
                last_saved_at=now,
                answers_json={},
                metrics_json={},
            )
            db.add(response)
            db.flush()
        db.commit()
        db.refresh(response)
        payload = _response_summary(instance, response, "public")
        payload["response_key"] = respondent_key
        return payload
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_response_session(response_id: int, tenant_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        response = (
            db.query(SurveyResponse)
            .join(SurveyInstance, SurveyResponse.instance_id == SurveyInstance.id)
            .filter(SurveyResponse.id == response_id, SurveyResponse.tenant_id == tenant_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not response:
            return None
        return _response_summary(response.instance, response, response.submission_channel or "internal")
    finally:
        db.close()


def save_response_draft(response_id: int, tenant_id: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    try:
        response = (
            db.query(SurveyResponse)
            .join(SurveyInstance, SurveyResponse.instance_id == SurveyInstance.id)
            .filter(SurveyResponse.id == response_id, SurveyResponse.tenant_id == tenant_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not response:
            raise ValueError("Respuesta no encontrada.")
        if response.status == "submitted":
            raise ValueError("La respuesta ya fue enviada.")
        instance = response.instance
        _ensure_instance_available_for_response(instance, "public" if response.submission_channel == "public_link" else "internal")
        quiz = _enforce_quiz_attempt_constraints(db, response)
        merged_answers = dict(response.answers_json or {})
        for key, value in (answers or {}).items():
            merged_answers[str(key)] = value
        errors = _validate_answers_payload(instance, merged_answers, require_all=False)
        if errors:
            raise ValueError(errors[0])
        stats = _upsert_response_items(db, response, instance, merged_answers)
        now = datetime.utcnow()
        attempt = _active_attempt_for_response(db, tenant_id, response)
        response.answers_json = stats["answers_json"]
        response.completion_pct = stats["completion_pct"]
        response.total_score = stats["total_score"]
        response.metrics_json = {
            **({"evaluation_360": (response.metrics_json or {}).get("evaluation_360")} if (response.metrics_json or {}).get("evaluation_360") else {}),
            "answered_questions": stats["answered_questions"],
            "total_questions": stats["total_questions"],
            "question_scores": stats["question_scores"],
            "section_scores": stats["section_scores"],
            "competency_scores": stats["competency_scores"],
            "quiz_approval_pct": stats["quiz_approval_pct"],
            "nps_score": stats["nps_score"],
            "csat_score": stats["csat_score"],
            "ces_score": stats["ces_score"],
            "attempt_number": int(attempt.attempt_number or 1) if attempt else 1,
            "attempt_strategy": quiz["attempt_strategy"],
            "max_attempts": quiz["max_attempts"],
            "timer_seconds": quiz["timer_seconds"],
            "passing_score": quiz["passing_score"],
            "evaluation_status": _evaluation_status(stats["total_score"], quiz["passing_score"]),
        }
        response.last_saved_at = now
        response.updated_at = now
        if response.assignment:
            response.assignment.status = "in_progress"
            response.assignment.updated_at = now
        db.commit()
        db.refresh(response)
        return _response_summary(instance, response, response.submission_channel or "internal")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def submit_response(response_id: int, tenant_id: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    try:
        response = (
            db.query(SurveyResponse)
            .join(SurveyInstance, SurveyResponse.instance_id == SurveyInstance.id)
            .filter(SurveyResponse.id == response_id, SurveyResponse.tenant_id == tenant_id, SurveyInstance.tenant_id == tenant_id)
            .first()
        )
        if not response:
            raise ValueError("Respuesta no encontrada.")
        if response.status == "submitted":
            return _response_summary(response.instance, response, response.submission_channel or "internal")
        instance = response.instance
        _ensure_instance_available_for_response(instance, "public" if response.submission_channel == "public_link" else "internal")
        quiz = _enforce_quiz_attempt_constraints(db, response)
        merged_answers = dict(response.answers_json or {})
        for key, value in (answers or {}).items():
            merged_answers[str(key)] = value
        errors = _validate_answers_payload(instance, merged_answers, require_all=True)
        if errors:
            raise ValueError(errors[0])
        stats = _upsert_response_items(db, response, instance, merged_answers)
        now = datetime.utcnow()
        attempt = _active_attempt_for_response(db, tenant_id, response)
        evaluation_status = _evaluation_status(stats["total_score"], quiz["passing_score"])
        response.answers_json = stats["answers_json"]
        response.completion_pct = 100.0 if stats["total_questions"] else 0.0
        response.total_score = stats["total_score"]
        response.metrics_json = {
            **({"evaluation_360": (response.metrics_json or {}).get("evaluation_360")} if (response.metrics_json or {}).get("evaluation_360") else {}),
            "answered_questions": stats["answered_questions"],
            "total_questions": stats["total_questions"],
            "submitted": True,
            "question_scores": stats["question_scores"],
            "section_scores": stats["section_scores"],
            "competency_scores": stats["competency_scores"],
            "quiz_approval_pct": stats["quiz_approval_pct"],
            "nps_score": stats["nps_score"],
            "csat_score": stats["csat_score"],
            "ces_score": stats["ces_score"],
            "attempt_number": int(attempt.attempt_number or 1) if attempt else 1,
            "attempt_strategy": quiz["attempt_strategy"],
            "max_attempts": quiz["max_attempts"],
            "timer_seconds": quiz["timer_seconds"],
            "passing_score": quiz["passing_score"],
            "evaluation_status": evaluation_status,
        }
        response.status = "submitted"
        response.last_saved_at = now
        response.submitted_at = now
        response.updated_at = now
        _apply_response_anonymity(instance, response)
        evaluation_row = None
        if str(response.external_entity_type or "") == "evaluation_360" and str(response.external_entity_id or "").isdigit():
            evaluation_row = (
                db.query(SurveyEvaluation360)
                .filter(
                    SurveyEvaluation360.id == int(str(response.external_entity_id)),
                    SurveyEvaluation360.tenant_id == tenant_id,
                )
                .first()
            )
            if evaluation_row:
                evaluation_row.status = "completed"
                evaluation_row.updated_at = now
        if response.assignment:
            response.assignment.response_count = (
                db.query(SurveyResponse)
                .filter(
                    SurveyResponse.assignment_id == response.assignment.id,
                    SurveyResponse.tenant_id == tenant_id,
                    SurveyResponse.status == "submitted",
                )
                .count()
            )
            if evaluation_row:
                pending_links = (
                    db.query(SurveyEvaluation360)
                    .filter(
                        SurveyEvaluation360.assignment_id == response.assignment.id,
                        SurveyEvaluation360.tenant_id == tenant_id,
                        SurveyEvaluation360.status != "completed",
                    )
                    .count()
                )
                response.assignment.status = "completed" if pending_links == 0 else "in_progress"
            else:
                response.assignment.status = "completed"
            response.assignment.updated_at = now
            if attempt:
                attempt.response_id = response.id
                attempt.status = "submitted"
                attempt.submitted_at = now
                if attempt.started_at:
                    attempt.elapsed_seconds = max(0, int((now - attempt.started_at).total_seconds()))
                attempt.score_value = response.total_score
                attempt.result_json = {
                    "question_scores": stats["question_scores"],
                    "section_scores": stats["section_scores"],
                    "quiz_approval_pct": stats["quiz_approval_pct"],
                    "nps_score": stats["nps_score"],
                    "csat_score": stats["csat_score"],
                    "ces_score": stats["ces_score"],
                    "evaluation_status": evaluation_status,
                    "passing_score": quiz["passing_score"],
                }
                attempt.updated_at = now
        _refresh_instance_results(db, instance)
        db.commit()
        db.refresh(response)
        summary = _response_summary(instance, response, response.submission_channel or "internal")
        queue_backendhook_event(
            tenant_id=tenant_id,
            instance_id=instance.id,
            event_name="response_submitted",
            payload={
                "response": summary,
                "metrics": response.metrics_json or {},
            },
            assignment_id=response.assignment.id if response.assignment else None,
        )
        return summary
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
