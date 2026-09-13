"""
AgriGuru AI - Phase 1, Step 1: Crop Recommendation dataset inspection.

Reproduces every number quoted in docs/DATASET_INSPECTION.md.
This script only READS the dataset; it writes nothing and trains no
production model. The baseline model section exists purely to answer
"is this problem separable, and which model family deserves a real
training pipeline?" - it is not the training pipeline itself.

Usage:
    python scripts/inspect_dataset.py [path/to/Crop_recommendation.csv]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

DEFAULT_CSV = Path(__file__).resolve().parents[1] / "data" / "raw" / "Crop_recommendation.csv"
RANDOM_STATE = 42
TARGET = "label"


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def structure(df: pd.DataFrame) -> None:
    section("1. STRUCTURE")
    print(f"rows: {df.shape[0]}   columns: {df.shape[1]}")
    print("\ndtypes:")
    print(df.dtypes.to_string())
    print("\nmissing values per column:")
    print(df.isna().sum().to_string())
    numeric = df.select_dtypes(include=[np.number])
    print(f"\nnon-finite (inf/-inf) values: {int(np.isinf(numeric).sum().sum())}")
    print(f"fully duplicated rows: {int(df.duplicated().sum())}")
    print(f"duplicated feature rows (ignoring target): {int(df.drop(columns=[TARGET]).duplicated().sum())}")


def target_balance(df: pd.DataFrame) -> None:
    section("2. TARGET / CLASS BALANCE")
    counts = df[TARGET].value_counts()
    print(f"target column: '{TARGET}'   classes: {counts.size}")
    print(counts.to_string())
    print(f"\nmin class size: {counts.min()}   max class size: {counts.max()}")
    print("perfectly balanced" if counts.nunique() == 1 else "IMBALANCED - stratify and report macro metrics")

    # Row ordering matters: a non-shuffled split on a class-sorted file is a
    # silent, catastrophic bug (some classes end up entirely in one split).
    blocks = (df[TARGET] != df[TARGET].shift()).cumsum().nunique()
    print(f"\ncontiguous label blocks in file order: {blocks}")
    if blocks == counts.size:
        print("=> file is sorted by class. ALWAYS shuffle + stratify when splitting.")


def distributions(df: pd.DataFrame) -> None:
    section("3. FEATURE DISTRIBUTIONS")
    features = df.drop(columns=[TARGET])
    print(features.describe().T.to_string())

    print("\nglobal IQR outliers (1.5 x IQR fence):")
    for col in features.columns:
        q1, q3 = features[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n = int(((features[col] < lo) | (features[col] > hi)).sum())
        print(f"  {col:<12} {n:>4} ({100 * n / len(features):>4.1f}%)  fence[{lo:>8.2f},{hi:>8.2f}]")
    print("\nNote: these fences are GLOBAL. This dataset is a mixture of 22")
    print("per-crop distributions, so a global outlier is usually a legitimate")
    print("member of a crop with extreme requirements, not dirty data.")

    print("\nagronomic plausibility:")
    print(f"  ph outside [0, 14]:        {int(((features.ph < 0) | (features.ph > 14)).sum())}")
    print(f"  ph outside [4.5, 8.5]:     {int(((features.ph < 4.5) | (features.ph > 8.5)).sum())}")
    print(f"  humidity outside [0, 100]: {int(((features.humidity < 0) | (features.humidity > 100)).sum())}")
    print(f"  negative feature values:   {int((features < 0).sum().sum())}")

    print("\nfeature correlation:")
    print(features.corr().round(2).to_string())


def scale_and_encoding(df: pd.DataFrame) -> None:
    section("4. SCALING / ENCODING REQUIREMENTS")
    features = df.drop(columns=[TARGET])
    spans = (features.max() - features.min()).sort_values()
    print("value span per feature:")
    print(spans.round(2).to_string())
    print(f"\nlargest span / smallest span = {spans.max() / spans.min():.1f}x")
    print("=> distance- and gradient-based models (LogReg, SVM, KNN) need scaling.")
    print("=> tree ensembles (RandomForest, XGBoost) do not, but a shared")
    print("   preprocessing artifact keeps inference identical across models.")
    print(f"\nall {features.shape[1]} features are numeric -> no categorical encoding needed.")
    print(f"target '{TARGET}' is categorical text -> needs a LabelEncoder, persisted as an artifact.")


def baselines(df: pd.DataFrame) -> None:
    section("5. BASELINE SEPARABILITY CHECK (not the training pipeline)")
    X = df.drop(columns=[TARGET])
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    candidates = {
        "LogisticRegression": Pipeline(
            [("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=2000))]
        ),
        "GaussianNB": GaussianNB(),
        "DecisionTree": DecisionTreeClassifier(random_state=RANDOM_STATE),
        "RandomForest": RandomForestClassifier(
            n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1
        ),
    }

    print(f"{'model':<20} {'cv_acc (5-fold, train)':<24} {'holdout_acc':<12}")
    fitted = {}
    for name, model in candidates.items():
        scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy", n_jobs=-1)
        model.fit(X_train, y_train)
        fitted[name] = model
        print(f"{name:<20} {scores.mean():.4f} +/- {scores.std():.4f}       {model.score(X_test, y_test):.4f}")

    rf = fitted["RandomForest"]
    print("\nRandomForest feature importance:")
    for feat, imp in sorted(zip(X.columns, rf.feature_importances_), key=lambda p: -p[1]):
        print(f"  {feat:<12} {imp:.3f}")

    confidence = rf.predict_proba(X_test).max(axis=1)
    print(f"\nRandomForest top-class probability on holdout:")
    print(f"  mean {confidence.mean():.3f}   min {confidence.min():.3f}   "
          f"below 0.60: {int((confidence < 0.60).sum())} of {len(confidence)}")
    print("\nThese numbers describe a clean, class-balanced, largely synthetic")
    print("benchmark dataset. They are NOT an estimate of real-world field accuracy.")


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        raise SystemExit(f"dataset not found: {csv_path}")

    print(f"AgriGuru AI - dataset inspection\nsource: {csv_path}")
    df = pd.read_csv(csv_path)

    if TARGET not in df.columns:
        raise SystemExit(f"expected target column '{TARGET}', found: {list(df.columns)}")

    structure(df)
    target_balance(df)
    distributions(df)
    scale_and_encoding(df)
    baselines(df)


if __name__ == "__main__":
    main()
