# Crop Recommendation Dataset — Inspection Report

**Phase 1, Step 1.** Every number below is produced by `scripts/inspect_dataset.py`
against `data/raw/Crop_recommendation.csv`. Nothing here is assumed or copied from
documentation about similar datasets.

```bash
python scripts/inspect_dataset.py
```

---

## 1. Structure

| Property | Value |
|---|---|
| Rows | 2,200 |
| Columns | 8 (7 features + 1 target) |
| Missing values | 0 |
| Infinite values | 0 |
| Fully duplicated rows | 0 |
| Duplicated feature rows (ignoring target) | 0 |

**Confirmed** column names and types — these match what the spec guessed, but the
confirmation comes from the file, not from the guess:

| Column | dtype | Meaning |
|---|---|---|
| `N` | int64 | Soil nitrogen content (ratio) |
| `P` | int64 | Soil phosphorus content (ratio) |
| `K` | int64 | Soil potassium content (ratio) |
| `temperature` | float64 | Temperature, °C |
| `humidity` | float64 | Relative humidity, % |
| `ph` | float64 | Soil pH |
| `rainfall` | float64 | Rainfall, mm |
| `label` | object | **Target** — crop name, 22 distinct values |

The dataset carries **no units metadata**. The units above are inferred from the
observed ranges (temperature 8.8–43.7 reads as °C; humidity 14.3–100.0 reads as %;
rainfall 20–299 reads as mm over a season). N/P/K have no documented unit at all —
they are unitless ratio values in the 0–205 band, **not** kg/ha. This matters for
the UI: see §6.

## 2. Target and class balance

22 crops, **exactly 100 rows each** — perfectly balanced:

```
rice, maize, chickpea, kidneybeans, pigeonpeas, mothbeans, mungbean,
blackgram, lentil, pomegranate, banana, mango, grapes, watermelon,
muskmelon, apple, orange, papaya, coconut, cotton, jute, coffee
```

Consequences:
- Plain **accuracy is a fair headline metric** here (it usually is not in multi-class
  work, but with an exactly uniform prior it is not misleading).
- Macro precision / recall / F1 are still reported, since per-class behaviour is what
  a farmer actually experiences.
- No resampling, no class weighting, no SMOTE needed. Adding them would be noise.

**Ordering hazard:** the file is sorted by class — the 2,200 rows form exactly 22
contiguous blocks of 100. A split without shuffling would put whole crops entirely
into train or entirely into test and produce a garbage model that still "runs".
Every split in this project must be **shuffled and stratified with a fixed seed**.

## 3. Distributions and outliers

| Feature | min | mean | max | std |
|---|---|---|---|---|
| N | 0.00 | 50.55 | 140.00 | 36.92 |
| P | 5.00 | 53.36 | 145.00 | 32.99 |
| K | 5.00 | 48.15 | 205.00 | 50.65 |
| temperature | 8.83 | 25.62 | 43.68 | 5.06 |
| humidity | 14.26 | 71.48 | 99.98 | 22.26 |
| ph | 3.50 | 6.47 | 9.94 | 0.77 |
| rainfall | 20.21 | 103.46 | 298.56 | 54.96 |

A global 1.5×IQR fence flags K (9.1%), P (6.3%), rainfall (4.5%), temperature (3.9%),
ph (2.6%), humidity (1.4%), N (0%).

**These are not dirty data and must not be dropped.** The dataset is a mixture of 22
per-crop distributions. K > 92 is "apple and grapes" (K ranges 195–205 for apple), not
a sensor error. Deleting global outliers here would delete entire crops from the
training set. Cleaning decisions must be made *per class* or not at all — and the
per-class ranges are internally consistent, so the correct action is **no row removal**.

Agronomic plausibility: 0 values outside pH 0–14, 0 humidity outside 0–100, 0 negative
values. 47 rows sit outside the common agronomic pH band of 4.5–8.5, concentrated in
crops the dataset gives wide pH tolerance (chickpea reaches pH 8.9) — plausible, kept.

**Feature correlation** is low except **P↔K = 0.74**. That is expected (both are
fertiliser components) and far from the ~0.95 that would justify dropping a feature.
All 7 features are retained.

## 4. Data leakage

No leakage found:
- No ID, timestamp, row-index, or "yield/price/season" column that could encode the answer.
- No target-derived feature.
- No duplicated rows, so no train/test contamination through exact copies.

The one real leakage risk is **procedural**, not structural: fitting a scaler on the
full dataset before splitting. The pipeline must fit preprocessing **inside** the
training fold only (`sklearn.pipeline.Pipeline` handles this correctly under CV).

## 5. Scaling and encoding

- Feature spans differ by **43×** (ph spans 6.4, rainfall spans 278). Scaling is
  **required** for LogisticRegression/SVM/KNN, **irrelevant** for tree ensembles.
  A `StandardScaler` is kept inside the pipeline anyway so that every candidate model
  is served through one identical preprocessing artifact.
- All 7 features are numeric → **no categorical encoding needed**.
- The target is text → a **`LabelEncoder` must be fitted and persisted**, so that
  `predict()` → class index → crop name is stable across retraining. Losing this
  artifact silently remaps every crop name.

## 6. Problems found — read this before trusting any accuracy number

These are the honest caveats. They shape the product, not just the model.

**6.1 — The dataset is effectively synthetic.**
Each class is exactly 100 rows, per-class feature ranges are suspiciously tidy
(apple N is exactly 0–40, K exactly 195–205), and `temperature` has 2,200 distinct
float values with 8 decimal places while `N`/`P`/`K` are integers. This is the
signature of data sampled from per-crop parameter ranges, not collected from 2,200
real farms. It is a perfectly good dataset for building and demonstrating the
pipeline — it is **not** evidence the model works on a Maharashtra farm.

**6.2 — Baseline accuracy is ~99%, and that is a warning, not a win.**

| Model | 5-fold CV accuracy (train) | Holdout accuracy |
|---|---|---|
| LogisticRegression (scaled) | 0.9682 ± 0.0066 | 0.9727 |
| GaussianNB | 0.9949 ± 0.0042 | 0.9955 |
| DecisionTree | 0.9852 ± 0.0068 | 0.9795 |
| RandomForest (300) | 0.9938 ± 0.0055 | 0.9932 |

Four very different model families land within 2.7 points of each other, and a naive
Bayes classifier — which assumes the features are conditionally independent — is at
the top. That means **the classes are nearly linearly separable by construction**, and
model choice is barely doing any work. There is no headroom worth chasing with
hyperparameter tuning or XGBoost; the honest report is "the problem is easy, here is
the evidence." Any write-up claiming 99% means AgriGuru predicts crops correctly in
the field would be false, and the UI must not imply it.

**6.3 — No geography, season, or soil type.**
The target market is Maharashtra. The dataset has no district, no soil class
(black/red/laterite), no sowing season (kharif/rabi), no irrigation availability. The
model cannot distinguish "grows anywhere in India given these numbers" from "is the
right crop for *this* farm *this* season." Phase 1 must present the output as a
**suggestion from soil and weather values only**, never as agronomic advice.

**6.4 — 22 crops, several of which are not Maharashtra crops.**
Apple and coconut are in the label set. A farmer in Nashik receiving "apple" is a
credibility failure even when the model is technically right about the input values.
Phase 1 does **not** filter the label set (that would be inventing agronomy), but the
result page must show the top-3 candidates rather than a single confident answer, so
an implausible top-1 is visibly one option among several.

**6.5 — N, P, K are unitless ratios with no documented scale.**
A farmer's soil health card reports nitrogen in kg/ha. Those numbers are **not
interchangeable** with this dataset's `N`. The input form must present the accepted
range and label it as a soil-test ratio value, and must not claim kg/ha. This is the
single most likely source of wrong real-world predictions, and it is a UI problem, not
a model problem.

**6.6 — Confidence is usable, but must be labelled honestly.**
RandomForest top-class probability on the holdout set averages 0.955, minimum 0.470,
with only 4 of 440 predictions below 0.60. The probabilities are real vote fractions,
not a fabricated number, so they can be shown — but they express *how consistently the
trees agreed on this dataset*, not the probability that the crop will succeed. The UI
wording must say so.

## 7. Decisions this inspection drives

1. **No row removal, no imputation, no resampling.** The data is clean; the work is in
   honest framing, not cleaning.
2. **Shuffled, stratified, seeded split** — mandatory, given the class-sorted file.
3. **Keep all 7 features.** P↔K correlation of 0.74 does not justify dropping either.
4. **Persist `StandardScaler` + `LabelEncoder` + model as versioned artifacts** with a
   `metadata.json` recording feature order. Feature order is a silent-corruption risk
   at inference time.
5. **Candidate models:** LogisticRegression (interpretable baseline), GaussianNB,
   DecisionTree, RandomForest, and XGBoost only if it earns its dependency weight.
   Selection on macro-F1 under 5-fold CV, ties broken toward the simpler model.
6. **Report training performance and real-world applicability separately**, in the
   model card and in the UI.
