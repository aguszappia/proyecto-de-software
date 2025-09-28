from src.core.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, String, UniqueConstraint
from datetime import datetime, timezone
from geoalchemy2.types import Geometry
from geoalchemy2.shape import to_shape

class Historic_Site(Base):
    """Represents an historic site"""

    __tablename__ = "historic_sites"
    __table_args__ = (UniqueConstraint("name", name="uq_historic_sites_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    province: Mapped[str] = mapped_column(String(120), nullable=False)
    location: Mapped[str] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=False)
    # estado de conservacion
    year: Mapped[int] = mapped_column(nullable=True)
    # categoria
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

# Inversion entre latitud longitud con postgis
@property
def latitude(self) -> float:
    """Returns the latitude of the location."""
    if self.location:
        point = to_shape(self.location)
        return point.y # latitude
    return None

@property
def longitude(self) -> float:
    """Returns the longitude of the location."""
    if self.location:
        point = to_shape(self.location)
        return point.x # longitud
    return None

# COMPLETAR con campos que faltan
def to_dict(self) -> dict:
    return {
        "id": self.id,
        "name": self.name,
        "description": self.description,
        "city": self.city,
        "province": self.province,
        "latitude": self.latitude,
        "longitude": self.longitude,
        "year": self.year,
        "created_at": self.created_at.isoformat() if self.created_at else None,
        "updated_at": self.updated_at.isoformat() if self.updated_at else None,
    }