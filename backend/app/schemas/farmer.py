"""Farmer profile and farm schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.database.models.enums import AreaUnit, Language


class FarmerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    preferred_language: Language
    state: str | None
    district: str | None
    taluka: str | None
    village: str | None
    pincode: str | None
    latitude: float | None
    longitude: float | None
    created_at: datetime
    updated_at: datetime


class FarmerProfileUpdate(BaseModel):
    """Every field optional: this is a partial update, and an omitted field
    must leave the stored value alone rather than blanking it."""

    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    preferred_language: Language | None = None
    state: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    taluka: str | None = Field(default=None, max_length=80)
    village: str | None = Field(default=None, max_length=120)
    pincode: str | None = Field(default=None, pattern=r"^\d{6}$")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class FarmCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    area_value: float = Field(gt=0, le=100000)
    area_unit: AreaUnit = AreaUnit.ACRE
    soil_type: str | None = Field(default=None, max_length=60)
    irrigation_source: str | None = Field(default=None, max_length=60)
    village: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class FarmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    area_value: float
    area_unit: AreaUnit
    soil_type: str | None
    irrigation_source: str | None
    village: str | None
    latitude: float | None
    longitude: float | None
    created_at: datetime
