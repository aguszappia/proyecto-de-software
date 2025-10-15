"""Modelos para manejar los feature flags de la app."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, Text, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.core.users.models import User


class FeatureFlag(Base):
    """Modelo base de un featureFlag."""

    __tablename__ = "feature_flags"
    __table_args__ = (UniqueConstraint("key", name="uq_feature_flags_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    message: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    updated_by: Mapped[User | None] = relationship("User")

    def __repr__(self) -> str:
        return f"<FeatureFlag key={self.key} enabled={self.enabled}>"
