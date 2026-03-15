from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from fastapi_modulo.db import MAIN


class SurveyTemplate(MAIN):
    __tablename__ = "survey_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_survey_templates_tenant_slug"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    nombre = Column(String(200), nullable=False)
    slug = Column(String(160), nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    categoria = Column(String(80), nullable=True, index=True)
    survey_type = Column(String(50), nullable=False, default="general", index=True)
    status = Column(String(30), nullable=False, default="draft", index=True)
    version = Column(Integer, nullable=False, default=1)
    source_app = Column(String(80), nullable=True, index=True)
    external_entity_type = Column(String(80), nullable=True, index=True)
    external_entity_id = Column(String(120), nullable=True, index=True)
    scoring_mode = Column(String(40), nullable=False, default="none")
    settings_json = Column(JSON, nullable=True)
    validation_rules_json = Column(JSON, nullable=True)
    created_by = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

    sections = relationship(
        "SurveySection",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="SurveySection.orden",
    )
    instances = relationship("SurveyInstance", back_populates="template")


class SurveyInstance(MAIN):
    __tablename__ = "survey_instances"
    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo", name="uq_survey_instances_tenant_codigo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    template_id = Column(Integer, ForeignKey("survey_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    codigo = Column(String(80), nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="draft", index=True)
    publication_mode = Column(String(30), nullable=False, default="manual")
    audience_mode = Column(String(30), nullable=False, default="internal")
    anonymity_mode = Column(String(30), nullable=False, default="identified", index=True)
    schedule_start_at = Column(DateTime, nullable=True, index=True)
    schedule_end_at = Column(DateTime, nullable=True, index=True)
    is_public_link_enabled = Column(Boolean, nullable=False, default=False)
    public_link_token = Column(String(120), nullable=True, index=True)
    source_app = Column(String(80), nullable=True, index=True)
    external_entity_type = Column(String(80), nullable=True, index=True)
    external_entity_id = Column(String(120), nullable=True, index=True)
    settings_json = Column(JSON, nullable=True)
    publication_rules_json = Column(JSON, nullable=True)
    created_by = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    template = relationship("SurveyTemplate", back_populates="instances")
    assignments = relationship("SurveyAssignment", back_populates="instance", cascade="all, delete-orphan")
    responses = relationship("SurveyResponse", back_populates="instance", cascade="all, delete-orphan")
    results = relationship("SurveyResult", back_populates="instance", cascade="all, delete-orphan")
    sections = relationship("SurveySection", back_populates="instance")


class SurveySection(MAIN):
    __tablename__ = "survey_sections"
    __table_args__ = (
        UniqueConstraint("template_id", "orden", name="uq_survey_sections_template_order"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    template_id = Column(Integer, ForeignKey("survey_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    instance_id = Column(Integer, ForeignKey("survey_instances.id", ondelete="SET NULL"), nullable=True, index=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    orden = Column(Integer, nullable=False, default=0)
    is_required = Column(Boolean, nullable=False, default=False)
    settings_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    template = relationship("SurveyTemplate", back_populates="sections")
    instance = relationship("SurveyInstance", back_populates="sections")
    questions = relationship(
        "SurveyQuestion",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="SurveyQuestion.orden",
    )


class SurveyQuestion(MAIN):
    __tablename__ = "survey_questions"
    __table_args__ = (
        UniqueConstraint("section_id", "orden", name="uq_survey_questions_section_order"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    template_id = Column(Integer, ForeignKey("survey_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("survey_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    question_key = Column(String(120), nullable=True, index=True)
    titulo = Column(Text, nullable=False)
    descripcion = Column(Text, nullable=True)
    question_type = Column(String(50), nullable=False, index=True)
    orden = Column(Integer, nullable=False, default=0)
    is_required = Column(Boolean, nullable=False, default=False)
    is_scored = Column(Boolean, nullable=False, default=False)
    max_score = Column(Float, nullable=True)
    min_score = Column(Float, nullable=True)
    config_json = Column(JSON, nullable=True)
    validation_json = Column(JSON, nullable=True)
    logic_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    section = relationship("SurveySection", back_populates="questions")
    options = relationship(
        "SurveyOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="SurveyOption.orden",
    )
    response_items = relationship("SurveyResponseItem", back_populates="question")


class SurveyOption(MAIN):
    __tablename__ = "survey_options"
    __table_args__ = (
        UniqueConstraint("question_id", "orden", name="uq_survey_options_question_order"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    question_id = Column(Integer, ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(300), nullable=False)
    value = Column(String(160), nullable=True)
    orden = Column(Integer, nullable=False, default=0)
    score_value = Column(Float, nullable=True)
    is_correct = Column(Boolean, nullable=False, default=False)
    config_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    question = relationship("SurveyQuestion", back_populates="options")
    response_items = relationship("SurveyResponseItem", back_populates="option")


class SurveyAudienceGroup(MAIN):
    __tablename__ = "survey_audience_groups"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_survey_audience_groups_tenant_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    nombre = Column(String(180), nullable=False)
    descripcion = Column(Text, nullable=True)
    source_app = Column(String(80), nullable=True, index=True)
    external_entity_type = Column(String(80), nullable=True, index=True)
    external_entity_id = Column(String(120), nullable=True, index=True)
    filters_json = Column(JSON, nullable=True)
    is_dynamic = Column(Boolean, nullable=False, default=False)
    created_by = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = relationship(
        "SurveyAudienceGroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    assignments = relationship("SurveyAssignment", back_populates="audience_group")


class SurveyAudienceGroupMember(MAIN):
    __tablename__ = "survey_audience_group_members"
    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "member_key",
            name="uq_survey_audience_group_members_group_member",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    group_id = Column(Integer, ForeignKey("survey_audience_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    member_key = Column(String(120), nullable=False, index=True)
    member_name_snapshot = Column(String(200), nullable=True)
    member_role_snapshot = Column(String(150), nullable=True)
    member_area_snapshot = Column(String(150), nullable=True)
    member_position_snapshot = Column(String(150), nullable=True)
    member_company_snapshot = Column(String(150), nullable=True)
    source_app = Column(String(80), nullable=True, index=True)
    external_entity_type = Column(String(80), nullable=True, index=True)
    external_entity_id = Column(String(120), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    group = relationship("SurveyAudienceGroup", back_populates="members")


class SurveyAssignment(MAIN):
    __tablename__ = "survey_assignments"
    __table_args__ = (
        UniqueConstraint(
            "instance_id",
            "assignee_key",
            "channel",
            name="uq_survey_assignments_instance_assignee_channel",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    instance_id = Column(Integer, ForeignKey("survey_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    audience_group_id = Column(Integer, ForeignKey("survey_audience_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    assignee_key = Column(String(120), nullable=False, index=True)
    assignee_name_snapshot = Column(String(200), nullable=True)
    assignee_role_snapshot = Column(String(150), nullable=True)
    assignee_area_snapshot = Column(String(150), nullable=True)
    assignee_position_snapshot = Column(String(150), nullable=True)
    assignee_company_snapshot = Column(String(150), nullable=True)
    source_app = Column(String(80), nullable=True, index=True)
    external_entity_type = Column(String(80), nullable=True, index=True)
    external_entity_id = Column(String(120), nullable=True, index=True)
    assignment_type = Column(String(40), nullable=False, default="user", index=True)
    channel = Column(String(40), nullable=False, default="internal")
    status = Column(String(30), nullable=False, default="pending", index=True)
    due_at = Column(DateTime, nullable=True, index=True)
    first_sent_at = Column(DateTime, nullable=True)
    last_sent_at = Column(DateTime, nullable=True)
    response_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    instance = relationship("SurveyInstance", back_populates="assignments")
    audience_group = relationship("SurveyAudienceGroup", back_populates="assignments")
    responses = relationship("SurveyResponse", back_populates="assignment")
    attempts = relationship("SurveyAttempt", back_populates="assignment")
    evaluations_360 = relationship("SurveyEvaluation360", back_populates="assignment")


class SurveyResponse(MAIN):
    __tablename__ = "survey_responses"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    instance_id = Column(Integer, ForeignKey("survey_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_id = Column(Integer, ForeignKey("survey_assignments.id", ondelete="SET NULL"), nullable=True, index=True)
    respondent_key = Column(String(120), nullable=True, index=True)
    respondent_name_snapshot = Column(String(200), nullable=True)
    respondent_role_snapshot = Column(String(150), nullable=True)
    respondent_area_snapshot = Column(String(150), nullable=True)
    respondent_position_snapshot = Column(String(150), nullable=True)
    respondent_company_snapshot = Column(String(150), nullable=True)
    source_app = Column(String(80), nullable=True, index=True)
    external_entity_type = Column(String(80), nullable=True, index=True)
    external_entity_id = Column(String(120), nullable=True, index=True)
    status = Column(String(30), nullable=False, default="draft", index=True)
    submission_channel = Column(String(40), nullable=False, default="internal")
    started_at = Column(DateTime, nullable=True, index=True)
    submitted_at = Column(DateTime, nullable=True, index=True)
    last_saved_at = Column(DateTime, nullable=True)
    completion_pct = Column(Float, nullable=False, default=0)
    total_score = Column(Float, nullable=True)
    metrics_json = Column(JSON, nullable=True)
    answers_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    instance = relationship("SurveyInstance", back_populates="responses")
    assignment = relationship("SurveyAssignment", back_populates="responses")
    items = relationship(
        "SurveyResponseItem",
        back_populates="response",
        cascade="all, delete-orphan",
    )
    attempts = relationship("SurveyAttempt", back_populates="response")


class SurveyResponseItem(MAIN):
    __tablename__ = "survey_response_items"
    __table_args__ = (
        UniqueConstraint(
            "response_id",
            "question_id",
            "item_index",
            name="uq_survey_response_items_response_question_index",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    response_id = Column(Integer, ForeignKey("survey_responses.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_id = Column(Integer, ForeignKey("survey_options.id", ondelete="SET NULL"), nullable=True, index=True)
    item_index = Column(Integer, nullable=False, default=0)
    answer_text = Column(Text, nullable=True)
    answer_value = Column(String(160), nullable=True)
    answer_json = Column(JSON, nullable=True)
    score_value = Column(Float, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    response = relationship("SurveyResponse", back_populates="items")
    question = relationship("SurveyQuestion", back_populates="response_items")
    option = relationship("SurveyOption", back_populates="response_items")


class SurveyResult(MAIN):
    __tablename__ = "survey_results"
    __table_args__ = (
        UniqueConstraint(
            "instance_id",
            "segment_key",
            "metric_key",
            name="uq_survey_results_instance_segment_metric",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    instance_id = Column(Integer, ForeignKey("survey_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_type = Column(String(60), nullable=False, default="general", index=True)
    segment_key = Column(String(120), nullable=False, default="general", index=True)
    metric_key = Column(String(80), nullable=False, index=True)
    metric_label = Column(String(180), nullable=True)
    value_numeric = Column(Float, nullable=True)
    value_text = Column(String(200), nullable=True)
    sample_size = Column(Integer, nullable=True)
    result_json = Column(JSON, nullable=True)
    computed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    instance = relationship("SurveyInstance", back_populates="results")


class SurveyAttempt(MAIN):
    __tablename__ = "survey_attempts"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "attempt_number",
            name="uq_survey_attempts_assignment_number",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    instance_id = Column(Integer, ForeignKey("survey_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_id = Column(Integer, ForeignKey("survey_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    response_id = Column(Integer, ForeignKey("survey_responses.id", ondelete="SET NULL"), nullable=True, index=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    status = Column(String(30), nullable=False, default="in_progress", index=True)
    started_at = Column(DateTime, nullable=True, index=True)
    submitted_at = Column(DateTime, nullable=True, index=True)
    elapsed_seconds = Column(Integer, nullable=True)
    score_value = Column(Float, nullable=True)
    result_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignment = relationship("SurveyAssignment", back_populates="attempts")
    response = relationship("SurveyResponse", back_populates="attempts")


class SurveyEvaluation360(MAIN):
    __tablename__ = "survey_evaluations_360"
    __table_args__ = (
        UniqueConstraint(
            "instance_id",
            "evaluatee_key",
            "evaluator_key",
            "relationship_type",
            name="uq_survey_evaluations_360_unique_link",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    instance_id = Column(Integer, ForeignKey("survey_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_id = Column(Integer, ForeignKey("survey_assignments.id", ondelete="SET NULL"), nullable=True, index=True)
    evaluatee_key = Column(String(120), nullable=False, index=True)
    evaluator_key = Column(String(120), nullable=False, index=True)
    relationship_type = Column(String(40), nullable=False, index=True)
    evaluatee_name_snapshot = Column(String(200), nullable=True)
    evaluatee_role_snapshot = Column(String(150), nullable=True)
    evaluatee_area_snapshot = Column(String(150), nullable=True)
    evaluatee_position_snapshot = Column(String(150), nullable=True)
    evaluatee_company_snapshot = Column(String(150), nullable=True)
    evaluator_name_snapshot = Column(String(200), nullable=True)
    evaluator_role_snapshot = Column(String(150), nullable=True)
    evaluator_area_snapshot = Column(String(150), nullable=True)
    evaluator_position_snapshot = Column(String(150), nullable=True)
    evaluator_company_snapshot = Column(String(150), nullable=True)
    status = Column(String(30), nullable=False, default="pending", index=True)
    source_app = Column(String(80), nullable=True, index=True)
    external_entity_type = Column(String(80), nullable=True, index=True)
    external_entity_id = Column(String(120), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignment = relationship("SurveyAssignment", back_populates="evaluations_360")


class SurveyDispatchLog(MAIN):
    __tablename__ = "survey_dispatch_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)
    instance_id = Column(Integer, ForeignKey("survey_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_id = Column(Integer, ForeignKey("survey_assignments.id", ondelete="SET NULL"), nullable=True, index=True)
    dispatch_type = Column(String(40), nullable=False, default="invitation", index=True)
    dispatch_status = Column(String(30), nullable=False, default="sent", index=True)
    channel = Column(String(40), nullable=False, default="internal", index=True)
    recipient_key = Column(String(120), nullable=True, index=True)
    recipient_name_snapshot = Column(String(200), nullable=True)
    message_text = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    dispatched_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
