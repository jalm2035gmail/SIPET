"""Alembic migration: Módulo de encuestas — tablas MAIN.

Revision ID: 20260312_add_encuestas_tables
Revises: 20260309_add_presentaciones_tables
Create Date: 2026-03-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260312_add_encuestas_tables"
down_revision = "20260309_add_presentaciones_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "survey_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("categoria", sa.String(length=80), nullable=True),
        sa.Column("survey_type", sa.String(length=50), nullable=False, server_default="general"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_app", sa.String(length=80), nullable=True),
        sa.Column("external_entity_type", sa.String(length=80), nullable=True),
        sa.Column("external_entity_id", sa.String(length=120), nullable=True),
        sa.Column("scoring_mode", sa.String(length=40), nullable=False, server_default="none"),
        sa.Column("settings_json", sa.JSON(), nullable=True),
        sa.Column("validation_rules_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(length=150), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_survey_templates_tenant_slug"),
    )
    op.create_index("ix_survey_templates_tenant_id", "survey_templates", ["tenant_id"])
    op.create_index("ix_survey_templates_slug", "survey_templates", ["slug"])
    op.create_index("ix_survey_templates_categoria", "survey_templates", ["categoria"])
    op.create_index("ix_survey_templates_survey_type", "survey_templates", ["survey_type"])
    op.create_index("ix_survey_templates_status", "survey_templates", ["status"])
    op.create_index("ix_survey_templates_source_app", "survey_templates", ["source_app"])
    op.create_index("ix_survey_templates_external_entity_type", "survey_templates", ["external_entity_type"])
    op.create_index("ix_survey_templates_external_entity_id", "survey_templates", ["external_entity_id"])

    op.create_table(
        "survey_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("survey_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("codigo", sa.String(length=80), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("publication_mode", sa.String(length=30), nullable=False, server_default="manual"),
        sa.Column("audience_mode", sa.String(length=30), nullable=False, server_default="internal"),
        sa.Column("anonymity_mode", sa.String(length=30), nullable=False, server_default="identified"),
        sa.Column("schedule_start_at", sa.DateTime(), nullable=True),
        sa.Column("schedule_end_at", sa.DateTime(), nullable=True),
        sa.Column("is_public_link_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("public_link_token", sa.String(length=120), nullable=True),
        sa.Column("source_app", sa.String(length=80), nullable=True),
        sa.Column("external_entity_type", sa.String(length=80), nullable=True),
        sa.Column("external_entity_id", sa.String(length=120), nullable=True),
        sa.Column("settings_json", sa.JSON(), nullable=True),
        sa.Column("publication_rules_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(length=150), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", "codigo", name="uq_survey_instances_tenant_codigo"),
    )
    op.create_index("ix_survey_instances_tenant_id", "survey_instances", ["tenant_id"])
    op.create_index("ix_survey_instances_template_id", "survey_instances", ["template_id"])
    op.create_index("ix_survey_instances_codigo", "survey_instances", ["codigo"])
    op.create_index("ix_survey_instances_status", "survey_instances", ["status"])
    op.create_index("ix_survey_instances_anonymity_mode", "survey_instances", ["anonymity_mode"])
    op.create_index("ix_survey_instances_schedule_start_at", "survey_instances", ["schedule_start_at"])
    op.create_index("ix_survey_instances_schedule_end_at", "survey_instances", ["schedule_end_at"])
    op.create_index("ix_survey_instances_public_link_token", "survey_instances", ["public_link_token"])
    op.create_index("ix_survey_instances_source_app", "survey_instances", ["source_app"])
    op.create_index("ix_survey_instances_external_entity_type", "survey_instances", ["external_entity_type"])
    op.create_index("ix_survey_instances_external_entity_id", "survey_instances", ["external_entity_id"])

    op.create_table(
        "survey_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("survey_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("survey_instances.id", ondelete="SET NULL"), nullable=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("settings_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("template_id", "orden", name="uq_survey_sections_template_order"),
    )
    op.create_index("ix_survey_sections_tenant_id", "survey_sections", ["tenant_id"])
    op.create_index("ix_survey_sections_template_id", "survey_sections", ["template_id"])
    op.create_index("ix_survey_sections_instance_id", "survey_sections", ["instance_id"])

    op.create_table(
        "survey_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("survey_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("survey_sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_key", sa.String(length=120), nullable=True),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("question_type", sa.String(length=50), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_scored", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("max_score", sa.Float(), nullable=True),
        sa.Column("min_score", sa.Float(), nullable=True),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("validation_json", sa.JSON(), nullable=True),
        sa.Column("logic_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("section_id", "orden", name="uq_survey_questions_section_order"),
    )
    op.create_index("ix_survey_questions_tenant_id", "survey_questions", ["tenant_id"])
    op.create_index("ix_survey_questions_template_id", "survey_questions", ["template_id"])
    op.create_index("ix_survey_questions_section_id", "survey_questions", ["section_id"])
    op.create_index("ix_survey_questions_question_key", "survey_questions", ["question_key"])
    op.create_index("ix_survey_questions_question_type", "survey_questions", ["question_type"])

    op.create_table(
        "survey_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(length=300), nullable=False),
        sa.Column("value", sa.String(length=160), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_value", sa.Float(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("question_id", "orden", name="uq_survey_options_question_order"),
    )
    op.create_index("ix_survey_options_tenant_id", "survey_options", ["tenant_id"])
    op.create_index("ix_survey_options_question_id", "survey_options", ["question_id"])

    op.create_table(
        "survey_audience_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("source_app", sa.String(length=80), nullable=True),
        sa.Column("external_entity_type", sa.String(length=80), nullable=True),
        sa.Column("external_entity_id", sa.String(length=120), nullable=True),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("is_dynamic", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(length=150), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", "nombre", name="uq_survey_audience_groups_tenant_name"),
    )
    op.create_index("ix_survey_audience_groups_tenant_id", "survey_audience_groups", ["tenant_id"])
    op.create_index("ix_survey_audience_groups_source_app", "survey_audience_groups", ["source_app"])
    op.create_index("ix_survey_audience_groups_external_entity_type", "survey_audience_groups", ["external_entity_type"])
    op.create_index("ix_survey_audience_groups_external_entity_id", "survey_audience_groups", ["external_entity_id"])

    op.create_table(
        "survey_audience_group_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("survey_audience_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_key", sa.String(length=120), nullable=False),
        sa.Column("member_name_snapshot", sa.String(length=200), nullable=True),
        sa.Column("member_role_snapshot", sa.String(length=150), nullable=True),
        sa.Column("member_area_snapshot", sa.String(length=150), nullable=True),
        sa.Column("member_position_snapshot", sa.String(length=150), nullable=True),
        sa.Column("member_company_snapshot", sa.String(length=150), nullable=True),
        sa.Column("source_app", sa.String(length=80), nullable=True),
        sa.Column("external_entity_type", sa.String(length=80), nullable=True),
        sa.Column("external_entity_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("group_id", "member_key", name="uq_survey_audience_group_members_group_member"),
    )
    op.create_index("ix_survey_audience_group_members_tenant_id", "survey_audience_group_members", ["tenant_id"])
    op.create_index("ix_survey_audience_group_members_group_id", "survey_audience_group_members", ["group_id"])
    op.create_index("ix_survey_audience_group_members_member_key", "survey_audience_group_members", ["member_key"])
    op.create_index("ix_survey_audience_group_members_source_app", "survey_audience_group_members", ["source_app"])
    op.create_index("ix_survey_audience_group_members_external_entity_type", "survey_audience_group_members", ["external_entity_type"])
    op.create_index("ix_survey_audience_group_members_external_entity_id", "survey_audience_group_members", ["external_entity_id"])

    op.create_table(
        "survey_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("survey_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("audience_group_id", sa.Integer(), sa.ForeignKey("survey_audience_groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assignee_key", sa.String(length=120), nullable=False),
        sa.Column("assignee_name_snapshot", sa.String(length=200), nullable=True),
        sa.Column("assignee_role_snapshot", sa.String(length=150), nullable=True),
        sa.Column("assignee_area_snapshot", sa.String(length=150), nullable=True),
        sa.Column("assignee_position_snapshot", sa.String(length=150), nullable=True),
        sa.Column("assignee_company_snapshot", sa.String(length=150), nullable=True),
        sa.Column("source_app", sa.String(length=80), nullable=True),
        sa.Column("external_entity_type", sa.String(length=80), nullable=True),
        sa.Column("external_entity_id", sa.String(length=120), nullable=True),
        sa.Column("assignment_type", sa.String(length=40), nullable=False, server_default="user"),
        sa.Column("channel", sa.String(length=40), nullable=False, server_default="internal"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("first_sent_at", sa.DateTime(), nullable=True),
        sa.Column("last_sent_at", sa.DateTime(), nullable=True),
        sa.Column("response_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "instance_id",
            "assignee_key",
            "channel",
            name="uq_survey_assignments_instance_assignee_channel",
        ),
    )
    op.create_index("ix_survey_assignments_tenant_id", "survey_assignments", ["tenant_id"])
    op.create_index("ix_survey_assignments_instance_id", "survey_assignments", ["instance_id"])
    op.create_index("ix_survey_assignments_audience_group_id", "survey_assignments", ["audience_group_id"])
    op.create_index("ix_survey_assignments_assignee_key", "survey_assignments", ["assignee_key"])
    op.create_index("ix_survey_assignments_source_app", "survey_assignments", ["source_app"])
    op.create_index("ix_survey_assignments_external_entity_type", "survey_assignments", ["external_entity_type"])
    op.create_index("ix_survey_assignments_external_entity_id", "survey_assignments", ["external_entity_id"])
    op.create_index("ix_survey_assignments_assignment_type", "survey_assignments", ["assignment_type"])
    op.create_index("ix_survey_assignments_status", "survey_assignments", ["status"])
    op.create_index("ix_survey_assignments_due_at", "survey_assignments", ["due_at"])

    op.create_table(
        "survey_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("survey_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("survey_assignments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("respondent_key", sa.String(length=120), nullable=True),
        sa.Column("respondent_name_snapshot", sa.String(length=200), nullable=True),
        sa.Column("respondent_role_snapshot", sa.String(length=150), nullable=True),
        sa.Column("respondent_area_snapshot", sa.String(length=150), nullable=True),
        sa.Column("respondent_position_snapshot", sa.String(length=150), nullable=True),
        sa.Column("respondent_company_snapshot", sa.String(length=150), nullable=True),
        sa.Column("source_app", sa.String(length=80), nullable=True),
        sa.Column("external_entity_type", sa.String(length=80), nullable=True),
        sa.Column("external_entity_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("submission_channel", sa.String(length=40), nullable=False, server_default="internal"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("last_saved_at", sa.DateTime(), nullable=True),
        sa.Column("completion_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("answers_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_survey_responses_tenant_id", "survey_responses", ["tenant_id"])
    op.create_index("ix_survey_responses_instance_id", "survey_responses", ["instance_id"])
    op.create_index("ix_survey_responses_assignment_id", "survey_responses", ["assignment_id"])
    op.create_index("ix_survey_responses_respondent_key", "survey_responses", ["respondent_key"])
    op.create_index("ix_survey_responses_source_app", "survey_responses", ["source_app"])
    op.create_index("ix_survey_responses_external_entity_type", "survey_responses", ["external_entity_type"])
    op.create_index("ix_survey_responses_external_entity_id", "survey_responses", ["external_entity_id"])
    op.create_index("ix_survey_responses_status", "survey_responses", ["status"])
    op.create_index("ix_survey_responses_started_at", "survey_responses", ["started_at"])
    op.create_index("ix_survey_responses_submitted_at", "survey_responses", ["submitted_at"])

    op.create_table(
        "survey_response_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("response_id", sa.Integer(), sa.ForeignKey("survey_responses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("option_id", sa.Integer(), sa.ForeignKey("survey_options.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answer_value", sa.String(length=160), nullable=True),
        sa.Column("answer_json", sa.JSON(), nullable=True),
        sa.Column("score_value", sa.Float(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "response_id",
            "question_id",
            "item_index",
            name="uq_survey_response_items_response_question_index",
        ),
    )
    op.create_index("ix_survey_response_items_tenant_id", "survey_response_items", ["tenant_id"])
    op.create_index("ix_survey_response_items_response_id", "survey_response_items", ["response_id"])
    op.create_index("ix_survey_response_items_question_id", "survey_response_items", ["question_id"])
    op.create_index("ix_survey_response_items_option_id", "survey_response_items", ["option_id"])

    op.create_table(
        "survey_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("survey_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("segment_type", sa.String(length=60), nullable=False, server_default="general"),
        sa.Column("segment_key", sa.String(length=120), nullable=False, server_default="general"),
        sa.Column("metric_key", sa.String(length=80), nullable=False),
        sa.Column("metric_label", sa.String(length=180), nullable=True),
        sa.Column("value_numeric", sa.Float(), nullable=True),
        sa.Column("value_text", sa.String(length=200), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "instance_id",
            "segment_key",
            "metric_key",
            name="uq_survey_results_instance_segment_metric",
        ),
    )
    op.create_index("ix_survey_results_tenant_id", "survey_results", ["tenant_id"])
    op.create_index("ix_survey_results_instance_id", "survey_results", ["instance_id"])
    op.create_index("ix_survey_results_segment_type", "survey_results", ["segment_type"])
    op.create_index("ix_survey_results_segment_key", "survey_results", ["segment_key"])
    op.create_index("ix_survey_results_metric_key", "survey_results", ["metric_key"])
    op.create_index("ix_survey_results_computed_at", "survey_results", ["computed_at"])

    op.create_table(
        "survey_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("survey_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("survey_assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("response_id", sa.Integer(), sa.ForeignKey("survey_responses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="in_progress"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=True),
        sa.Column("score_value", sa.Float(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("assignment_id", "attempt_number", name="uq_survey_attempts_assignment_number"),
    )
    op.create_index("ix_survey_attempts_tenant_id", "survey_attempts", ["tenant_id"])
    op.create_index("ix_survey_attempts_instance_id", "survey_attempts", ["instance_id"])
    op.create_index("ix_survey_attempts_assignment_id", "survey_attempts", ["assignment_id"])
    op.create_index("ix_survey_attempts_response_id", "survey_attempts", ["response_id"])
    op.create_index("ix_survey_attempts_status", "survey_attempts", ["status"])
    op.create_index("ix_survey_attempts_started_at", "survey_attempts", ["started_at"])
    op.create_index("ix_survey_attempts_submitted_at", "survey_attempts", ["submitted_at"])

    op.create_table(
        "survey_evaluations_360",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("survey_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("survey_assignments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evaluatee_key", sa.String(length=120), nullable=False),
        sa.Column("evaluator_key", sa.String(length=120), nullable=False),
        sa.Column("relationship_type", sa.String(length=40), nullable=False),
        sa.Column("evaluatee_name_snapshot", sa.String(length=200), nullable=True),
        sa.Column("evaluatee_role_snapshot", sa.String(length=150), nullable=True),
        sa.Column("evaluatee_area_snapshot", sa.String(length=150), nullable=True),
        sa.Column("evaluatee_position_snapshot", sa.String(length=150), nullable=True),
        sa.Column("evaluatee_company_snapshot", sa.String(length=150), nullable=True),
        sa.Column("evaluator_name_snapshot", sa.String(length=200), nullable=True),
        sa.Column("evaluator_role_snapshot", sa.String(length=150), nullable=True),
        sa.Column("evaluator_area_snapshot", sa.String(length=150), nullable=True),
        sa.Column("evaluator_position_snapshot", sa.String(length=150), nullable=True),
        sa.Column("evaluator_company_snapshot", sa.String(length=150), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("source_app", sa.String(length=80), nullable=True),
        sa.Column("external_entity_type", sa.String(length=80), nullable=True),
        sa.Column("external_entity_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "instance_id",
            "evaluatee_key",
            "evaluator_key",
            "relationship_type",
            name="uq_survey_evaluations_360_unique_link",
        ),
    )
    op.create_index("ix_survey_evaluations_360_tenant_id", "survey_evaluations_360", ["tenant_id"])
    op.create_index("ix_survey_evaluations_360_instance_id", "survey_evaluations_360", ["instance_id"])
    op.create_index("ix_survey_evaluations_360_assignment_id", "survey_evaluations_360", ["assignment_id"])
    op.create_index("ix_survey_evaluations_360_evaluatee_key", "survey_evaluations_360", ["evaluatee_key"])
    op.create_index("ix_survey_evaluations_360_evaluator_key", "survey_evaluations_360", ["evaluator_key"])
    op.create_index("ix_survey_evaluations_360_relationship_type", "survey_evaluations_360", ["relationship_type"])
    op.create_index("ix_survey_evaluations_360_status", "survey_evaluations_360", ["status"])
    op.create_index("ix_survey_evaluations_360_source_app", "survey_evaluations_360", ["source_app"])
    op.create_index("ix_survey_evaluations_360_external_entity_type", "survey_evaluations_360", ["external_entity_type"])
    op.create_index("ix_survey_evaluations_360_external_entity_id", "survey_evaluations_360", ["external_entity_id"])


def downgrade() -> None:
    op.drop_table("survey_evaluations_360")
    op.drop_table("survey_attempts")
    op.drop_table("survey_results")
    op.drop_table("survey_response_items")
    op.drop_table("survey_responses")
    op.drop_table("survey_assignments")
    op.drop_table("survey_audience_group_members")
    op.drop_table("survey_audience_groups")
    op.drop_table("survey_options")
    op.drop_table("survey_questions")
    op.drop_table("survey_sections")
    op.drop_table("survey_instances")
    op.drop_table("survey_templates")
