"""GithubAccount model — tracks GitHub users flagged by the pipeline."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GithubAccount(Base):
    __tablename__ = "github_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_username: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    flag_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    account_status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    # "active" | "banned"
    banned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<GithubAccount username={self.github_username!r} "
            f"flags={self.flag_count} status={self.account_status}>"
        )
