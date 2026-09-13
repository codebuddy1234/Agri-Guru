# Model Card — Crop Recommendation v1

| | |
|---|---|
| **Model name** | `crop_recommendation` |
| **Version** | `v1.0.0` |
| **Algorithm** | RandomForest (scikit-learn Pipeline: StandardScaler → classifier) |
| **Trained** | 2026-09-13 |
| **Task** | 22-class single-label classification |
| **Artifacts** | `backend/app/ml/crop_recommendation/artifacts/` |
| **scikit-learn** | 1.6.1 |

## Intended use

Suggests candidate crops from seven soil and weather measurements entered by a
farmer. It is a **starting point for a conversation with an agricultural
officer**, not a sowing decision.

**Out of scope.** The model has no knowledge of field history, irrigation,
seed availability, market prices, season, or forecast. It must not be used to
plan finances, and it is not a substitute for agronomic advice.

## Training data

`Crop_recommendation.csv` — 2,200 rows, 22 crops, exactly 100 rows per crop.
SHA-256 `54a5a6e5408668e668667efc50de2fc8…`

Features (order is contractual): N, P, K, temperature, humidity, ph, rainfall

Full inspection: [`DATASET_INSPECTION.md`](./DATASET_INSPECTION.md).

## How the model was chosen

Two gates on 5-fold stratified CV over the training split only.

| Model | CV macro-F1 | CV log loss | Saturated | Mean top prob |
|---|---|---|---|---|
| GaussianNB | 0.9949 ± 0.0042 | 0.0158 | 60.7% | 0.9919 |
| LogisticRegression | 0.9678 ± 0.0068 | 0.2365 | 0.0% | 0.8239 |
| DecisionTree | 0.9852 ± 0.0068 | 0.5325 | 100.0% | 1.0000 |
| RandomForest | 0.9931 ± 0.0053 | 0.0603 | 13.8% | 0.9478 |

**Gate 1 — accuracy.** Within 0.005 macro-F1 of the leader: GaussianNB, RandomForest.

**Gate 2 — probability quality.** At most 25% of out-of-fold predictions may be
*saturated* (top class holding essentially all probability mass).

GaussianNB won on macro-F1 but was **rejected**: it returns exactly 1.0 for the
top crop and 0.0 for every alternative on 60.7% of predictions. That is an
artefact of its conditional-independence assumption on near-separable data, not
real certainty. Serving it would mean showing a farmer "Confidence: 100%" and a
list of alternative crops at 0%. The product shows both, so a model that cannot
express uncertainty honestly cannot serve — the 0.0017 macro-F1 it wins by is
not worth a confidence figure that is a lie.

DecisionTree is worse still: 100% saturated, log loss 0.53.

**Selected: RandomForest** — passes both gates, graded probabilities.

## Performance

Holdout set (440 rows), evaluated once, never used for selection:

| Metric | Value |
|---|---|
| Accuracy | 0.9955 |
| Macro F1 | 0.9955 |
| Macro precision | 0.9957 |
| Macro recall | 0.9955 |

Accuracy is a fair headline here only because the classes are exactly balanced;
macro metrics are reported alongside because per-class behaviour is what a
farmer experiences.

Weakest classes by F1:

| Crop | F1 |
|---|---|
| blackgram | 0.9744 |
| rice | 0.9744 |
| jute | 0.9756 |
| maize | 0.9756 |
| apple | 1.0000 |

## ⚠️ These numbers are not field accuracy

**These metrics come from a clean, perfectly class-balanced, largely synthetic benchmark dataset with no geography, season or soil-type features. They describe performance on that dataset only and are NOT an estimate of real-world field accuracy.**

Three specific reasons:

1. **The dataset is effectively synthetic.** Exactly 100 rows per class,
   suspiciously tidy per-crop ranges, integer N/P/K against 8-decimal
   temperatures. Sampled from per-crop parameter ranges, not collected from
   2,200 real farms.
2. **The problem is near-separable by construction.** Four very different model
   families land within 2.7 points of each other, and a naive Bayes classifier
   leads. Model choice is barely doing any work — the data is easy, not the
   model good.
3. **No geography, season, or soil type.** The target region is Maharashtra, but
   the model cannot distinguish "grows somewhere in India given these numbers"
   from "is right for this farm this season". The label set includes apple and
   coconut, which are not Maharashtra crops.

Because of (3), the UI always shows ranked alternatives rather than a single
answer, so an implausible top choice is visibly one option among several.

## Known limitations

- **N, P, K are unitless ratio values, not kg/ha.** A value copied from a soil
  health card is on a different scale and will mislead. The input form states
  this above the fields; it is the single most likely cause of a wrong
  real-world prediction, and it is a UI problem rather than a model one.
- **Confidence means tree agreement, not success probability.** It reports how
  consistently the forest voted on this dataset.
- **Extrapolation is flagged, not blocked.** Physically plausible values outside
  the training range are accepted, and the response marks them
  `out_of_training_range`.
- **No calibration step.** Probabilities are raw vote fractions. If confidence
  is ever used for a decision threshold rather than display, calibrate first
  (e.g. `CalibratedClassifierCV`).

## Reproducing

```bash
cd backend
python -m app.ml.crop_recommendation.training.train
```

Deterministic given the same dataset and library versions (`random_state=42`).
`metadata.json` records the dataset SHA-256 and library versions, so a changed
prediction can always be traced to a changed input or a changed dependency.
