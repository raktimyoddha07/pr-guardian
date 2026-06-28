"""KnowledgeChunk model — RAG source chunk + embedding (pgvector)."""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base

# pgvector is optional at import time — only declare the vector column when the
# extension is available. We try to import it; if it's missing, fall back to a
# JSON column so the app still boots (migrations/queries that use vectors will
# error explicitly, which is fine for chromadb-only setups).
try:
    from pgvector.sqlalchemy import Vector  # type: ignore[import-not-found]
    _HAS_PGVECTOR = True
except Exception:  # pragma: no cover — pgvector not installed in some envs
    _HAS_PGVECTOR = False


def _embedding_column() -> Any:
    dim = settings.EMBEDDING_DIM
    if _HAS_PGVECTOR:
        return Vector(dim).with_variant(
            Vector(dim), "postgresql"
        )
    # Non-pgvector environments: store as text placeholder.
    return Text()


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # "repo" | "issue"
    source_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    # repo: "path/to/file.py"; issue: "issues/42"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any] = mapped_column(_embedding_column(), nullable=True)

    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    agent: Mapped["Agent"] = relationship("Agent")  # noqa: F821

    def __repr__(self) -> str:
        return f"<KnowledgeChunk id={self.id} {self.source_type}:{self.source_ref}>"


# Exported flag so the vector store can decide whether to use vector ops.
HAS_PGVECTOR: bool = _HAS_PGVECTOR
