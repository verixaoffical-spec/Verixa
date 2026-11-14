"""pr_file_snapshots, agent_steps and the Risk feed index (T-094, D-013)

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-15 03:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('pr_file_snapshots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('assessment_id', sa.Integer(), nullable=False),
    sa.Column('head_sha', sa.String(length=64), nullable=False),
    sa.Column('data', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['assessment_id'], ['risk_assessments.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('assessment_id')
    )
    op.create_table('agent_steps',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('repo', sa.String(length=200), nullable=False),
    sa.Column('pr_number', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.String(length=40), nullable=True),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('event', sa.String(length=60), nullable=False),
    sa.Column('stage', sa.String(length=20), nullable=False),
    sa.Column('level', sa.String(length=10), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('done', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_steps_pr', 'agent_steps', ['repo', 'pr_number', 'at'], unique=False)
    op.create_index('ix_risk_feed', 'risk_assessments', ['project_id', 'repo', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_risk_feed', table_name='risk_assessments')
    op.drop_index('ix_agent_steps_pr', table_name='agent_steps')
    op.drop_table('agent_steps')
    op.drop_table('pr_file_snapshots')
