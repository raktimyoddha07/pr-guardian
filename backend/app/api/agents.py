"""Agent CRUD endpoints: create, list, get, update, delete, sync.

Ownership is enforced: every query scopes agents to the current user.
"""
import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DBSession
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentRead, AgentUpdate
from app.tasks import sync_all_agents_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentRead])
async def list_agents(current_user: CurrentUser, db: DBSession) -> list[Agent]:
    result = await db.execute(
        select(Agent)
        .where(Agent.user_id == current_user.id)
        .order_by(Agent.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> Agent:
    agent = Agent(
        user_id=current_user.id,
        name=payload.name,
        repo_full_name=payload.repo_full_name,
        llm_provider=payload.llm_provider,
        vector_db_type=payload.vector_db_type,
        is_active=True,
        ingestion_status="pending",
    )
    db.add(agent)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create agent (invalid input)",
        ) from exc
    await db.refresh(agent)

    # Kick off ingestion in Celery worker; status is tracked on the agent row.
    # This will also automatically trigger pending PR processing after ingestion completes.
    sync_all_agents_task.delay()
    return agent


async def _get_owned_or_404(db: DBSession, agent_id: int, user_id: int) -> Agent:
    """Fetch an agent owned by ``user_id`` or raise 404."""
    agent = await db.get(Agent, agent_id)
    if agent is None or agent.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )
    return agent


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(
    agent_id: int, current_user: CurrentUser, db: DBSession
) -> Agent:
    return await _get_owned_or_404(db, agent_id, current_user.id)


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: int,
    payload: AgentUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> Agent:
    agent = await _get_owned_or_404(db, agent_id, current_user.id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(agent, field, value)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int, current_user: CurrentUser, db: DBSession
) -> None:
    agent = await _get_owned_or_404(db, agent_id, current_user.id)
    await db.delete(agent)
    await db.commit()


@router.post("/{agent_id}/sync", response_model=AgentRead)
async def sync_agent(
    agent_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> Agent:
    """Trigger a manual re-ingestion of the agent's knowledge base."""
    agent = await _get_owned_or_404(db, agent_id, current_user.id)
    # Trigger ingestion in Celery worker
    sync_all_agents_task.delay()
    # Re-read fresh status without blocking.
    await db.refresh(agent)
    return agent
