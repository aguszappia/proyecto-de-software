"""User persistence models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.core.users import DEFAULT_USER_ROLE


class Role(Base):
    """Rol de usuario (public, editor, admin, sysadmin)."""

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("slug", name="uq_roles_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    users: Mapped[list["User"]] = relationship("User", back_populates="role_rel")
    permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Role slug={self.slug}>"


class User(Base):
    """Represents an application user."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    role_rel: Mapped[Role] = relationship("Role", back_populates="users")

    @property
    def role(self) -> str:
        if self.role_rel:
            return self.role_rel.slug
        return DEFAULT_USER_ROLE.value

    @property
    def role_name(self) -> str:
        if self.role_rel:
            return self.role_rel.name
        return DEFAULT_USER_ROLE.value

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
