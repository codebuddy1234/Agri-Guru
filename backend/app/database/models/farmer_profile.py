"""farmer_profiles — 1:1 with a user whose role is 'farmer'.

Location is stored as structured district/taluka/village columns rather than
free text: the weather and market modules will need to join on district, and
retrofitting structure onto free text later is painful. PostGIS is not
introduced in Phase 1 — two float columns cover the need and can be migrated
to a geography type if proximity queries ever appear.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.models.enums import Language

if TYPE_CHECKING:
    from app.database.models.crop_prediction import CropPrediction
    from app.database.models.farm import Farm
    from app.database.models.user import User


class FarmerProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "farmer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    preferred_language: Mapped[Language] = mapped_column(
        Enum(Language, name="language", values_callable=lambda e: [m.value for m in e]),
        default=Language.MARATHI,
        nullable=False,
    )

    state: Mapped[str | None] = mapped_column(String(80), default="Maharashtra")
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    taluka: Mapped[str | None] = mapped_column(String(80))
    village: Mapped[str | None] = mapped_column(String(120))
    pincode: Mapped[str | None] = mapped_column(String(10))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    user: Mapped["User"] = relationship(back_populates="farmer_profile")
    farms: Mapped[list["Farm"]] = relationship(
        back_populates="farmer_profile", cascade="all, delete-orphan"
    )
    predictions: Mapped[list["CropPrediction"]] = relationship(
        back_populates="farmer_profile", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FarmerProfile {self.full_name}>"
