# AgriGuru AI

Smart agriculture decision-support platform for farmers — Maharashtra first, in
**Marathi, Hindi and English**.

**Phase 1 is complete**: the Crop Recommendation module is built end-to-end, on
an architecture the remaining modules attach to without restructuring.

```
Farmer → Next.js → FastAPI → validation → service → trained model
                                    ↓
                              PostgreSQL → history
```

---

## What works today

| | |
|---|---|
| 🌱 **Crop Recommendation** | Live — 22 crops from 7 soil/weather values |
| 🔐 Authentication | Email + password, JWT access/refresh, farmer/expert/admin roles |
| 👤 Farmer profile & farms | Profile, location, farms in acre/guntha/hectare |
| 📜 Prediction history | Every recommendation saved with its model version |
| 🌐 Marathi / Hindi / English | Server-rendered per locale, no hardcoded strings |

Disease detection, weather, market prices, fertiliser, yield, schemes and
expert review appear on the dashboard as **Coming Soon** cards. They are not
clickable and have no route — no fake functionality ships.

## ⚠️ Read this before quoting an accuracy number

The model scores **0.9955 holdout accuracy**, and that figure is close to
meaningless as a measure of real-world usefulness:

- The dataset is effectively **synthetic** — exactly 100 rows per crop, tidy
  per-crop ranges, integer N/P/K against 8-decimal temperatures.
- The classes are **near-separable by construction**: four very different model
  families land within 2.7 points, and naive Bayes leads.
- There is **no geography, season or soil type** in the data, yet the target
  region is Maharashtra — and the label set contains apple and coconut.
- **N, P, K are unitless ratios, not kg/ha.** A soil health card value is on a
  different scale and will mislead.

Details: [`docs/DATASET_INSPECTION.md`](docs/DATASET_INSPECTION.md) §6 and
[`docs/MODEL_CARD.md`](docs/MODEL_CARD.md).

## Quick start

### With Docker

```bash
cp .env.example backend/.env
# set a real SECRET_KEY — the app refuses to start with the placeholder:
python -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up --build
```

Then: frontend http://localhost:3000 · API docs http://localhost:8000/api/v1/docs

### Manual

**1. Database** (PostgreSQL 13+ — `gen_random_uuid()` is built in from 13)

```bash
createdb agriguru
psql -c "CREATE USER agriguru WITH PASSWORD 'agriguru';"
```

**2. Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp ../.env.example .env          # then set a real SECRET_KEY
alembic upgrade head             # creates the 4 tables

# Train the model (once). The API loads the artifacts; it never retrains.
python -m app.ml.crop_recommendation.training.train

uvicorn app.main:app --reload
```

**3. Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000 — it redirects to `/mr` (Marathi is the default).

## Testing

```bash
cd backend && pytest              # 82 tests, needs PostgreSQL
python scripts/inspect_dataset.py # reproduces every dataset figure
cd frontend && npm run typecheck && npm run build
```

The backend tests run against **real PostgreSQL**, not SQLite: the schema uses
JSONB, UUID server defaults and PG enums, so a SQLite substitute would test a
different schema than the one that ships. Set `TEST_DATABASE_URL` to point at a
scratch database.

## Project structure

```
backend/
  app/
    api/v1/        routes — validate, delegate, return. No ML, no SQL.
    core/          config, security, exceptions, logging
    database/      SQLAlchemy models + session
    schemas/       Pydantic request/response contracts
    services/      business logic and transactions
    ml/crop_recommendation/
      schema.py    FEATURE_ORDER + validation ranges (single source of truth)
      training/    offline only — never imported by the API
      inference/   predictor loaded once at startup
      artifacts/   model.joblib, label_encoder.joblib, metadata.json
  alembic/         migrations
  tests/           82 tests
frontend/
  app/[locale]/    landing, login, register, dashboard,
                   crop-recommendation, history, profile
  components/      ui/ crop/ farmer/ layout/
  locales/         en.json · hi.json · mr.json (identical key sets, type-checked)
data/raw/          Crop_recommendation.csv
docs/              DATASET_INSPECTION · PHASE1_PLAN · API · MODEL_CARD
scripts/           inspect_dataset.py
```

## Architecture decisions worth knowing

**Modular monolith, not microservices.** One API, one database, one compose
file. Adding a module means four files (`api/v1/x.py`, `schemas/x.py`,
`services/x_service.py`, `database/models/x.py`) plus one router line.

**The model loads once at startup.** If the artifacts are missing the app still
boots, `/health` reports `degraded`, and only `/predict` returns 503 — a broken
model file must not take down login and history.

**Feature order is enforced, not assumed.** It is written to `metadata.json`,
checked against the code's `FEATURE_ORDER` at load, and request vectors are
built by name lookup. A silent reorder would produce confident wrong answers
with no error anywhere; a test proves the guard actually bites.

**Model selection has a probability-quality gate.** Accuracy alone picked
GaussianNB, which returns 100% confidence on 60.7% of predictions. Since the UI
shows confidence and ranked alternatives, that model was disqualified in favour
of RandomForest. See [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md).

**Extrapolation is flagged, not hidden.** Plausible values outside the training
range are accepted and marked `out_of_training_range` in the response and the UI.

**Cross-farmer reads return 404, not 403** — a 403 confirms the record exists.

## Security

Password hashing with bcrypt · JWT with a `type` claim so a refresh token
cannot be replayed as an access token · role-based dependencies ready for
expert and admin · CORS restricted to configured origins (never `*`) · all
secrets from `.env` with `.env.example` committed and `.env` git-ignored ·
ORM-only queries · structured errors that never leak stack traces.

No external API keys are needed in Phase 1. `.env.example` marks where weather,
SMS and market credentials will go when those modules are built.

## Roadmap

Phase 2: disease detection (CNN), weather integration, mobile OTP login.
Phase 3: market prices, fertiliser recommendation.
Phase 4: yield prediction, schemes, expert verification, admin dashboard.

Each attaches to `farmer_profiles` / `farms` / `users` with the conventions
already in place. None of their tables are created early.
