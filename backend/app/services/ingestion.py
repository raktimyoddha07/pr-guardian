"""RAG ingestion.

Fetches every text file (via the git tree + blobs) and every issue (with
comments) from the agent's repo, chunks everything, embeds it, and stores it in
the ``KnowledgeChunk`` table (pgvector). Tracks progress on the Agent row:
``ingestion_status`` pending → running → done|failed, plus ``last_ingested_at``
and ``chunk_count``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import update

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.agent import Agent
from app.services.chunker import chunk_text, estimate_tokens
from app.services.github import GithubError, github_client
from app.services.llm import get_embedding, resolve_provider
from app.services.vectorstore import vector_store

logger = logging.getLogger(__name__)


def _is_text_path(path: str) -> bool:
    if not path:
        return False
    lower = path.lower()
    # Filename-based matches (e.g. Dockerfile, .gitignore).
    basename = lower.rsplit("/", 1)[-1]
    name_hits = {"dockerfile", "license", "readme", "makefile", ".gitignore",
                 ".gitattributes", ".env.example", "requirements.txt"}
    if basename in name_hits:
        return True
    allowed = {ext.strip() for ext in settings.INGESTION_TEXT_EXTS.split(",") if ext.strip()}
    # Match by extension, including dotfiles.
    for ext in allowed:
        if lower.endswith(ext):
            return True
    return False


async def _fetch_repo_chunks(
    repo_full_name: str, branch: str | None, provider: str
) -> list[tuple[str, str, list[float]]]:
    """Return (source_ref, content, embedding) triples for all repo files."""
    blobs = await github_client.get_tree_blobs(repo_full_name, branch=branch)

    triples: list[tuple[str, str, list[float]]] = []
    processed = 0
    for blob in blobs[: settings.INGESTION_MAX_FILES]:
        path = blob.get("path", "")
        size = int(blob.get("size", 0) or 0)
        if not _is_text_path(path) or size == 0 or size > settings.INGESTION_MAX_FILE_BYTES:
            continue
        sha = blob.get("sha")
        if not sha:
            continue
        try:
            content = await github_client.get_blob_content(repo_full_name, sha)
        except GithubError as exc:
            logger.warning("ingestion: skip %s (%s)", path, exc)
            continue

        for chunk in chunk_text(content):
            text = f"# file: {path}\n{chunk.text}"
            embedding = await get_embedding(text, provider=provider)  # type: ignore[arg-type]
            triples.append((path, text, embedding))
        processed += 1

    logger.info("ingestion[repo]: %s files → %s chunks", processed, len(triples))
    return triples


async def _fetch_issue_chunks(
    repo_full_name: str, provider: str
) -> list[tuple[str, str, list[float]]]:
    """Return (source_ref, content, embedding) triples for issues + comments."""
    issues = await github_client.list_issues(repo_full_name, state="all")
    # GitHub's issues endpoint also returns PRs; filter PRs out.
    issues = [i for i in issues if "pull_request" not in i]

    triples: list[tuple[str, str, list[float]]] = []
    for issue in issues:
        number = issue.get("number")
        title = issue.get("title") or ""
        body = issue.get("body") or ""
        state = issue.get("state") or "open"
        ref = f"issues/{number}"

        try:
            comments = await github_client.get_issue_comments(repo_full_name, number)
        except GithubError:
            comments = []
        comment_bodies = [c.get("body") or "" for c in comments]

        text = f"# issue #{number} [{state}]: {title}\n\n{body}"
        if comment_bodies:
            text += "\n\n## comments\n" + "\n\n---\n\n".join(comment_bodies)

        for chunk in chunk_text(text):
            embedding = await get_embedding(chunk.text, provider=provider)  # type: ignore[arg-type]
            triples.append((ref, chunk.text, embedding))

    logger.info("ingestion[issues]: %s issues → %s chunks", len(issues), len(triples))
    return triples


async def _set_status(
    agent_id: int,
    status: str,
    *,
    chunk_count: int | None = None,
    last_ingested_at: datetime | None = None,
) -> None:
    values: dict = {"ingestion_status": status}
    if chunk_count is not None:
        values["chunk_count"] = chunk_count
    if last_ingested_at is not None:
        values["last_ingested_at"] = last_ingested_at
    async with AsyncSessionLocal() as db:
        await db.execute(update(Agent).where(Agent.id == agent_id).values(**values))
        await db.commit()


async def ingest_agent(agent_id: int) -> int:
    """Run a full ingestion for an agent. Returns the chunk count stored."""
    async with AsyncSessionLocal() as db:
        agent = await db.get(Agent, agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        repo_full_name = agent.repo_full_name
        provider = resolve_provider(agent)

    await _set_status(agent_id, "running")
    logger.info("ingestion: start agent=%s repo=%s provider=%s",
                agent_id, repo_full_name, provider)

    try:
        # Reset existing chunks for this agent (idempotent re-sync).
        await vector_store.reset(agent_id)

        repo_triples = await _fetch_repo_chunks(repo_full_name, None, provider)
        issue_triples = await _fetch_issue_chunks(repo_full_name, provider)

        # Embedding already happened per-chunk above; build the store tuples.
        chunks = [
            ("repo", ref, content, embedding) for ref, content, embedding in repo_triples
        ] + [
            ("issue", ref, content, embedding) for ref, content, embedding in issue_triples
        ]

        stored = await vector_store.add(agent_id, chunks)

        await _set_status(
            agent_id,
            "done",
            chunk_count=stored,
            last_ingested_at=datetime.now(timezone.utc),
        )
        logger.info("ingestion: done agent=%s chunks=%s", agent_id, stored)
        return stored
    except Exception as exc:
        logger.exception("ingestion: failed agent=%s: %s", agent_id, exc)
        await _set_status(agent_id, "failed")
        raise
