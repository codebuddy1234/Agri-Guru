"""crop_predictions — prediction history, and the audit record.

Design notes:

* Inputs are typed columns, not a JSON blob. Phase 1 has a fixed, known
  feature set, so typed columns buy constraints, indexes and simple
  analytics. A future module with variable inputs gets its own table.
* `alternatives` is JSONB: variable-shape, read whole, never queried by key.
  That is exactly the case JSONB is for, and exactly the case typed columns
  are not.
* `model_version` is mandatory on every row. When v2 ships, "which model
  produced this recommendation?" must be answerable for historical rows.
  This column is what makes artifact versioning mean anything.
* `confidence` is nullable by design. If a model without meaningful
  probabilities is ever selected, this stays NULL and the UI omits it
  rather than displaying an invented number.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.farm import Farm
    from app.database.models.farmer_profile import FarmerProfile


class CropPrediction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crop_predictions"
    __table_args__ = (
        Index("ix_crop_predictions_farmer_created", "farmer_profile_id", "created_at"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_crop_predictions_confidence_range",
        ),
    )

    farmer_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmer_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: a farmer may request a recommendation before adding a farm.
    farm_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.id", ondelete="SET NULL"), index=True
    )

    # --- Model inputs, exactly as submitted ---
    input_n: Mapped[float] = mapped_column(Float, nullable=False)
    input_p: Mapped[float] = mapped_column(Float, nullable=False)
    input_k: Mapped[float] = mapped_column(Float, nullable=False)
    input_temperature: Mapped[float] = mapped_column(Float, nullable=False)
    input_humidity: Mapped[float] = mapped_column(Float, nullable=False)
    input_ph: Mapped[float] = mapped_column(Float, nullable=False)
    input_rainfall: Mapped[float] = mapped_column(Float, nullable=False)

    # --- Model output ---
    recommended_crop: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    alternatives: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )

    # --- Provenance ---
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    farmer_profile: Mapped["FarmerProfile"] = relationship(back_populates="predictions")
    farm: Mapped["Farm | None"] = relationship(back_populates="predictions")

    def __repr__(self) -> str:
        return f"<CropPrediction {self.recommended_crop} {self.model_version}>"
