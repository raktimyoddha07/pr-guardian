"""GitHub Connection model — stores OAuth connections for users."""
from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

ConnectionStatus = Literal["active", "revoked", "expired"]


class GitHubConnection(Base):
    __tablename__ = "github_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    github_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    github_username: Mapped[str] = mapped_column(String(255), nullable=False)
    github_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # OAuth tokens
    access_token: Mapped[str] = mapped_column(String(500), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Installation info (for GitHub App)
    installation_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="github_connections")

    def __repr__(self) -> str:
        return f"<GitHubConnection id={self.id} github_user={self.github_username!r} status={self.status}>"
