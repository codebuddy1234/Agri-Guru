# AgriGuru AI

Smart agriculture decision-support platform for farmers — starting with Maharashtra,
India, in Marathi, Hindi and English.

> **Phase 1 is in planning.** One module is being built end-to-end: **Crop
> Recommendation**. The architecture is laid out so later modules attach without
> restructuring the application.

## Current status

| | |
|---|---|
| ✅ Step 0 | Dataset inspection complete — [`docs/DATASET_INSPECTION.md`](docs/DATASET_INSPECTION.md) |
| 📋 Plan | Awaiting confirmation — [`docs/PHASE1_PLAN.md`](docs/PHASE1_PLAN.md) |
| ⏳ Steps 1–14 | Not started |

## Phase 1 scope

`Farmer → Frontend → API → validation → preprocessing → trained model → prediction →
farmer-friendly result → database → history`

Planned for later, and **not** implemented: crop disease detection, weather, market
information, fertiliser recommendation, yield prediction, government schemes, AI
assistant, expert verification, admin dashboard, notifications, Power BI analytics.
These appear in the UI as clearly marked "Coming Soon" — no fake functionality ships.

## Stack

**Frontend** Next.js · React · TypeScript · Tailwind CSS · shadcn/ui · Framer Motion
**Backend** Python · FastAPI · Pydantic · SQLAlchemy · Alembic
**Database** PostgreSQL
**ML** pandas · NumPy · scikit-learn
**Infra** Docker-ready, `.env` configuration

## Dataset

`data/raw/Crop_recommendation.csv` — 2,200 rows, 7 numeric features
(N, P, K, temperature, humidity, ph, rainfall), 22 crop classes, exactly 100 rows each.
No missing values, no duplicates.

Reproduce the inspection:

```bash
pip install pandas numpy scikit-learn
python scripts/inspect_dataset.py
```

**Read [`docs/DATASET_INSPECTION.md`](docs/DATASET_INSPECTION.md) §6 before quoting any
accuracy figure.** Baseline models reach ~99% on this dataset, and that reflects a
clean, class-balanced, largely synthetic benchmark — it is not an estimate of
real-world field accuracy.
