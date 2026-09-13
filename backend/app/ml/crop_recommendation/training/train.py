"""Offline training pipeline for the crop recommendation model.

Run from the backend directory:

    python -m app.ml.crop_recommendation.training.train

This module is NEVER imported by the running API. It pulls pandas and the
full training stack; inference needs only the fitted estimator. Keeping the
boundary hard means there is no code path by which a farmer's request could
trigger a retrain.

Methodology (justified in docs/DATASET_INSPECTION.md):
  * No row removal. Global IQR "outliers" are legitimate members of crops
    with extreme requirements; dropping them would delete whole classes.
  * Shuffled + stratified split, fixed seed. The CSV is sorted by class, so
    an unshuffled split puts entire crops in one side.
  * Preprocessing is fitted inside each CV fold via a Pipeline, so the
    scaler never sees the validation fold. That is the only real leakage
    risk this dataset presents.
  * Selection is a two-gate process on 5-fold CV over the TRAIN split only.
    The holdout set is touched exactly once, at the end, and never informs a
    choice.

      Gate 1 - accuracy: macro-F1 within TIE_BREAK_TOLERANCE of the leader.
      Gate 2 - probability quality: the product shows a confidence figure and
               a ranked list of alternative crops, so a model whose
               probabilities are degenerate cannot serve, however accurate it
               is. Measured as the share of predictions where the top class
               takes essentially all the mass.

    Gate 2 exists because accuracy alone picks the wrong model here.
    Measured on this dataset:

        model                cv_macro_f1   saturated   mean_top_p
        GaussianNB              0.9949       60.7%       0.9919
        DecisionTree            0.9853      100.0%       1.0000
        RandomForest            0.9932       13.8%       0.9478
        LogisticRegression      0.9681        0.0%       0.8239

    GaussianNB has the best macro-F1, but returns exactly 1.0 for the top
    crop and exactly 0.0 for every alternative on the majority of rows - an
    artefact of its conditional-independence assumption on near-separable
    data, not real certainty. Serving it would mean printing "Confidence:
    100%" to a farmer and a top-3 list of three crops at 0%. Spec section 12
    forbids fabricating confidence, so the 0.0017 macro-F1 it wins by is not
    worth a confidence number that is a lie.

  * Among candidates passing both gates, ties break toward the simpler
    model, so complexity is never bought for a fraction of a point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)
from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_predict,
    cross_val_score,
    train_test_split,
)
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from app.core.config import get_settings
from app.ml.crop_recommendation.schema import (
    FEATURE_ORDER,
    FEATURE_SPECS,
    MODEL_NAME,
    TARGET_NAME,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("train")

RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
MODEL_VERSION = "v1.0.0"

#: Lower rank = structurally simpler. Used only to break near-ties, so the
#: pipeline never buys a fraction of a point with a heavier model.
COMPLEXITY_RANK: dict[str, int] = {
    "GaussianNB": 0,
    "LogisticRegression": 1,
    "DecisionTree": 2,
    "RandomForest": 3,
}

#: A candidate must beat the best macro-F1 by more than this to win outright.
TIE_BREAK_TOLERANCE = 0.005

#: A prediction is "saturated" when the top class holds essentially all the
#: probability mass, leaving no meaningful runner-up to show as an alternative.
SATURATION_THRESHOLD = 0.999999

#: A model may not serve if more than this share of its predictions are
#: saturated. See gate 2 in the module docstring.
MAX_SATURATED_SHARE = 0.25


def build_candidates() -> dict[str, Pipeline]:
    """Every candidate is a Pipeline, so preprocessing is refitted inside each
    CV fold. Tree models do not need scaling, but keeping one shared pipeline
    shape means inference is identical whichever model wins."""
    return {
        "GaussianNB": Pipeline([("scaler", StandardScaler()), ("clf", GaussianNB())]),
        "LogisticRegression": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=2000, random_state=RANDOM_STATE)),
            ]
        ),
        "DecisionTree": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", DecisionTreeClassifier(random_state=RANDOM_STATE)),
            ]
        ),
        "RandomForest": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1
                    ),
                ),
            ]
        ),
    }


def load_dataset(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    df = pd.read_csv(csv_path)

    expected = set(FEATURE_ORDER) | {TARGET_NAME}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(
            f"Dataset is missing expected columns {sorted(missing)}. "
            f"Found: {sorted(df.columns)}"
        )

    # Fail loudly rather than training on data that silently changed shape.
    if df[list(FEATURE_ORDER)].isna().any().any():
        raise ValueError("Dataset contains missing feature values.")
    if not np.isfinite(df[list(FEATURE_ORDER)].to_numpy()).all():
        raise ValueError("Dataset contains non-finite feature values.")

    n_dupes = int(df.duplicated().sum())
    if n_dupes:
        logger.warning("Dataset contains %d duplicate rows.", n_dupes)

    logger.info("Loaded %d rows x %d columns from %s", len(df), df.shape[1], csv_path.name)
    return df


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_model(
    candidates: dict[str, Pipeline],
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_classes: int,
) -> tuple[str, dict[str, dict[str, float]]]:
    """Two-gate selection: accuracy, then probability quality, then simplicity.

    See the module docstring for why probability quality is a gate and not a
    tiebreaker.
    """
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    results: dict[str, dict[str, float]] = {}

    logger.info(
        "\n%-20s %14s %12s %11s %11s",
        "model",
        "cv_macro_f1",
        "cv_log_loss",
        "saturated",
        "mean_top_p",
    )
    logger.info("%s", "-" * 72)

    for name, pipeline in candidates.items():
        f1_scores = cross_val_score(
            pipeline, X_train, y_train, cv=cv, scoring="f1_macro", n_jobs=-1
        )
        # Out-of-fold probabilities: the only honest way to judge how the
        # model's confidence behaves on data it did not fit.
        proba = cross_val_predict(
            pipeline, X_train, y_train, cv=cv, method="predict_proba", n_jobs=-1
        )
        top_p = proba.max(axis=1)
        saturated_share = float((top_p > SATURATION_THRESHOLD).mean())

        results[name] = {
            "cv_macro_f1_mean": float(f1_scores.mean()),
            "cv_macro_f1_std": float(f1_scores.std()),
            "cv_log_loss": float(log_loss(y_train, proba, labels=list(range(n_classes)))),
            "cv_saturated_share": saturated_share,
            "cv_mean_top_probability": float(top_p.mean()),
        }
        logger.info(
            "%-20s %8.4f +/-%.4f %12.4f %10.1f%% %11.4f",
            name,
            f1_scores.mean(),
            f1_scores.std(),
            results[name]["cv_log_loss"],
            saturated_share * 100,
            top_p.mean(),
        )

    # --- Gate 1: accuracy ---
    best_f1 = max(r["cv_macro_f1_mean"] for r in results.values())
    accurate = [
        name
        for name, r in results.items()
        if best_f1 - r["cv_macro_f1_mean"] <= TIE_BREAK_TOLERANCE
    ]
    logger.info(
        "\nGate 1 - within %.3f macro-F1 of the leader: %s",
        TIE_BREAK_TOLERANCE,
        ", ".join(accurate),
    )

    # --- Gate 2: probability quality ---
    usable = [n for n in accurate if results[n]["cv_saturated_share"] <= MAX_SATURATED_SHARE]
    rejected = [n for n in accurate if n not in usable]
    for name in rejected:
        logger.info(
            "Gate 2 - REJECTED %s: %.1f%% of predictions saturated (limit %.0f%%). "
            "Its confidence and alternative-crop list would be meaningless.",
            name,
            results[name]["cv_saturated_share"] * 100,
            MAX_SATURATED_SHARE * 100,
        )
    if not usable:
        raise RuntimeError(
            "No candidate passed both gates. Either widen the candidate set or "
            "add probability calibration (e.g. CalibratedClassifierCV)."
        )
    logger.info("Gate 2 - usable probabilities: %s", ", ".join(usable))

    # --- Simplicity tie-break among survivors ---
    winner = min(usable, key=lambda n: (COMPLEXITY_RANK[n], -results[n]["cv_macro_f1_mean"]))
    logger.info("\nSelected: %s (simplest model passing both gates)", winner)
    return winner, results


def evaluate_holdout(
    model: BaseEstimator,
    X_test: np.ndarray,
    y_test: np.ndarray,
    class_names: list[str],
) -> dict[str, Any]:
    """Touched exactly once, after selection. Never a tuning signal."""
    y_pred = model.predict(X_test)
    metrics = {
        "holdout_accuracy": float(accuracy_score(y_test, y_pred)),
        "holdout_macro_f1": float(f1_score(y_test, y_pred, average="macro")),
        "holdout_macro_precision": float(
            precision_score(y_test, y_pred, average="macro", zero_division=0)
        ),
        "holdout_macro_recall": float(
            recall_score(y_test, y_pred, average="macro", zero_division=0)
        ),
    }
    logger.info("\nHoldout evaluation (%d rows, never used for selection):", len(y_test))
    for key, value in metrics.items():
        logger.info("  %-26s %.4f", key, value)

    report = classification_report(
        y_test, y_pred, target_names=class_names, zero_division=0, output_dict=True
    )
    per_class = {
        name: round(float(report[name]["f1-score"]), 4)
        for name in class_names
        if name in report
    }
    worst = sorted(per_class.items(), key=lambda kv: kv[1])[:3]
    logger.info("  weakest classes by F1: %s", worst)

    cm = confusion_matrix(y_test, y_pred)
    return {
        "metrics": metrics,
        "per_class_f1": per_class,
        "confusion_matrix": cm.tolist(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the crop recommendation model.")
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    settings = get_settings()
    csv_path = args.dataset or settings.DATASET_PATH
    out_dir = args.output_dir or settings.MODEL_ARTIFACTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(csv_path)

    X = df[list(FEATURE_ORDER)].copy()
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(df[TARGET_NAME])
    class_names = list(label_encoder.classes_)
    logger.info("Target '%s': %d classes", TARGET_NAME, len(class_names))

    # Stratified AND shuffled: the CSV is sorted by class.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, shuffle=True, random_state=RANDOM_STATE
    )
    logger.info("Split: %d train / %d holdout", len(X_train), len(X_test))

    # Fit on plain arrays, not DataFrames. Fitting on a DataFrame makes
    # scikit-learn record column names and warn on every array prediction,
    # which would push pandas into the API runtime just to silence a warning.
    # Feature order is instead enforced explicitly: it is written to
    # metadata.json and checked against FEATURE_ORDER when the predictor
    # loads, and the request vector is assembled by name lookup.
    X_train_arr = X_train.to_numpy(dtype=np.float64)
    X_test_arr = X_test.to_numpy(dtype=np.float64)

    winner, cv_results = select_model(
        build_candidates(), X_train_arr, y_train, n_classes=len(class_names)
    )

    final_model = build_candidates()[winner]
    final_model.fit(X_train_arr, y_train)

    holdout = evaluate_holdout(final_model, X_test_arr, y_test, class_names)

    # The fitted scaler is saved separately as well as inside the pipeline:
    # the pipeline is what inference uses, the standalone artifact makes the
    # preprocessing inspectable and reusable by future modules.
    scaler = final_model.named_steps["scaler"]

    joblib.dump(final_model, out_dir / "model.joblib")
    joblib.dump(scaler, out_dir / "preprocessor.joblib")
    joblib.dump(label_encoder, out_dir / "label_encoder.joblib")

    metadata = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "algorithm": winner,
        "trained_at": datetime.now(UTC).isoformat(),
        "random_state": RANDOM_STATE,
        "dataset": {
            "file": csv_path.name,
            "sha256": file_sha256(csv_path),
            "n_rows": int(len(df)),
            "n_classes": len(class_names),
            "test_size": TEST_SIZE,
        },
        "feature_names": list(FEATURE_ORDER),
        "target_name": TARGET_NAME,
        "classes": class_names,
        "selection": {
            "gate_1_accuracy": (
                f"macro-F1 within {TIE_BREAK_TOLERANCE} of the leader "
                f"(5-fold CV on the training split)"
            ),
            "gate_2_probability_quality": (
                f"at most {MAX_SATURATED_SHARE:.0%} of out-of-fold predictions saturated "
                f"(top class probability > {SATURATION_THRESHOLD}); a model that fails "
                f"this cannot honestly report confidence or rank alternative crops"
            ),
            "tie_break": "simplest model among those passing both gates",
            "candidates": cv_results,
        },
        "metrics": {
            **cv_results[winner],
            **holdout["metrics"],
        },
        "per_class_f1": holdout["per_class_f1"],
        "confusion_matrix": holdout["confusion_matrix"],
        "input_ranges": {
            spec.name: {
                "training_min": spec.training_min,
                "training_max": spec.training_max,
                "accepted_min": spec.accepted_min,
                "accepted_max": spec.accepted_max,
                "unit": spec.unit,
            }
            for spec in FEATURE_SPECS.values()
        },
        "library_versions": {
            "scikit-learn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "joblib": joblib.__version__,
        },
        "caveat": (
            "These metrics come from a clean, perfectly class-balanced, largely "
            "synthetic benchmark dataset with no geography, season or soil-type "
            "features. They describe performance on that dataset only and are NOT "
            "an estimate of real-world field accuracy."
        ),
    }
    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    logger.info("\nArtifacts written to %s", out_dir)
    for artifact in sorted(out_dir.iterdir()):
        logger.info("  %-24s %8.1f KB", artifact.name, artifact.stat().st_size / 1024)


if __name__ == "__main__":
    main()
