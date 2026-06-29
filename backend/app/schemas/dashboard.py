"""Dashboard aggregate + flagged-account schemas (Phase 4)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardStats(BaseModel):
    """Aggregate counts for the dashboard summary cards."""

    total_prs: int
    approved: int
    declined: int
    errors: int
    flagged_accounts: int
    banned_accounts: int
    approval_rate: float  # 0.0–1.0


class AgentStats(BaseModel):
    """Per-agent stats entry."""

    model_config = ConfigDict(from_attributes=True)

    agent_id: int
    agent_name: str
    repo_full_name: str
    total_prs: int
    approved: int
    declined: int
    approval_rate: float


class FlaggedAccountRead(BaseModel):
    """A GitHub account flagged by one of the current user's agents."""

    model_config = ConfigDict(from_attributes=True)

    github_username: str
    flag_count: int
    account_status: str
    banned_at: datetime | None
    first_seen: datetime
    updated_at: datetime
