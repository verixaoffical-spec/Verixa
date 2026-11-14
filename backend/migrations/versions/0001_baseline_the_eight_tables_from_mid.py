"""baseline: the eight tables from mid

Revision ID: 0001
Revises: 
Create Date: 2026-11-14 17:41:03.898842
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Generated from backend.db.Base and backend.agent_db.AgentBase, which are mid's models unchanged (T-010).
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")  # QA Memory (FYP-II); kept when downgrading
    op.create_table('pending_signups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('password_hash', sa.String(length=200), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=True),
    sa.Column('name', sa.String(length=80), nullable=True),
    sa.Column('password_hash', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('github_id', sa.BigInteger(), nullable=True),
    sa.Column('github_login', sa.String(length=100), nullable=True),
    sa.Column('github_name', sa.String(length=200), nullable=True),
    sa.Column('github_token', sa.Text(), nullable=True),
    sa.Column('github_refresh', sa.Text(), nullable=True),
    sa.Column('github_expires_at', sa.BigInteger(), nullable=True),
    sa.Column('atlassian_token', sa.Text(), nullable=True),
    sa.Column('atlassian_refresh', sa.Text(), nullable=True),
    sa.Column('atlassian_expires_at', sa.BigInteger(), nullable=True),
    sa.Column('jira_cloud_id', sa.String(length=100), nullable=True),
    sa.Column('jira_site', sa.String(length=200), nullable=True),
    sa.Column('totp_secret', sa.Text(), nullable=True),
    sa.Column('totp_pending', sa.Text(), nullable=True),
    sa.Column('totp_last_step', sa.BigInteger(), nullable=True),
    sa.Column('session_version', sa.Integer(), server_default='0', nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('github_id')
    )
    op.create_table('password_resets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_password_resets_user_id'), 'password_resets', ['user_id'], unique=False)
    op.create_table('projects',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('repo', sa.String(length=200), nullable=False),
    sa.Column('jira_key', sa.String(length=50), nullable=False),
    sa.Column('jira_name', sa.String(length=200), nullable=False),
    sa.Column('hook_id', sa.BigInteger(), nullable=True),
    sa.Column('webhook_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('recovery_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('code_hash', sa.String(length=200), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recovery_codes_user_id'), 'recovery_codes', ['user_id'], unique=False)
    op.create_table('collections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('request_count', sa.Integer(), nullable=False),
    sa.Column('revision', sa.Integer(), server_default='1', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id')
    )
    op.create_table('spec_files',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('test_count', sa.Integer(), nullable=False),
    sa.Column('revision', sa.Integer(), server_default='1', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'name')
    )
    op.create_table('risk_assessments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('repo', sa.String(length=200), nullable=False),
    sa.Column('pr_number', sa.Integer(), nullable=False),
    sa.Column('head_sha', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=True),
    sa.Column('pr_url', sa.String(length=500), nullable=True),
    sa.Column('author', sa.String(length=100), nullable=True),
    sa.Column('delivery_id', sa.String(length=100), nullable=True),
    sa.Column('state', sa.String(length=24), nullable=False),
    sa.Column('risk_label', sa.String(length=10), nullable=True),
    sa.Column('base_label', sa.String(length=10), nullable=True),
    sa.Column('score', sa.Integer(), nullable=True),
    sa.Column('module', sa.String(length=200), nullable=True),
    sa.Column('modules_touched', sa.Text(), nullable=True),
    sa.Column('files_changed', sa.Integer(), nullable=True),
    sa.Column('lines_changed', sa.Integer(), nullable=True),
    sa.Column('past_defects', sa.Integer(), nullable=True),
    sa.Column('sensitivity', sa.String(length=10), nullable=True),
    sa.Column('scoring_basis', sa.String(length=200), nullable=True),
    sa.Column('risk_factors', sa.Text(), nullable=True),
    sa.Column('reasoning', sa.Text(), nullable=True),
    sa.Column('test_areas', sa.Text(), nullable=True),
    sa.Column('model_used', sa.String(length=120), nullable=True),
    sa.Column('concern', sa.Text(), nullable=True),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('errors', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'pr_number', 'head_sha', name='uq_risk_pr_head')
    )
    op.create_index(op.f('ix_risk_assessments_project_id'), 'risk_assessments', ['project_id'], unique=False)
    op.create_index(op.f('ix_risk_assessments_repo'), 'risk_assessments', ['repo'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_risk_assessments_repo'), table_name='risk_assessments')
    op.drop_index(op.f('ix_risk_assessments_project_id'), table_name='risk_assessments')
    op.drop_table('risk_assessments')
    op.drop_table('spec_files')
    op.drop_table('collections')
    op.drop_index(op.f('ix_recovery_codes_user_id'), table_name='recovery_codes')
    op.drop_table('recovery_codes')
    op.drop_table('projects')
    op.drop_index(op.f('ix_password_resets_user_id'), table_name='password_resets')
    op.drop_table('password_resets')
    op.drop_table('users')
    op.drop_table('pending_signups')
