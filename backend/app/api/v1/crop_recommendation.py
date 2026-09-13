"""Crop recommendation routes.

The route does four things: take a validated schema, call the service, shape
the response, return it. No scikit-learn import, no session handling, no
business rules - those all live one layer down.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.v1.deps import CurrentFarmer, DbSession, Predictor
from app.schemas.common import envelope
from app.schemas.crop import CropPredictionRequest
from app.services.crop_recommendation_service import CropRecommendationService

router = APIRouter(prefix="/crop-recommendation", tags=["crop recommendation"])


def _prediction_payload(prediction: Any, flagged: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": str(prediction.id),
        "recommended_crop": prediction.recommended_crop,
        "confidence": float(prediction.confidence) if prediction.confidence is not None else None,
        "alternatives": prediction.alternatives,
        "model_name": prediction.model_name,
        "model_version": prediction.model_version,
        "created_at": prediction.created_at.isoformat(),
        "inputs": CropRecommendationService.inputs_of(prediction),
        "out_of_training_range": flagged or [],
    }


@router.post("/predict", summary="Recommend a crop from soil and weather values")
def predict(
    payload: CropPredictionRequest,
    user: CurrentFarmer,
    session: DbSession,
    predictor: Predictor,
) -> dict[str, Any]:
    service = CropRecommendationService(session, predictor)
    prediction, flagged = service.predict_and_save(user.id, payload)
    return envelope({"prediction": _prediction_payload(prediction, flagged)})


@router.get("/history", summary="Past recommendations, newest first")
def history(
    user: CurrentFarmer,
    session: DbSession,
    predictor: Predictor,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    service = CropRecommendationService(session, predictor)
    items, total = service.list_history(user.id, limit=limit, offset=offset)
    return {
        "success": True,
        "data": [
            {
                "id": str(p.id),
                "recommended_crop": p.recommended_crop,
                "confidence": float(p.confidence) if p.confidence is not None else None,
                "model_version": p.model_version,
                "created_at": p.created_at.isoformat(),
            }
            for p in items
        ],
        "meta": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total,
        },
    }


@router.get("/history/{prediction_id}", summary="One past recommendation in full")
def history_detail(
    prediction_id: uuid.UUID,
    user: CurrentFarmer,
    session: DbSession,
    predictor: Predictor,
) -> dict[str, Any]:
    service = CropRecommendationService(session, predictor)
    prediction = service.get_prediction(user.id, prediction_id)
    return envelope({"prediction": _prediction_payload(prediction)})


@router.get("/model-info", summary="Which model is currently serving predictions")
def model_info(user: CurrentFarmer, predictor: Predictor) -> dict[str, Any]:
    """Exposed so the UI can show provenance honestly, and so the training
    caveat travels with the numbers instead of being lost in a README."""
    meta = predictor.metadata
    return envelope(
        {
            "model_name": predictor.model_name,
            "model_version": predictor.model_version,
            "algorithm": meta.get("algorithm"),
            "trained_at": meta.get("trained_at"),
            "n_classes": len(meta.get("classes", [])),
            "crops": meta.get("classes", []),
            "metrics": meta.get("metrics", {}),
            "caveat": meta.get("caveat"),
            "input_ranges": meta.get("input_ranges", {}),
        }
    )
