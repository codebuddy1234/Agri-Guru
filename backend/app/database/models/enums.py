"""Enumerations shared by the ORM models and the Pydantic schemas.

Defined once here so a value can never drift between the database
constraint and the API contract.
"""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    FARMER = "farmer"
    EXPERT = "expert"
    ADMIN = "admin"


class Language(str, enum.Enum):
    MARATHI = "mr"
    HINDI = "hi"
    ENGLISH = "en"


class AreaUnit(str, enum.Enum):
    """Maharashtra farmers commonly use acre and guntha; forcing hectares at
    input is a reliable way to collect silently wrong data."""

    ACRE = "acre"
    HECTARE = "hectare"
    GUNTHA = "guntha"
