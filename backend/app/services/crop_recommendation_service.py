"""Crop recommendation orchestration.

This is the layer the spec's flow describes:

    route -> validation -> CropRecommendationService -> model -> save -> response

The route knows nothing about scikit-learn; the predictor knows nothing about
the database. This service is the only place the two meet.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.database.models.crop_prediction import CropPrediction
from app.ml.crop_recommendation.inference.predictor import CropRecommendationPredictor
from app.ml.crop_recommendation.schema import (
    API_FIELD_TO_FEATURE,
    FEATURE_SPECS,
    out_of_training_range,
)
from app.schemas.crop import CropPredictionRequest
from app.services.farmer_service import FarmerService

logger = logging.getLogger(__name__)


class CropRecommendationService:
    def __init__(self, session: Session, predictor: CropRecommendationPredictor) -> None:
        self.session = session
        self.predictor = predictor
        self.farmer_service = FarmerService(session)

    @staticmethod
    def _to_features(payload: CropPredictionRequest) -> dict[str, float]:
        """Map farmer-facing API field names to dataset feature names."""
        data = payload.model_dump()
        return {
            feature: float(data[api_field])
            for api_field, feature in API_FIELD_TO_FEATURE.items()
        }

    def predict_and_save(
        self, user_id: uuid.UUID, payload: CropPredictionRequest
    ) -> tuple[CropPrediction, list[str]]:
        profile = self.farmer_service.get_profile(user_id)

        # Verify farm ownership before predicting: no point spending the
        # inference if the request is going to be rejected anyway.
        farm_id = None
        if payload.farm_id is not None:
            farm = self.farmer_service.get_owned_farm(user_id, payload.farm_id)
            farm_id = farm.id

        features = self._to_features(payload)
        result = self.predictor.predict(features)
        flagged = out_of_training_range(features)

        if flagged:
            logger.info(
                "Prediction for %s used values outside the training range: %s",
                profile.id,
                flagged,
            )

        prediction = CropPrediction(
            farmer_profile_id=profile.id,
            farm_id=farm_id,
            input_n=features["N"],
            input_p=features["P"],
            input_k=features["K"],
            input_temperature=features["temperature"],
            input_humidity=features["humidity"],
            input_ph=features["ph"],
            input_rainfall=features["rainfall"],
            recommended_crop=result.recommended_crop,
            confidence=result.confidence,
            alternatives=[
                {"crop": c.crop, "probability": c.probability} for c in result.alternatives
            ],
            model_name=result.model_name,
            model_version=result.model_version,
        )
        self.session.add(prediction)
        self.session.commit()
        self.session.refresh(prediction)

        logger.info(
            "Prediction %s: %s (%.4f) via %s",
            prediction.id,
            result.recommended_crop,
            result.confidence or 0.0,
            result.model_version,
        )
        return prediction, flagged

    def list_history(
        self, user_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[CropPrediction], int]:
        profile = self.farmer_service.get_profile(user_id)

        total = self.session.scalar(
            select(func.count())
            .select_from(CropPrediction)
            .where(CropPrediction.farmer_profile_id == profile.id)
        )
        stmt = (
            select(CropPrediction)
            .where(CropPrediction.farmer_profile_id == profile.id)
            .order_by(CropPrediction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt)), int(total or 0)

    def get_prediction(self, user_id: uuid.UUID, prediction_id: uuid.UUID) -> CropPrediction:
        """Scoped to the requesting farmer.

        Another farmer's prediction id returns 404, not 403: a 403 would
        confirm the record exists.
        """
        profile = self.farmer_service.get_profile(user_id)
        stmt = select(CropPrediction).where(
            CropPrediction.id == prediction_id,
            CropPrediction.farmer_profile_id == profile.id,
        )
        prediction = self.session.scalar(stmt)
        if not prediction:
            raise NotFoundError("Recommendation not found.")
        return prediction

    @staticmethod
    def inputs_of(prediction: CropPrediction) -> dict[str, float]:
        """Rebuild the farmer-facing input map from the stored columns."""
        stored = {
            "N": prediction.input_n,
            "P": prediction.input_p,
            "K": prediction.input_k,
            "temperature": prediction.input_temperature,
            "humidity": prediction.input_humidity,
            "ph": prediction.input_ph,
            "rainfall": prediction.input_rainfall,
        }
        return {FEATURE_SPECS[f].api_field: v for f, v in stored.items()}
