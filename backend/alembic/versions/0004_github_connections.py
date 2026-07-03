"""Add GitHub connections table for OAuth integration

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create github_connections table
    op.create_table(
        'github_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('github_user_id', sa.Integer(), nullable=False),
        sa.Column('github_username', sa.String(length=255), nullable=False),
        sa.Column('github_email', sa.String(length=255), nullable=True),
        sa.Column('access_token', sa.String(length=500), nullable=False),
        sa.Column('refresh_token', sa.String(length=500), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('installation_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_github_connections_github_user_id'), 'github_connections', ['github_user_id'], unique=False)
    op.create_index(op.f('ix_github_connections_installation_id'), 'github_connections', ['installation_id'], unique=False)
    op.create_index(op.f('ix_github_connections_user_id'), 'github_connections', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_github_connections_user_id'), table_name='github_connections')
    op.drop_index(op.f('ix_github_connections_installation_id'), table_name='github_connections')
    op.drop_index(op.f('ix_github_connections_github_user_id'), table_name='github_connections')
    op.drop_table('github_connections')
