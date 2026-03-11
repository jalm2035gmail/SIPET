"""Initial migration

Revision ID: 428edd7ec8a9
Revises: 
Create Date: 2026-02-10 21:44:34.249176

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '428edd7ec8a9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(idx.get("name") == index_name for idx in inspector.get_indexes(table_name))


def _unique_exists(table_name: str, unique_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(item.get("name") == unique_name for item in inspector.get_unique_constraints(table_name))


def upgrade() -> None:
    """Upgrade schema."""
    if not _table_exists('departments'):
        op.create_table('departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('manager_id', sa.Integer(), nullable=True),
        sa.Column('budget', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['manager_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['departments.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
        )
    if _table_exists('departments') and not _index_exists('departments', op.f('ix_departments_id')):
        op.create_index(op.f('ix_departments_id'), 'departments', ['id'], unique=False)
    if not _table_exists('reports'):
        op.create_table('reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=True),
        sa.Column('template', sa.JSON(), nullable=True),
        sa.Column('schedule', sa.JSON(), nullable=True),
        sa.Column('recipients', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
    if _table_exists('reports') and not _index_exists('reports', op.f('ix_reports_id')):
        op.create_index(op.f('ix_reports_id'), 'reports', ['id'], unique=False)
    if not _table_exists('users'):
        op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=True),
        sa.Column('full_name', sa.String(length=150), nullable=True),
        sa.Column('password', sa.String(length=255), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if _table_exists('users') and not _index_exists('users', op.f('ix_users_email')):
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    if _table_exists('users') and not _index_exists('users', op.f('ix_users_id')):
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    if _table_exists('users') and not _index_exists('users', op.f('ix_users_username')):
        op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    if not _table_exists('generated_reports'):
        op.create_table('generated_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if _table_exists('generated_reports') and not _index_exists('generated_reports', op.f('ix_generated_reports_id')):
        op.create_index(op.f('ix_generated_reports_id'), 'generated_reports', ['id'], unique=False)
    if not _table_exists('strategic_plans'):
        op.create_table('strategic_plans',
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('vision', sa.Text(), nullable=False),
        sa.Column('mission', sa.Text(), nullable=False),
        sa.Column('values', sa.JSON(), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'IN_REVIEW', 'APPROVED', 'ACTIVE', 'COMPLETED', 'ARCHIVED', 'CANCELLED', name='planstatus'), nullable=True),
        sa.Column('approval_date', sa.Date(), nullable=True),
        sa.Column('approval_by', sa.Integer(), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('parent_plan_id', sa.Integer(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['parent_plan_id'], ['strategic_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if _table_exists('strategic_plans') and not _index_exists('strategic_plans', op.f('ix_strategic_plans_code')):
        op.create_index(op.f('ix_strategic_plans_code'), 'strategic_plans', ['code'], unique=True)
    if _table_exists('strategic_plans') and not _index_exists('strategic_plans', op.f('ix_strategic_plans_id')):
        op.create_index(op.f('ix_strategic_plans_id'), 'strategic_plans', ['id'], unique=False)
    if _table_exists('strategic_plans') and not _index_exists('strategic_plans', op.f('ix_strategic_plans_name')):
        op.create_index(op.f('ix_strategic_plans_name'), 'strategic_plans', ['name'], unique=False)
    if not _table_exists('diagnostic_analysis'):
        op.create_table('diagnostic_analysis',
        sa.Column('strategic_plan_id', sa.Integer(), nullable=False),
        sa.Column('swot_strengths', sa.JSON(), nullable=True),
        sa.Column('swot_weaknesses', sa.JSON(), nullable=True),
        sa.Column('swot_opportunities', sa.JSON(), nullable=True),
        sa.Column('swot_threats', sa.JSON(), nullable=True),
        sa.Column('pestel_political', sa.JSON(), nullable=True),
        sa.Column('pestel_economic', sa.JSON(), nullable=True),
        sa.Column('pestel_social', sa.JSON(), nullable=True),
        sa.Column('pestel_technological', sa.JSON(), nullable=True),
        sa.Column('pestel_environmental', sa.JSON(), nullable=True),
        sa.Column('pestel_legal', sa.JSON(), nullable=True),
        sa.Column('porter_supplier_power', sa.Text(), nullable=True),
        sa.Column('porter_buyer_power', sa.Text(), nullable=True),
        sa.Column('porter_competitive_rivalry', sa.Text(), nullable=True),
        sa.Column('porter_threat_of_substitutes', sa.Text(), nullable=True),
        sa.Column('porter_threat_of_new_entrants', sa.Text(), nullable=True),
        sa.Column('customer_perception', sa.JSON(), nullable=True),
        sa.Column('market_research', sa.JSON(), nullable=True),
        sa.Column('competitor_analysis', sa.JSON(), nullable=True),
        sa.Column('key_findings', sa.Text(), nullable=True),
        sa.Column('strategic_implications', sa.Text(), nullable=True),
        sa.Column('recommendations', sa.Text(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['strategic_plan_id'], ['strategic_plans.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('strategic_plan_id')
        )
    if _table_exists('diagnostic_analysis') and not _index_exists('diagnostic_analysis', op.f('ix_diagnostic_analysis_id')):
        op.create_index(op.f('ix_diagnostic_analysis_id'), 'diagnostic_analysis', ['id'], unique=False)
    if not _table_exists('poas'):
        op.create_table('poas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategic_plan_id', sa.Integer(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('total_budget', sa.Float(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['strategic_plan_id'], ['strategic_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if _table_exists('poas') and not _index_exists('poas', op.f('ix_poas_id')):
        op.create_index(op.f('ix_poas_id'), 'poas', ['id'], unique=False)
    if not _table_exists('strategic_axes'):
        op.create_table('strategic_axes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategic_plan_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('color', sa.String(length=10), nullable=True),
        sa.Column('progress', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['strategic_plan_id'], ['strategic_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if _table_exists('strategic_axes') and not _index_exists('strategic_axes', op.f('ix_strategic_axes_id')):
        op.create_index(op.f('ix_strategic_axes_id'), 'strategic_axes', ['id'], unique=False)
    if not _table_exists('strategic_objectives'):
        op.create_table('strategic_objectives',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategic_axis_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['strategic_axis_id'], ['strategic_axes.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if _table_exists('strategic_objectives') and not _index_exists('strategic_objectives', op.f('ix_strategic_objectives_id')):
        op.create_index(op.f('ix_strategic_objectives_id'), 'strategic_objectives', ['id'], unique=False)
    if not _table_exists('activities'):
        op.create_table('activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('poa_id', sa.Integer(), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('strategic_objective_id', sa.Integer(), nullable=True),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('budget', sa.Float(), nullable=True),
        sa.Column('progress', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['poa_id'], ['poas.id'], ),
        sa.ForeignKeyConstraint(['strategic_objective_id'], ['strategic_objectives.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if _table_exists('activities') and not _index_exists('activities', op.f('ix_activities_id')):
        op.create_index(op.f('ix_activities_id'), 'activities', ['id'], unique=False)
    if not _table_exists('kpis'):
        op.create_table('kpis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('strategic_objective_id', sa.Integer(), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('responsible_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(length=20), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('target_value', sa.Float(), nullable=True),
        sa.Column('min_value', sa.Float(), nullable=True),
        sa.Column('max_value', sa.Float(), nullable=True),
        sa.Column('formula', sa.Text(), nullable=True),
        sa.Column('data_source', sa.String(length=200), nullable=True),
        sa.Column('frequency', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['responsible_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['strategic_objective_id'], ['strategic_objectives.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
        )
    if _table_exists('kpis') and not _index_exists('kpis', op.f('ix_kpis_id')):
        op.create_index(op.f('ix_kpis_id'), 'kpis', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    if _table_exists('kpis') and _index_exists('kpis', op.f('ix_kpis_id')):
        op.drop_index(op.f('ix_kpis_id'), table_name='kpis')
    if _table_exists('kpis'):
        op.drop_table('kpis')
    if _table_exists('activities') and _index_exists('activities', op.f('ix_activities_id')):
        op.drop_index(op.f('ix_activities_id'), table_name='activities')
    if _table_exists('activities'):
        op.drop_table('activities')
    if _table_exists('strategic_objectives') and _index_exists('strategic_objectives', op.f('ix_strategic_objectives_id')):
        op.drop_index(op.f('ix_strategic_objectives_id'), table_name='strategic_objectives')
    if _table_exists('strategic_objectives'):
        op.drop_table('strategic_objectives')
    if _table_exists('strategic_axes') and _index_exists('strategic_axes', op.f('ix_strategic_axes_id')):
        op.drop_index(op.f('ix_strategic_axes_id'), table_name='strategic_axes')
    if _table_exists('strategic_axes'):
        op.drop_table('strategic_axes')
    if _table_exists('poas') and _index_exists('poas', op.f('ix_poas_id')):
        op.drop_index(op.f('ix_poas_id'), table_name='poas')
    if _table_exists('poas'):
        op.drop_table('poas')
    if _table_exists('diagnostic_analysis') and _index_exists('diagnostic_analysis', op.f('ix_diagnostic_analysis_id')):
        op.drop_index(op.f('ix_diagnostic_analysis_id'), table_name='diagnostic_analysis')
    if _table_exists('diagnostic_analysis'):
        op.drop_table('diagnostic_analysis')
    if _table_exists('strategic_plans') and _index_exists('strategic_plans', op.f('ix_strategic_plans_name')):
        op.drop_index(op.f('ix_strategic_plans_name'), table_name='strategic_plans')
    if _table_exists('strategic_plans') and _index_exists('strategic_plans', op.f('ix_strategic_plans_id')):
        op.drop_index(op.f('ix_strategic_plans_id'), table_name='strategic_plans')
    if _table_exists('strategic_plans') and _index_exists('strategic_plans', op.f('ix_strategic_plans_code')):
        op.drop_index(op.f('ix_strategic_plans_code'), table_name='strategic_plans')
    if _table_exists('strategic_plans'):
        op.drop_table('strategic_plans')
    if _table_exists('generated_reports') and _index_exists('generated_reports', op.f('ix_generated_reports_id')):
        op.drop_index(op.f('ix_generated_reports_id'), table_name='generated_reports')
    if _table_exists('generated_reports'):
        op.drop_table('generated_reports')
    if _table_exists('users') and _index_exists('users', op.f('ix_users_username')):
        op.drop_index(op.f('ix_users_username'), table_name='users')
    if _table_exists('users') and _index_exists('users', op.f('ix_users_id')):
        op.drop_index(op.f('ix_users_id'), table_name='users')
    if _table_exists('users') and _index_exists('users', op.f('ix_users_email')):
        op.drop_index(op.f('ix_users_email'), table_name='users')
    if _table_exists('users'):
        op.drop_table('users')
    if _table_exists('reports') and _index_exists('reports', op.f('ix_reports_id')):
        op.drop_index(op.f('ix_reports_id'), table_name='reports')
    if _table_exists('reports'):
        op.drop_table('reports')
    if _table_exists('departments') and _index_exists('departments', op.f('ix_departments_id')):
        op.drop_index(op.f('ix_departments_id'), table_name='departments')
    if _table_exists('departments'):
        op.drop_table('departments')
