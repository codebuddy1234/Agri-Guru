"""Farmer profile and farm operations."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.database.models.farm import Farm
from app.database.models.farmer_profile import FarmerProfile
from app.schemas.farmer import FarmCreate, FarmerProfileUpdate


class FarmerService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_profile(self, user_id: uuid.UUID) -> FarmerProfile:
        stmt = select(FarmerProfile).where(FarmerProfile.user_id == user_id)
        profile = self.session.scalar(stmt)
        if not profile:
            raise NotFoundError("No farmer profile exists for this account.")
        return profile

    def update_profile(
        self, user_id: uuid.UUID, payload: FarmerProfileUpdate
    ) -> FarmerProfile:
        profile = self.get_profile(user_id)
        # exclude_unset: only fields the client actually sent are applied, so
        # a partial update cannot blank out values it never mentioned.
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        self.session.commit()
        self.session.refresh(profile)
        return profile

    def list_farms(self, user_id: uuid.UUID) -> list[Farm]:
        profile = self.get_profile(user_id)
        stmt = (
            select(Farm)
            .where(Farm.farmer_profile_id == profile.id)
            .order_by(Farm.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def create_farm(self, user_id: uuid.UUID, payload: FarmCreate) -> Farm:
        profile = self.get_profile(user_id)
        farm = Farm(farmer_profile_id=profile.id, **payload.model_dump())
        self.session.add(farm)
        self.session.commit()
        self.session.refresh(farm)
        return farm

    def get_owned_farm(self, user_id: uuid.UUID, farm_id: uuid.UUID) -> Farm:
        """Fetch a farm only if it belongs to this farmer.

        Returns 404 rather than 403 for someone else's farm: a 403 would
        confirm the record exists, which is itself a disclosure.
        """
        profile = self.get_profile(user_id)
        stmt = select(Farm).where(Farm.id == farm_id, Farm.farmer_profile_id == profile.id)
        farm = self.session.scalar(stmt)
        if not farm:
            raise NotFoundError("Farm not found.")
        return farm
