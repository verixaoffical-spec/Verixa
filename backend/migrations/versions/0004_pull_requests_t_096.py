"""pull_requests: every pull request of a connected repository with its author (T-096)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-15 16:59:51.959527
"""
from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('pull_requests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('repo', sa.String(length=200), nullable=False),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=True),
    sa.Column('author', sa.String(length=100), nullable=True),
    sa.Column('state', sa.String(length=10), nullable=False),
    sa.Column('draft', sa.Boolean(), nullable=False),
    sa.Column('html_url', sa.String(length=500), nullable=True),
    sa.Column('head_sha', sa.String(length=64), nullable=True),
    sa.Column('gh_created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('gh_updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('synced_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('listed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'number', name='uq_pull_requests_project_number')
    )
    op.create_index('ix_pull_requests_feed', 'pull_requests', ['project_id', 'gh_updated_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_pull_requests_feed', table_name='pull_requests')
    op.drop_table('pull_requests')
