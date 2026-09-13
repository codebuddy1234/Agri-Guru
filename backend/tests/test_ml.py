"""ML artifact and inference contract tests.

These guard the failure mode that produces no error at all: a model that
loads, predicts, returns plausible crop names, and is wrong about every one
of them because the feature vector was assembled in the wrong order.
"""

from __future__ import annotations

import json

import pytest

from app.core.config import get_settings
from app.core.exceptions import ModelUnavailableError, PredictionFailedError
from app.ml.crop_recommendation.inference.predictor import CropRecommendationPredictor
from app.ml.crop_recommendation.schema import FEATURE_ORDER

BASE_FEATURES = {
    "N": 90.0,
    "P": 42.0,
    "K": 43.0,
    "temperature": 20.9,
    "humidity": 82.0,
    "ph": 6.5,
    "rainfall": 202.9,
}


@pytest.fixture(scope="module")
def predictor() -> CropRecommendationPredictor:
    p = CropRecommendationPredictor(get_settings().MODEL_ARTIFACTS_DIR)
    if not p.try_load():
        pytest.skip(
            "Model artifacts not found. Run: "
            "python -m app.ml.crop_recommendation.training.train"
        )
    return p


def test_artifacts_load(predictor):
    assert predictor.is_loaded
    assert predictor.load_error is None
    assert predictor.model_version


def test_metadata_declares_the_expected_feature_order(predictor):
    assert tuple(predictor.metadata["feature_names"]) == FEATURE_ORDER


def test_metadata_records_provenance(predictor):
    meta = predictor.metadata
    for key in ("model_name", "model_version", "algorithm", "trained_at", "classes"):
        assert meta.get(key), f"metadata is missing {key}"
    # Dataset fingerprint: makes "why did predictions change?" answerable.
    assert len(meta["dataset"]["sha256"]) == 64
    assert meta["dataset"]["n_rows"] == 2200
    assert len(meta["classes"]) == 22


def test_metadata_keeps_the_honesty_caveat_with_the_metrics(predictor):
    assert "synthetic" in predictor.metadata["caveat"].lower()


def test_prediction_returns_a_known_class(predictor):
    result = predictor.predict(BASE_FEATURES)
    assert result.recommended_crop in predictor.metadata["classes"]
    assert 0.0 <= result.confidence <= 1.0


def test_prediction_is_deterministic(predictor):
    a = predictor.predict(BASE_FEATURES)
    b = predictor.predict(BASE_FEATURES)
    assert a.recommended_crop == b.recommended_crop
    assert a.confidence == b.confidence


def test_dict_ordering_does_not_change_the_result(predictor):
    """The vector is built by name lookup, so the caller's dict order is
    irrelevant. If this ever fails, assembly has become positional."""
    reversed_dict = {k: BASE_FEATURES[k] for k in reversed(list(BASE_FEATURES))}
    assert (
        predictor.predict(reversed_dict).recommended_crop
        == predictor.predict(BASE_FEATURES).recommended_crop
    )


def test_feature_order_actually_matters(predictor):
    """Proves the order guard is doing real work rather than passing by
    coincidence: the same numbers against the wrong features must give a
    different answer."""
    values = [BASE_FEATURES[name] for name in FEATURE_ORDER]
    scrambled = dict(zip(FEATURE_ORDER, reversed(values)))
    assert (
        predictor.predict(scrambled).recommended_crop
        != predictor.predict(BASE_FEATURES).recommended_crop
    )


def test_alternatives_are_ranked_and_exclude_the_top_crop(predictor):
    result = predictor.predict(BASE_FEATURES)
    probs = [c.probability for c in result.alternatives]
    assert probs == sorted(probs, reverse=True)
    assert all(c.crop != result.recommended_crop for c in result.alternatives)


def test_missing_feature_is_rejected(predictor):
    incomplete = {k: v for k, v in BASE_FEATURES.items() if k != "rainfall"}
    with pytest.raises(PredictionFailedError):
        predictor.predict(incomplete)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_values_are_rejected(predictor, bad):
    with pytest.raises(PredictionFailedError):
        predictor.predict({**BASE_FEATURES, "ph": bad})


def test_non_numeric_value_is_rejected(predictor):
    with pytest.raises(PredictionFailedError):
        predictor.predict({**BASE_FEATURES, "ph": "acidic"})


def test_missing_artifacts_degrade_rather_than_crash(tmp_path):
    """An empty artifacts directory must not raise on load or on startup; it
    must surface as an unavailable model and a 503 at the endpoint."""
    p = CropRecommendationPredictor(tmp_path)
    assert p.try_load() is False
    assert p.is_loaded is False
    assert p.health()["status"] == "unavailable"
    with pytest.raises(ModelUnavailableError):
        p.predict(BASE_FEATURES)


def test_feature_order_mismatch_is_refused_at_load(tmp_path, predictor):
    """A model trained on a different feature order must be rejected outright
    rather than served: it would return confident nonsense."""
    import shutil

    src = get_settings().MODEL_ARTIFACTS_DIR
    for name in ("model.joblib", "label_encoder.joblib"):
        shutil.copy(src / name, tmp_path / name)

    meta = json.loads((src / "metadata.json").read_text())
    meta["feature_names"] = list(reversed(meta["feature_names"]))
    (tmp_path / "metadata.json").write_text(json.dumps(meta))

    tampered = CropRecommendationPredictor(tmp_path)
    assert tampered.try_load() is False
    assert "feature order mismatch" in (tampered.load_error or "").lower()
