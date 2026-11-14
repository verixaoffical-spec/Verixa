"""model_calls log (T-026)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14 18:55:22.720149
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('model_calls',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agent', sa.String(length=40), nullable=False),
    sa.Column('model', sa.String(length=120), nullable=False),
    sa.Column('provider', sa.String(length=40), nullable=False),
    sa.Column('tokens', sa.Integer(), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('ok', sa.Boolean(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('run_id', sa.String(length=40), nullable=True),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_calls_at'), 'model_calls', ['at'], unique=False)
    op.create_index(op.f('ix_model_calls_run_id'), 'model_calls', ['run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_model_calls_run_id'), table_name='model_calls')
    op.drop_index(op.f('ix_model_calls_at'), table_name='model_calls')
    op.drop_table('model_calls')
