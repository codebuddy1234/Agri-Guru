"""Importing every model here ensures they are all registered on Base.metadata
before Alembic autogenerate runs — a model that is never imported is silently
left out of migrations."""

from app.database.models.crop_prediction import CropPrediction
from app.database.models.enums import AreaUnit, Language, UserRole
from app.database.models.farm import Farm
from app.database.models.farmer_profile import FarmerProfile
from app.database.models.user import User

__all__ = [
    "AreaUnit",
    "CropPrediction",
    "Farm",
    "FarmerProfile",
    "Language",
    "User",
    "UserRole",
]
