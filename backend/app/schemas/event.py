"""PREvent schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PREventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    pr_number: int
    pr_url: str
    author_github: str
    decision: str
    layer_caught: str | None
    reason: str | None
    created_at: datetime
