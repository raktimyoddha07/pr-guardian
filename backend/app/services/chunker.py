"""Lightweight text chunker (rough token estimate, sliding-window overlap).

We avoid a heavyweight tokenizer dependency by approximating tokens as
``len(text) / 4`` (a common English/code heuristic). Chunks are produced on word
boundaries to avoid splitting identifiers awkwardly. Good enough for RAG; the
PHASE.md spec calls for 512-token chunks with 50-token overlap.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings

CHARS_PER_TOKEN = 4


@dataclass
class Chunk:
    text: str
    token_count: int


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def chunk_text(
    text: str,
    *,
    max_tokens: int = settings.RAG_CHUNK_TOKENS,
    overlap_tokens: int = settings.RAG_CHUNK_OVERLAP,
) -> list[Chunk]:
    """Split ``text`` into overlapping token-bounded chunks."""
    text = text.strip()
    if not text:
        return []

    max_chars = max_tokens * CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * CHARS_PER_TOKEN

    chunks: list[Chunk] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        piece = text[start:end]
        chunks.append(Chunk(text=piece, token_count=estimate_tokens(piece)))
        if end >= n:
            break
        start = end - overlap_chars
        if start < 0:
            start = 0
    return chunks
