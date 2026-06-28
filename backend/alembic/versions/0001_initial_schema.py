"""initial schema: users, agents, github_accounts, pr_events

Revision ID: 0001
Revises:
Create Date: 2026-06-28 00:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------------- users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # --------------------------------------------------------------- agents
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("repo_full_name", sa.String(length=255), nullable=False),
        sa.Column(
            "llm_provider", sa.String(length=16), nullable=False, server_default="ollama"
        ),
        sa.Column(
            "vector_db_type",
            sa.String(length=16),
            nullable=False,
            server_default="pgvector",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "ingestion_status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_agents_user_id", "agents", ["user_id"])
    op.create_index("ix_agents_repo_full_name", "agents", ["repo_full_name"])

    # ----------------------------------------------------- github_accounts
    op.create_table(
        "github_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("github_username", sa.String(length=255), nullable=False),
        sa.Column("flag_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "account_status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.Column("banned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "first_seen",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "github_username", name="uq_github_accounts_username"
        ),
    )
    op.create_index(
        "ix_github_accounts_github_username", "github_accounts", ["github_username"]
    )

    # ----------------------------------------------------------- pr_events
    op.create_table(
        "pr_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "agent_id",
            sa.Integer(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("pr_url", sa.String(length=500), nullable=False),
        sa.Column("author_github", sa.String(length=255), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("layer_caught", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_pr_events_agent_id", "pr_events", ["agent_id"])
    op.create_index("ix_pr_events_author_github", "pr_events", ["author_github"])
    op.create_index("ix_pr_events_decision", "pr_events", ["decision"])
    op.create_index("ix_pr_events_created_at", "pr_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_pr_events_created_at", table_name="pr_events")
    op.drop_index("ix_pr_events_decision", table_name="pr_events")
    op.drop_index("ix_pr_events_author_github", table_name="pr_events")
    op.drop_index("ix_pr_events_agent_id", table_name="pr_events")
    op.drop_table("pr_events")

    op.drop_index(
        "ix_github_accounts_github_username", table_name="github_accounts"
    )
    op.drop_table("github_accounts")

    op.drop_index("ix_agents_repo_full_name", table_name="agents")
    op.drop_index("ix_agents_user_id", table_name="agents")
    op.drop_table("agents")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
