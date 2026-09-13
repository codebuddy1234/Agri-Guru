"""farms — 1:N from a farmer profile.

Optional in Phase 1: a farmer can get a recommendation without registering a
farm, so crop_predictions.farm_id is nullable.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.models.enums import AreaUnit

if TYPE_CHECKING:
    from app.database.models.crop_prediction import CropPrediction
    from app.database.models.farmer_profile import FarmerProfile


class Farm(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "farms"
    __table_args__ = (
        CheckConstraint("area_value > 0", name="ck_farms_area_positive"),
    )

    farmer_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmer_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Area is value + unit, never a bare number: see AreaUnit.
    area_value: Mapped[float] = mapped_column(Float, nullable=False)
    area_unit: Mapped[AreaUnit] = mapped_column(
        Enum(AreaUnit, name="area_unit", values_callable=lambda e: [m.value for m in e]),
        default=AreaUnit.ACRE,
        nullable=False,
    )

    # Free text in Phase 1: the trained model does not use soil type or
    # irrigation, so constraining them now would be inventing a taxonomy the
    # system cannot yet act on. They become enums when a module consumes them.
    soil_type: Mapped[str | None] = mapped_column(String(60))
    irrigation_source: Mapped[str | None] = mapped_column(String(60))

    village: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    farmer_profile: Mapped["FarmerProfile"] = relationship(back_populates="farms")
    predictions: Mapped[list["CropPrediction"]] = relationship(back_populates="farm")

    def __repr__(self) -> str:
        return f"<Farm {self.name} {self.area_value}{self.area_unit.value}>"
