"""GitHub webhook receiver.

Validates the ``X-Hub-Signature-256`` header with HMAC-SHA256, then routes
valid ``pull_request`` events (actions ``opened`` / ``synchronize``) to a
background task that runs the full LangGraph pipeline. Per AGENTS.md the
webhook must respond within 10 seconds, so all pipeline work happens out-of-band.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from app.core.config import settings
from app.pipeline.runner import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# PR actions we treat as "review this PR".
HANDLED_PR_ACTIONS = {"opened", "synchronize"}


def _verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Constant-time HMAC-SHA256 verification of the GitHub webhook signature."""
    if not signature_header:
        return False
    try:
        algo, delivered = signature_header.split("=", 1)
    except ValueError:
        return False
    if algo != "sha256":
        return False
    expected = hmac.new(
        key=settings.GITHUB_WEBHOOK_SECRET.encode(),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(delivered, expected)


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> dict[str, str]:
    raw_body = await request.body()

    # 1. Validate the signature before any processing.
    if not _verify_signature(raw_body, x_hub_signature_256):
        logger.warning("webhook: invalid signature, rejecting")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # 2. Only act on pull_request events.
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"event {x_github_event!r} not handled"}

    try:
        payload: dict[str, Any] = await request.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body"
        ) from exc

    action = payload.get("action")
    if action not in HANDLED_PR_ACTIONS:
        return {"status": "ignored", "reason": f"action {action!r} not handled"}

    pr = payload.get("pull_request") or {}
    repo = payload.get("repository") or {}
    repo_full_name = repo.get("full_name")
    if not repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing repository.full_name",
        )

    pr_number = pr.get("number")
    pr_url = pr.get("html_url") or ""
    author = ((pr.get("user") or {}).get("login")) or "unknown"
    if not pr_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing pull_request.number",
        )

    # 3. Dispatch — do NOT block the webhook response.
    background_tasks.add_task(
        run_pipeline,
        repo_full_name=repo_full_name,
        pr_number=int(pr_number),
        pr_url=pr_url,
        author=author,
    )
    return {"status": "accepted", "pr_number": str(pr_number)}
