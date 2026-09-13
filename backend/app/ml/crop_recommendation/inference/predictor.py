"""Crop recommendation inference.

Loaded once at application startup and reused for every request. Reloading
the artifacts per request would add ~100ms of pure waste and defeat the
purpose of persisting them at all.

If the artifacts are missing or inconsistent, loading raises and the
application still starts: /health reports the model as unavailable and the
predict endpoint returns a clean 503, while login, profile and history keep
working. A broken model file must not take the whole platform down.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.core.exceptions import ModelUnavailableError, PredictionFailedError
from app.ml.crop_recommendation.schema import FEATURE_ORDER, MODEL_NAME

logger = logging.getLogger(__name__)

#: How many crops to return in the ranked alternatives list.
TOP_K = 3

#: Alternatives below this probability are dropped rather than shown as
#: "0%" options, which would read as a recommendation the model did not make.
MIN_ALTERNATIVE_PROBABILITY = 1e-4


@dataclass(frozen=True)
class CropCandidate:
    crop: str
    probability: float


@dataclass(frozen=True)
class PredictionResult:
    recommended_crop: str
    confidence: float | None
    alternatives: list[CropCandidate]
    model_name: str
    model_version: str


class CropRecommendationPredictor:
    """Wraps the trained pipeline and its artifacts."""

    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir
        self._model: Any = None
        self._label_encoder: Any = None
        self._metadata: dict[str, Any] = {}
        self._loaded = False
        self._load_error: str | None = None

    # --- lifecycle ---

    def load(self) -> None:
        """Load artifacts. Raises on failure; callers decide whether that is fatal."""
        model_path = self.artifacts_dir / "model.joblib"
        encoder_path = self.artifacts_dir / "label_encoder.joblib"
        metadata_path = self.artifacts_dir / "metadata.json"

        missing = [p.name for p in (model_path, encoder_path, metadata_path) if not p.exists()]
        if missing:
            raise FileNotFoundError(
                f"Missing model artifacts {missing} in {self.artifacts_dir}. "
                "Run: python -m app.ml.crop_recommendation.training.train"
            )

        self._model = joblib.load(model_path)
        self._label_encoder = joblib.load(encoder_path)
        self._metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        self._verify_feature_contract()

        self._loaded = True
        self._load_error = None
        logger.info(
            "Loaded %s %s (%s), %d classes",
            self._metadata.get("model_name"),
            self._metadata.get("model_version"),
            self._metadata.get("algorithm"),
            len(self._label_encoder.classes_),
        )

    def _verify_feature_contract(self) -> None:
        """The code's feature order and the artifact's must agree exactly.

        If they ever diverge, every prediction is silently wrong - correct
        types, plausible values, no exception, meaningless answers. Checking
        at load time turns that into a startup failure instead.
        """
        artifact_features = tuple(self._metadata.get("feature_names", ()))
        if artifact_features != FEATURE_ORDER:
            raise ValueError(
                "Feature order mismatch between code and model artifact. "
                f"Code expects {FEATURE_ORDER}, artifact was trained on "
                f"{artifact_features}. Refusing to serve predictions - retrain "
                "the model or restore the matching artifact."
            )
        if not hasattr(self._model, "predict_proba"):
            raise ValueError(
                f"Model {type(self._model).__name__} has no predict_proba. "
                "The API contract requires ranked alternatives."
            )

    def try_load(self) -> bool:
        """Load without raising. Used at startup so a bad artifact degrades
        one feature instead of preventing the app from booting."""
        try:
            self.load()
            return True
        except Exception as exc:  # noqa: BLE001 - deliberately broad at the boundary
            self._loaded = False
            self._load_error = str(exc)
            logger.error("Crop recommendation model unavailable: %s", exc)
            return False

    # --- introspection ---

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def model_version(self) -> str:
        return str(self._metadata.get("model_version", "unknown"))

    @property
    def model_name(self) -> str:
        return str(self._metadata.get("model_name", MODEL_NAME))

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata

    def health(self) -> dict[str, Any]:
        if not self._loaded:
            return {"status": "unavailable", "reason": self._load_error}
        return {
            "status": "available",
            "model_name": self.model_name,
            "model_version": self.model_version,
            "algorithm": self._metadata.get("algorithm"),
            "trained_at": self._metadata.get("trained_at"),
        }

    # --- prediction ---

    def predict(self, features: dict[str, float]) -> PredictionResult:
        """Predict from a {feature_name: value} mapping.

        The feature vector is assembled by explicit name lookup against
        FEATURE_ORDER, never by relying on dict insertion order. Positional
        assembly is how a refactor elsewhere turns into confidently wrong
        predictions with no error raised.
        """
        if not self._loaded:
            raise ModelUnavailableError()

        missing = [name for name in FEATURE_ORDER if name not in features]
        if missing:
            raise PredictionFailedError(f"Missing feature values: {missing}")

        try:
            vector = np.array(
                [[float(features[name]) for name in FEATURE_ORDER]], dtype=np.float64
            )
        except (TypeError, ValueError) as exc:
            raise PredictionFailedError("Feature values must be numeric.") from exc

        if not np.isfinite(vector).all():
            raise PredictionFailedError("Feature values must be finite numbers.")

        try:
            probabilities = self._model.predict_proba(vector)[0]
        except Exception as exc:  # noqa: BLE001
            logger.exception("Prediction failed")
            raise PredictionFailedError() from exc

        ranked_idx = np.argsort(probabilities)[::-1]
        ranked = [
            CropCandidate(
                crop=str(self._label_encoder.inverse_transform([int(i)])[0]),
                probability=round(float(probabilities[i]), 4),
            )
            for i in ranked_idx[:TOP_K]
        ]

        top = ranked[0]
        alternatives = [
            c for c in ranked[1:] if c.probability >= MIN_ALTERNATIVE_PROBABILITY
        ]

        return PredictionResult(
            recommended_crop=top.crop,
            confidence=top.probability,
            alternatives=alternatives,
            model_name=self.model_name,
            model_version=self.model_version,
        )


#: Module-level singleton, populated by the FastAPI lifespan handler.
_predictor: CropRecommendationPredictor | None = None


def init_predictor(artifacts_dir: Path) -> CropRecommendationPredictor:
    global _predictor
    _predictor = CropRecommendationPredictor(artifacts_dir)
    _predictor.try_load()
    return _predictor


def get_predictor() -> CropRecommendationPredictor:
    if _predictor is None:
        raise ModelUnavailableError("The prediction service is not initialised.")
    return _predictor
