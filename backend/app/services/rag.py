"""RAG retrieval helpers.

``retrieve`` embeds the query and returns the top-K most similar knowledge
chunks for an agent (cosine similarity over the ``KnowledgeChunk`` table).
"""
from __future__ import annotations

from app.services.llm import get_embedding, resolve_provider
from app.services.vectorstore import ChunkHit, vector_store


async def retrieve(
    agent,
    query: str,
    k: int = 8,
) -> list[ChunkHit]:
    """Return the top-K chunk hits for ``query`` against ``agent``'s KB."""
    provider = resolve_provider(agent)
    query_embedding = await get_embedding(query, provider=provider)
    return await vector_store.search(agent.id, query_embedding, k=k)


async def retrieve_texts(agent, query: str, k: int = 8) -> list[str]:
    """Convenience wrapper returning just the chunk contents as strings."""
    hits = await retrieve(agent, query, k=k)
    return [h.content for h in hits]
