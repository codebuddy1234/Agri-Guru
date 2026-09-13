"""Single source of truth for the crop recommendation feature contract.

Feature order lives here and in metadata.json, and the predictor asserts the
two agree at load time. A silent feature reorder produces confident wrong
answers with no error anywhere — it is the most expensive bug available in
this kind of system, so it gets a dedicated guard rather than a convention.

Validation bounds are also defined here. `TRAINING_RANGE` is what the model
actually saw (taken from the dataset). `ACCEPTED_RANGE` is what the API
accepts: wider, covering physically plausible values. A value inside
ACCEPTED_RANGE but outside TRAINING_RANGE is accepted and flagged — the model
is extrapolating and the farmer deserves to be told, rather than receiving a
confident answer from a region the model has never seen.
"""

from __future__ import annotations

from dataclasses import dataclass

MODEL_NAME = "crop_recommendation"
TARGET_NAME = "label"

#: Order is contractual. Never reorder — append only, and bump the model version.
FEATURE_ORDER: tuple[str, ...] = (
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall",
)


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    api_field: str
    unit: str
    training_min: float
    training_max: float
    accepted_min: float
    accepted_max: float


#: training_* values are the observed min/max in Crop_recommendation.csv.
#: accepted_* are physically plausible bounds, widened where the dataset is
#: narrower than reality (temperature, rainfall) and clamped to physical
#: limits where reality is narrower (humidity, ph).
FEATURE_SPECS: dict[str, FeatureSpec] = {
    "N": FeatureSpec("N", "nitrogen", "ratio", 0.0, 140.0, 0.0, 200.0),
    "P": FeatureSpec("P", "phosphorus", "ratio", 5.0, 145.0, 0.0, 200.0),
    "K": FeatureSpec("K", "potassium", "ratio", 5.0, 205.0, 0.0, 250.0),
    "temperature": FeatureSpec("temperature", "temperature", "°C", 8.83, 43.68, 0.0, 55.0),
    "humidity": FeatureSpec("humidity", "humidity", "%", 14.26, 99.98, 0.0, 100.0),
    "ph": FeatureSpec("ph", "ph", "pH", 3.50, 9.94, 0.0, 14.0),
    "rainfall": FeatureSpec("rainfall", "rainfall", "mm", 20.21, 298.56, 0.0, 500.0),
}

#: API request field name -> dataset feature name.
API_FIELD_TO_FEATURE: dict[str, str] = {
    spec.api_field: spec.name for spec in FEATURE_SPECS.values()
}


def out_of_training_range(features: dict[str, float]) -> list[str]:
    """Return the API field names whose values sit outside what the model was
    trained on. Accepted, but reported to the caller."""
    flagged = []
    for name, value in features.items():
        spec = FEATURE_SPECS.get(name)
        if spec and not (spec.training_min <= value <= spec.training_max):
            flagged.append(spec.api_field)
    return flagged
