"""Modelos y enums para sitios históricos y sus etiquetas."""

from src.core.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, String, UniqueConstraint, Table, Column, Integer, ForeignKey
from datetime import datetime, timezone
from geoalchemy2.types import Geometry
from geoalchemy2.shape import to_shape
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship

class SiteHistory(Base):
    """Modelo base para un sitio Historico."""

    __tablename__ = "site_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=True)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def to_dict(self) -> dict:
        """Devuelvo el evento listo para serializar en JSON."""
        return {
            "id": self.id,
            "site_id": self.site_id,
            "user_id": self.user_id,
            "action_type": self.action_type,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

# Tabla relacion entre sitios y etiquetas
site_tag_association = Table(
    'site_tag_association',
    Base.metadata,
    Column('site_id', Integer, ForeignKey('historic_sites.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('site_tags.id'), primary_key=True)
)

class ConservationStatus(str, Enum):
    """Defino los posibles estados de conservación de un sitio."""

    GOOD = "Bueno"
    REGULAR = "Regular" 
    BAD = "Malo"

class SiteCategory(str, Enum):
    """Enumero las categorías de sitios históricos disponibles."""

    ARCHITECTURE = "Arquitectura"
    INFRASTRUCTURE = "Infraestructura"
    ARCHAEOLOGICAL = "Sitio arqueológico"
    OTRO = "Otro" 

class Historic_Site(Base):
    """Modelo base de un sitio histórico."""

    __tablename__ = "historic_sites"
    __table_args__ = (UniqueConstraint("name", name="uq_historic_sites_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_description: Mapped[str] = mapped_column(String(255), nullable=False)
    full_description: Mapped[str] = mapped_column(String(2000), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    province: Mapped[str] = mapped_column(String(120), nullable=False)
    location: Mapped[str] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=False)
    conservation_status: Mapped[ConservationStatus] = mapped_column(
        SQLAlchemyEnum(ConservationStatus), nullable=False
    )
    inaguration_year: Mapped[int] = mapped_column(nullable=True)
    category: Mapped[SiteCategory] = mapped_column(
        SQLAlchemyEnum(SiteCategory), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    is_visible: Mapped[bool] = mapped_column(default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    tags = relationship("SiteTag", secondary=site_tag_association, back_populates="sites") # type: ignore

    def to_dict(self) -> dict:
        """Armo un dict con los datos del sitio listo para APIs."""
        return {
            "id": self.id,
            "name": self.name,
            "short_description": self.short_description,
            "full_description": self.full_description,
            "city": self.city,
            "province": self.province,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "conservation_status": self.conservation_status,
            "inaguration_year": self.inaguration_year,
            "category": self.category,
            "is_visible": self.is_visible,
            "tags": [tag.name for tag in self.tags],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    # Inversion entre latitud longitud con postgis
    @property
    def latitude(self) -> float:
        """Expongo la latitud calculada desde la geometría."""
        if self.location:
            point = to_shape(self.location)
            return point.y # latitude
        return None

    @property
    def longitude(self) -> float:
        """Expongo la longitud calculada desde la geometría."""
        if self.location:
            point = to_shape(self.location)
            return point.x # longitud
        return None

# Modelo para etiquetas
class SiteTag(Base):
    """Modelo base para una etiqueta de sitio histórico."""

    __tablename__ = "site_tags"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_site_tags_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relación con sitios
    sites = relationship("Historic_Site", secondary=site_tag_association, back_populates="tags")
