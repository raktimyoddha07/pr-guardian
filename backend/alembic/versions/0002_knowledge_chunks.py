"""add knowledge_chunks table (pgvector)

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-28 00:01:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector type. We create the extension here too (idempotent) so a fresh
    # database has it before the vector column is added.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "agent_id",
            sa.Integer(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_ref", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_knowledge_chunks_agent_id", "knowledge_chunks", ["agent_id"])

    # Upgrade the plain-float ARRAY column to a real vector type. Done as a raw
    # ALTER so we don't depend on pgvector's alembic integration at generation
    # time; the runtime model uses pgvector.sqlalchemy.Vector.
    op.execute(
        "ALTER TABLE knowledge_chunks "
        "ALTER COLUMN embedding TYPE vector(768) USING embedding::vector(768);"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding "
        "ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding;")
    op.drop_index("ix_knowledge_chunks_agent_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
