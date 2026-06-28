"""Vector store — pgvector only.

Embeddings live in the ``KnowledgeChunk`` table alongside the rest of the data,
so there's one source of truth, one DB to back up, and native cosine-distance
search with no extra service to run. The ``Agent.vector_db_type`` column is kept
for backward compatibility but every agent uses pgvector.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.knowledge_chunk import HAS_PGVECTOR, KnowledgeChunk


@dataclass
class ChunkHit:
    content: str
    source_type: str
    source_ref: str
    score: float


class PgVectorStore:
    """Stores and searches embeddings via the ``KnowledgeChunk`` table."""

    async def reset(self, agent_id: int) -> None:
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(KnowledgeChunk).where(KnowledgeChunk.agent_id == agent_id)
            )
            await db.commit()

    async def add(
        self,
        agent_id: int,
        chunks: list[tuple[str, str, str, list[float]]],
    ) -> int:
        """Add (source_type, source_ref, content, embedding) tuples. Returns count."""
        if not chunks:
            return 0
        rows = [
            KnowledgeChunk(
                agent_id=agent_id,
                source_type=source_type,
                source_ref=source_ref,
                content=content,
                embedding=embedding,
            )
            for source_type, source_ref, content, embedding in chunks
        ]
        async with AsyncSessionLocal() as db:
            db.add_all(rows)
            await db.commit()
        return len(rows)

    async def search(
        self, agent_id: int, query_embedding: list[float], k: int = 8
    ) -> list[ChunkHit]:
        if not HAS_PGVECTOR:
            raise RuntimeError(
                "pgvector is not installed; install pgvector + the extension"
            )
        from pgvector.sqlalchemy import Vector  # type: ignore[import-not-found]

        async with AsyncSessionLocal() as db:
            stmt = (
                select(
                    KnowledgeChunk.content,
                    KnowledgeChunk.source_type,
                    KnowledgeChunk.source_ref,
                    KnowledgeChunk.embedding.cosine_distance(query_embedding).label(
                        "distance"
                    ),
                )
                .where(KnowledgeChunk.agent_id == agent_id)
                .order_by("distance")
                .limit(k)
            )
            result = await db.execute(stmt)
            hits = []
            for content, source_type, source_ref, distance in result.all():
                # cosine_distance is 0 (identical) → 2 (opposite); score = 1 - dist.
                hits.append(
                    ChunkHit(
                        content=content,
                        source_type=source_type,
                        source_ref=source_ref,
                        score=max(0.0, 1.0 - float(distance)),
                    )
                )
            return hits


# Single shared instance — there is only one vector store in this app.
vector_store = PgVectorStore()


def get_vector_store(_vector_db_type: str | None = None) -> PgVectorStore:
    """Return the vector store. ``vector_db_type`` is ignored — pgvector only."""
    return vector_store
