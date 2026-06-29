"""Pipeline runner — the entrypoint the webhook calls.

``run_pipeline`` fetches the full PR + diff from GitHub, builds the initial
``PRState``, runs the LangGraph pipeline, and records an error event if
anything blows up. Fully async end-to-end.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.agent import Agent
from app.models.pr_event import PREvent
from app.pipeline.graph import pipeline
from app.pipeline.state import PRState
from app.services.github import GithubError, github_client

logger = logging.getLogger(__name__)


async def _load_agent(repo_full_name: str) -> Agent | None:
    """Return the active agent that owns ``repo_full_name`` (most recent)."""
    async with AsyncSessionLocal() as db:
        return await db.scalar(
            select(Agent)
            .where(Agent.repo_full_name == repo_full_name)
            .where(Agent.is_active.is_(True))
            .order_by(Agent.id.desc())
            .limit(1)
        )


async def _fetch_pr(repo_full_name: str, pr_number: int) -> tuple[str, str, str]:
    """Return (title, body, diff) for the PR. Falls back to empty strings."""
    title = body = diff = ""
    try:
        pr = await github_client.get_pr(repo_full_name, pr_number)
        title = pr.get("title") or ""
        body = pr.get("body") or ""
    except GithubError as exc:
        logger.warning("run_pipeline: get_pr failed (%s)", exc)

    try:
        diff = await github_client.get_pr_diff(repo_full_name, pr_number)
    except GithubError as exc:
        logger.warning("run_pipeline: get_pr_diff failed (%s)", exc)

    return title, body, diff


async def _record_error(agent_id: int, pr_number: int, pr_url: str, author: str, msg: str) -> None:
    async with AsyncSessionLocal() as db:
        db.add(
            PREvent(
                agent_id=agent_id,
                pr_number=pr_number,
                pr_url=pr_url,
                author_github=author,
                decision="error",
                layer_caught=None,
                reason=f"Pipeline error: {msg[:500]}",
            )
        )
        await db.commit()


async def run_pipeline(repo_full_name: str, pr_number: int, pr_url: str, author: str) -> dict:
    """Run the full pipeline for a PR. Returns the final state dict.

    Designed to be called as a background task from the webhook. Never raises
    into the request cycle — failures are recorded as ``decision="error"``.
    """
    logger.info("run_pipeline: start PR #%s on %s by %s", pr_number, repo_full_name, author)

    agent = await _load_agent(repo_full_name)
    if agent is None:
        logger.info("run_pipeline: no agent owns %s, ignoring", repo_full_name)
        return {"status": "ignored", "reason": "no agent owns repo"}

    title, body, diff = await _fetch_pr(repo_full_name, pr_number)

    state: PRState = {
        "agent_id": agent.id,
        "repo_full_name": repo_full_name,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "pr_title": title,
        "pr_body": body,
        "pr_diff": diff,
        "pr_author": author,
        "agent": agent,
        "retrieved_context": [],
        "layer_results": {},
        "final_decision": "approved",
        "decline_reason": None,
        "flag_account": False,
        "summary_title": None,
        "summary_body": None,
    }

    try:
        final_state = await pipeline.ainvoke(state)
        decision = final_state.get("final_decision", "approved")
        logger.info(
            "run_pipeline: done PR #%s decision=%s reason=%s",
            pr_number,
            decision,
            final_state.get("decline_reason"),
        )
        return {"status": "ok", "decision": decision, "state": final_state}
    except Exception as exc:  # noqa: BLE001 — record so it's visible in the dashboard
        logger.exception("run_pipeline: crashed PR #%s: %s", pr_number, exc)
        await _record_error(agent.id, pr_number, pr_url, author, str(exc))
        return {"status": "error", "reason": str(exc)}
