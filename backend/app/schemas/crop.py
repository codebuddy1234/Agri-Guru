"""Crop recommendation request/response schemas.

Validation bounds are read from app.ml.crop_recommendation.schema, which is
also what the model metadata is checked against. Hard-coding numbers here
would let the API's idea of a valid value drift from the model's.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ml.crop_recommendation.schema import FEATURE_SPECS

_N = FEATURE_SPECS["N"]
_P = FEATURE_SPECS["P"]
_K = FEATURE_SPECS["K"]
_T = FEATURE_SPECS["temperature"]
_H = FEATURE_SPECS["humidity"]
_PH = FEATURE_SPECS["ph"]
_R = FEATURE_SPECS["rainfall"]

# allow_inf_nan=False makes Pydantic reject NaN and +/-Infinity outright.
# Without it, float("nan") passes every ge/le check silently, because every
# comparison against NaN is False.
Measurement = Annotated[float, Field(allow_inf_nan=False)]


class CropPredictionRequest(BaseModel):
    """The seven model features, named for farmers rather than for the dataset.

    Note on units: N, P and K are the dataset's unitless soil-test ratio
    values. They are NOT kg/ha, and a value copied straight off a soil health
    card will not mean the same thing. The UI states this; the API documents
    it here.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nitrogen": 90,
                "phosphorus": 42,
                "potassium": 43,
                "temperature": 20.9,
                "humidity": 82.0,
                "ph": 6.5,
                "rainfall": 202.9,
            }
        }
    )

    nitrogen: Measurement = Field(
        ge=_N.accepted_min, le=_N.accepted_max, description="Soil nitrogen (ratio value)"
    )
    phosphorus: Measurement = Field(
        ge=_P.accepted_min, le=_P.accepted_max, description="Soil phosphorus (ratio value)"
    )
    potassium: Measurement = Field(
        ge=_K.accepted_min, le=_K.accepted_max, description="Soil potassium (ratio value)"
    )
    temperature: Measurement = Field(
        ge=_T.accepted_min, le=_T.accepted_max, description="Average temperature (°C)"
    )
    humidity: Measurement = Field(
        ge=_H.accepted_min, le=_H.accepted_max, description="Relative humidity (%)"
    )
    ph: Measurement = Field(
        ge=_PH.accepted_min, le=_PH.accepted_max, description="Soil pH (0–14)"
    )
    rainfall: Measurement = Field(
        ge=_R.accepted_min, le=_R.accepted_max, description="Rainfall (mm)"
    )

    farm_id: uuid.UUID | None = Field(
        default=None, description="Optional: link this prediction to a registered farm"
    )

    @field_validator(
        "nitrogen", "phosphorus", "potassium", "temperature", "humidity", "ph", "rainfall"
    )
    @classmethod
    def _finite(cls, v: float) -> float:
        # Belt and braces alongside allow_inf_nan=False.
        if not math.isfinite(v):
            raise ValueError("Value must be a finite number.")
        return v


class CropCandidateOut(BaseModel):
    crop: str
    probability: float


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recommended_crop: str
    confidence: float | None
    alternatives: list[CropCandidateOut]
    model_name: str
    model_version: str
    created_at: datetime

    #: API field names whose values sit outside the model's training range.
    #: Accepted, but the caller is told the model is extrapolating.
    out_of_training_range: list[str] = []

    inputs: dict[str, float] = {}


class PredictionHistoryItem(BaseModel):
    """Deliberately lighter than PredictionOut: the history list does not need
    every input value, and sending them makes the list needlessly heavy on a
    slow connection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recommended_crop: str
    confidence: float | None
    model_version: str
    created_at: datetime


class PredictionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recommended_crop: str
    confidence: float | None
    alternatives: list[dict[str, Any]]
    model_name: str
    model_version: str
    created_at: datetime
    inputs: dict[str, float]
    farm_id: uuid.UUID | None
