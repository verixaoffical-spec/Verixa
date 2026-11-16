"""pull_requests: source and target branch of each pull request (T-099)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-16 04:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Saved rows get their branches on the next read of GitHub's list or the next webhook delivery
    op.add_column('pull_requests', sa.Column('head_ref', sa.String(length=255), nullable=True))
    op.add_column('pull_requests', sa.Column('base_ref', sa.String(length=255), nullable=True))
    op.create_index('ix_pull_requests_head', 'pull_requests', ['project_id', 'head_ref'], unique=False)
    op.create_index('ix_pull_requests_base', 'pull_requests', ['project_id', 'base_ref'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_pull_requests_base', table_name='pull_requests')
    op.drop_index('ix_pull_requests_head', table_name='pull_requests')
    op.drop_column('pull_requests', 'base_ref')
    op.drop_column('pull_requests', 'head_ref')
