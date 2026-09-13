"""Farmer profile and farm routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from app.api.v1.deps import CurrentFarmer, DbSession
from app.schemas.common import envelope
from app.schemas.farmer import FarmCreate, FarmerProfileOut, FarmerProfileUpdate, FarmOut
from app.services.farmer_service import FarmerService

router = APIRouter(prefix="/farmer", tags=["farmer"])


@router.get("/profile", summary="Get the signed-in farmer's profile")
def get_profile(user: CurrentFarmer, session: DbSession) -> dict[str, Any]:
    profile = FarmerService(session).get_profile(user.id)
    return envelope(FarmerProfileOut.model_validate(profile).model_dump(mode="json"))


@router.put("/profile", summary="Update profile (partial)")
def update_profile(
    payload: FarmerProfileUpdate, user: CurrentFarmer, session: DbSession
) -> dict[str, Any]:
    profile = FarmerService(session).update_profile(user.id, payload)
    return envelope(FarmerProfileOut.model_validate(profile).model_dump(mode="json"))


@router.get("/farms", summary="List the farmer's farms")
def list_farms(user: CurrentFarmer, session: DbSession) -> dict[str, Any]:
    farms = FarmerService(session).list_farms(user.id)
    return envelope([FarmOut.model_validate(f).model_dump(mode="json") for f in farms])


@router.post("/farms", status_code=status.HTTP_201_CREATED, summary="Add a farm")
def create_farm(
    payload: FarmCreate, user: CurrentFarmer, session: DbSession
) -> dict[str, Any]:
    farm = FarmerService(session).create_farm(user.id, payload)
    return envelope(FarmOut.model_validate(farm).model_dump(mode="json"))
