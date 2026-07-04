"""Read-only PR event log endpoints.

Events are scoped to agents owned by the current user. Supports filtering by
agent, decision, layer, date range, with pagination — enough for the Phase 1 dashboard and the
richer Phase 4 view.
"""
from datetime import datetime
from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DBSession
from app.models.agent import Agent
from app.models.pr_event import PREvent
from app.models.pr_processing_status import PRProcessingStatus
from app.schemas.event import PREventRead

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=list[PREventRead])
async def list_events(
    current_user: CurrentUser,
    db: DBSession,
    agent_id: int | None = Query(default=None, description="Filter to one agent"),
    decision: str | None = Query(
        default=None, description="approved | declined | error"
    ),
    layer_caught: str | None = Query(
        default=None, description="Filter by layer that caught the PR (spam, malicious_code, hijack_proof, summary)"
    ),
    start_date: str | None = Query(default=None, description="Filter events from this date onwards (ISO format)"),
    end_date: str | None = Query(default=None, description="Filter events up to this date (ISO format)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PREvent]:
    stmt = (
        select(PREvent)
        .join(Agent, Agent.id == PREvent.agent_id)
        .where(Agent.user_id == current_user.id)
        .order_by(PREvent.created_at.desc())
    )
    if agent_id is not None:
        stmt = stmt.where(PREvent.agent_id == agent_id)
    if decision is not None:
        stmt = stmt.where(PREvent.decision == decision)
    if layer_caught is not None:
        stmt = stmt.where(PREvent.layer_caught == layer_caught)
    if start_date is not None:
        try:
            start_dt = datetime.fromisoformat(start_date)
            stmt = stmt.where(PREvent.created_at >= start_dt)
        except ValueError:
            pass  # Invalid date format, ignore filter
    if end_date is not None:
        try:
            end_dt = datetime.fromisoformat(end_date)
            stmt = stmt.where(PREvent.created_at <= end_dt)
        except ValueError:
            pass  # Invalid date format, ignore filter
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/count", response_model=int)
async def count_events(
    current_user: CurrentUser,
    db: DBSession,
    agent_id: int | None = Query(default=None),
    decision: str | None = Query(default=None),
    layer_caught: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> int:
    stmt = (
        select(func.count(PREvent.id))
        .join(Agent, Agent.id == PREvent.agent_id)
        .where(Agent.user_id == current_user.id)
    )
    if agent_id is not None:
        stmt = stmt.where(PREvent.agent_id == agent_id)
    if decision is not None:
        stmt = stmt.where(PREvent.decision == decision)
    if layer_caught is not None:
        stmt = stmt.where(PREvent.layer_caught == layer_caught)
    if start_date is not None:
        try:
            start_dt = datetime.fromisoformat(start_date)
            stmt = stmt.where(PREvent.created_at >= start_dt)
        except ValueError:
            pass
    if end_date is not None:
        try:
            end_dt = datetime.fromisoformat(end_date)
            stmt = stmt.where(PREvent.created_at <= end_dt)
        except ValueError:
            pass
    return int(await db.scalar(stmt) or 0)


@router.get("/processing-status", response_model=list[dict])
async def list_processing_status(
    current_user: CurrentUser,
    db: DBSession,
    agent_id: int | None = Query(default=None, description="Filter to one agent"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    """Get real-time processing status for PRs currently being processed."""
    stmt = (
        select(PRProcessingStatus)
        .join(Agent, Agent.id == PRProcessingStatus.agent_id)
        .where(Agent.user_id == current_user.id)
        .order_by(PRProcessingStatus.detected_at.desc())
    )
    if agent_id is not None:
        stmt = stmt.where(PRProcessingStatus.agent_id == agent_id)
    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    statuses = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "agent_id": s.agent_id,
            "pr_number": s.pr_number,
            "pr_url": s.pr_url,
            "pr_title": s.pr_title,
            "author_github": s.author_github,
            "status": s.status,
            "layer_results": s.layer_results,
            "final_decision": s.final_decision,
            "decline_reason": s.decline_reason,
            "error_message": s.error_message,
            "detected_at": s.detected_at.isoformat() if s.detected_at else None,
            "queued_at": s.queued_at.isoformat() if s.queued_at else None,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        }
        for s in statuses
    ]
