"""Read-only PR event log endpoints.

Events are scoped to agents owned by the current user. Supports filtering by
agent and decision, with pagination — enough for the Phase 1 dashboard and the
richer Phase 4 view.
"""
from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DBSession
from app.models.agent import Agent
from app.models.pr_event import PREvent
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
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/count", response_model=int)
async def count_events(
    current_user: CurrentUser,
    db: DBSession,
    agent_id: int | None = Query(default=None),
    decision: str | None = Query(default=None),
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
    return int(await db.scalar(stmt) or 0)
