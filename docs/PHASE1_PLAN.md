# AgriGuru AI — Phase 1 Plan (Crop Recommendation)

**Status: proposal. Awaiting confirmation before the main codebase is implemented.**

Scope of Phase 1: one complete, production-oriented vertical slice —
`Farmer → Frontend → API → validation → preprocessing → trained model → prediction →
farmer-friendly result → database → history` — plus the foundation (auth, roles,
i18n, module registry, error contract) that later modules plug into without a rewrite.

Not built in Phase 1: disease detection, weather, market, fertiliser, yield, schemes,
AI assistant, expert verification, admin dashboard, notifications, Power BI. Their
seats are reserved in the architecture; no fake functionality ships.

---

## 1. Architecture

A **modular monolith**. One FastAPI app, one Next.js app, one PostgreSQL database, one
Docker Compose file. No microservices, no queues, no Kubernetes — per §24 of the spec.

```
Next.js (App Router)  ──REST/JSON──▶  FastAPI
                                        │
                                   API route layer      thin: auth + Pydantic only
                                        │
                                   Service layer        business logic, transactions
                                        │
                        ┌───────────────┴───────────────┐
                   ML inference engine            Repository / ORM
                (loaded once at startup)               │
                        │                         PostgreSQL
              model.pkl / scaler / encoder
                   + metadata.json
```

**The rules that make this scale to module 2 through 12:**

- A route never imports sklearn, never touches a `Session` directly, never builds a
  response dict by hand. It validates, calls one service method, returns a schema.
- Services are the only layer that knows about transactions. A service can call another
  service; a service never imports a route.
- The ML model is loaded **once at application startup** into a module-level singleton
  and injected as a FastAPI dependency. Per-request `joblib.load()` would add ~100ms
  and defeat the point of artifacts. If the artifact is missing, the app **starts
  anyway** and `/health` reports `model: unavailable` — a broken model must not take
  down login and history.
- Every module gets the same four files: `api/v1/<module>.py`, `schemas/<module>.py`,
  `services/<module>_service.py`, `database/models/<module>.py`. Adding disease
  detection in Phase 2 means adding those four files and one router include — no
  restructuring. That is the whole point of this phase.

**Module registry.** Dashboard tiles come from one backend endpoint
(`GET /api/v1/modules`) returning `{key, status: "available"|"coming_soon", ...}`.
Activating a future module becomes a one-line status flip, not a frontend rewrite,
and "Coming Soon" cards can never accidentally become clickable dead ends.

## 2. Project structure

```
agriguru-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                  app factory, router mounting, lifespan
│   │   ├── api/v1/
│   │   │   ├── router.py            aggregates all v1 routers
│   │   │   ├── health.py  auth.py  farmer.py  crop_recommendation.py  modules.py
│   │   │   └── deps.py              get_db, get_current_user, require_role, get_model
│   │   ├── core/
│   │   │   ├── config.py            pydantic-settings, .env driven
│   │   │   ├── security.py          bcrypt hashing, JWT encode/decode
│   │   │   ├── exceptions.py        AppError hierarchy + handlers
│   │   │   └── logging.py           structured logs, request id
│   │   ├── database/
│   │   │   ├── session.py  base.py
│   │   │   └── models/              user.py  farmer_profile.py  farm.py  crop_prediction.py
│   │   ├── schemas/                 common.py  auth.py  farmer.py  crop.py
│   │   ├── services/                auth_service.py  farmer_service.py
│   │   │                            crop_recommendation_service.py
│   │   └── ml/crop_recommendation/
│   │       ├── training/train.py    offline only — never imported by the API
│   │       ├── inference/predictor.py
│   │       ├── artifacts/           model.joblib  preprocessor.joblib
│   │       │                        label_encoder.joblib  metadata.json
│   │       └── schema.py            FEATURE_ORDER + validation ranges (single source)
│   ├── alembic/                     migrations
│   ├── tests/
│   ├── requirements.txt  requirements-dev.txt
│   └── Dockerfile
├── frontend/
│   ├── app/[locale]/                (landing) login register dashboard
│   │                                crop-recommendation  history  profile
│   ├── components/ui/               shadcn primitives
│   ├── components/crop/ farmer/ layout/
│   ├── lib/                         api-client.ts  auth.ts  i18n.ts  validation.ts
│   ├── hooks/  types/
│   ├── locales/en.json  hi.json  mr.json
│   └── package.json  Dockerfile
├── data/raw/  data/processed/
├── docs/                            DATASET_INSPECTION.md  PHASE1_PLAN.md  API.md  MODEL_CARD.md
├── scripts/inspect_dataset.py
├── docker-compose.yml  .env.example  .gitignore  README.md
```

**Two deliberate changes** from the structure in the spec, both justified:

1. **ML artifacts live in `app/ml/crop_recommendation/artifacts/`, not `models/`.**
   The spec's tree has `ml/.../models/` while the database entities also live in
   `models/`. Two different meanings of "models" in one backend is a permanent source
   of confusion and wrong imports. `artifacts/` is unambiguous.
2. **`training/` is never imported by the running API.** Training pulls pandas and the
   full sklearn training stack; inference needs only the loaded estimator. Keeping the
   boundary hard means the API container never has a code path that could retrain on a
   request — the failure mode §9 of the spec warns about, prevented structurally
   rather than by discipline.

Everything else follows the spec's tree.

## 3. Database design

PostgreSQL + SQLAlchemy 2.0 (typed `Mapped[]`) + Alembic. UUID primary keys
(`gen_random_uuid()`) so records can be created across future services without
sequence collisions. All timestamps `TIMESTAMPTZ`. Deletes are soft where a farmer
would expect their history to persist.

**`users`** — authentication and role only. No farmer-specific fields; the expert and
admin roles share this table.
`id · email (unique, citext) · mobile (unique, nullable) · password_hash · role (enum:
farmer|expert|admin) · is_active · is_verified · last_login_at · created_at · updated_at`

**`farmer_profiles`** — 1:1 with a `farmer` user.
`id · user_id (FK unique → users, cascade) · full_name · preferred_language (enum:
mr|hi|en, default mr) · state · district · taluka · village · pincode · latitude ·
longitude · created_at · updated_at`

Location is stored as **separate district/taluka/village columns plus optional
lat/long**, not a free-text blob — future weather and market modules need to join on
district, and retrofitting structure onto free text later is painful. PostGIS is not
introduced in Phase 1; two float columns are enough and can be migrated later.

**`farms`** — 1:N from a farmer profile. Optional in Phase 1: a farmer can get a
prediction without registering a farm.
`id · farmer_profile_id (FK) · name · area_value · area_unit (enum: acre|hectare|guntha) ·
soil_type (nullable) · irrigation_source (nullable) · latitude · longitude ·
created_at · updated_at`

Area is `value + unit`, not a single number. Maharashtra farmers use guntha and acre;
forcing hectares at input is how you get silently wrong data.

**`crop_predictions`** — the history table, and the audit record.
`id · farmer_profile_id (FK) · farm_id (FK, nullable) · input_n · input_p · input_k ·
input_temperature · input_humidity · input_ph · input_rainfall · recommended_crop ·
confidence (numeric, nullable) · alternatives (JSONB) · model_name · model_version ·
created_at`

Design decisions worth stating:
- **Inputs are stored as typed columns, not JSON.** They are a fixed, known feature set
  in Phase 1; typed columns give constraints, indexes, and straightforward analytics.
  A future module with variable inputs gets its own table.
- **`alternatives` is JSONB** — top-3 crops with probabilities. Variable-shape,
  read-whole, never queried by key. JSONB is correct here and wrong for the inputs.
- **`model_version` is mandatory on every row.** When v2 ships, "which model said
  this?" must be answerable for every historical prediction. This is the field that
  makes the whole artifact-versioning discipline meaningful.
- **`confidence` is nullable** — if a selected model has no meaningful probability
  output, the column is NULL and the UI omits it rather than showing a fabricated number.

Indexes: `crop_predictions(farmer_profile_id, created_at DESC)` for the history feed,
unique on `users.email`, FK indexes throughout.

Future tables (`disease_reports`, `expert_reviews`, `market_prices`, `weather_records`,
`fertilizer_recommendations`, `yield_predictions`, `schemes`, `notifications`,
`audit_logs`) attach to `farmer_profiles` / `farms` / `users` with the same conventions.
**None of them are created in Phase 1.**

## 4. ML pipeline

Findings are in [`DATASET_INSPECTION.md`](./DATASET_INSPECTION.md); this is what gets built.

**Training** (`ml/crop_recommendation/training/train.py`, run offline via
`python -m app.ml.crop_recommendation.training.train`):

1. Load `data/raw/Crop_recommendation.csv`; assert 8 expected columns, fail loudly otherwise.
2. Validate: no nulls, no infinities, no duplicates, 22 classes × 100 rows. **No row
   removal** — the inspection established that global outliers are legitimate members
   of extreme-requirement crops.
3. **Shuffled, stratified** 80/20 split, `random_state=42`. Non-negotiable: the CSV is
   sorted by class.
4. Fit `LabelEncoder` on the training split only.
5. Candidates, each as a `Pipeline(StandardScaler, estimator)` so preprocessing is
   fitted inside each CV fold — no leakage:
   LogisticRegression · GaussianNB · DecisionTree · RandomForest · XGBoost
   (XGBoost is evaluated; it is only kept as a dependency if it actually wins by a
   margin that matters, which on this data it will not).
6. 5-fold `StratifiedKFold` CV on the training split. **Primary metric: macro-F1**,
   with accuracy, macro precision, macro recall, per-class report, and confusion matrix
   all recorded.
7. Select the best model; **break ties toward the simpler model.** With four families
   inside 2.7 points, complexity that buys 0.3% is not worth the inference cost or the
   explanation burden.
8. Evaluate the chosen model **once** on the untouched holdout set. That number goes in
   the model card and nowhere else — it is not a tuning signal.
9. Persist `model.joblib`, `preprocessor.joblib`, `label_encoder.joblib`, and
   `metadata.json`:
   ```json
   {
     "model_name": "crop_recommendation",
     "model_version": "v1.0.0",
     "algorithm": "RandomForestClassifier",
     "trained_at": "<ISO-8601 UTC>",
     "dataset": {"file": "Crop_recommendation.csv", "sha256": "...", "n_rows": 2200, "n_classes": 22},
     "feature_names": ["N","P","K","temperature","humidity","ph","rainfall"],
     "target_name": "label",
     "classes": ["apple", "...", "watermelon"],
     "metrics": {"cv_macro_f1_mean": 0.0, "cv_macro_f1_std": 0.0, "holdout_accuracy": 0.0,
                 "holdout_macro_f1": 0.0, "holdout_precision_macro": 0.0, "holdout_recall_macro": 0.0},
     "input_ranges": {"N": [0, 140], "...": []},
     "library_versions": {"scikit-learn": "...", "numpy": "..."}
   }
   ```
   The dataset SHA-256 and library versions make a run reproducible and make "why did
   predictions change?" answerable. `input_ranges` is read by the API for validation —
   **one source of truth**, so the model's world and the validator's world cannot drift.

**Inference** (`inference/predictor.py`):
- Loads all four artifacts once at startup. Missing/corrupt → `ModelUnavailableError`,
  logged, app still starts, `/health` reports it, the predict endpoint returns a clean
  503.
- Builds the feature vector **by explicit name lookup against `metadata.feature_names`**,
  never by dict ordering. Silent feature reordering is the most expensive bug in this
  class of system; a positional bug here yields confident wrong answers with no error.
- Returns top-1 plus **top-3 alternatives** with probabilities, and the model version.
- Actual `predict_proba` vote fractions only. If a selected model lacks meaningful
  probabilities, confidence is returned as `null` — no fabrication, per §12.

**Honesty in the product.** The model card and the result UI both state plainly: high
benchmark accuracy comes from a clean, balanced, largely synthetic dataset and is not a
field-accuracy estimate. Result copy stays tied to the model output and general crop
information is clearly labelled as general — no invented agronomy.

## 5. Backend API

Versioned under `/api/v1`. Every response uses one envelope, so the frontend has
exactly one shape to handle:

```json
{ "success": true,  "data": { } }
{ "success": false, "error": { "code": "INVALID_INPUT", "message": "…",
                               "details": [{"field": "ph", "message": "…"}] } }
```

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/v1/health` | — | liveness + db + model status |
| POST | `/api/v1/auth/register` | — | farmer registration |
| POST | `/api/v1/auth/login` | — | returns access + refresh token |
| POST | `/api/v1/auth/refresh` | refresh | rotate access token |
| GET | `/api/v1/auth/me` | ✓ | current user + role |
| GET | `/api/v1/farmer/profile` | farmer | profile |
| PUT | `/api/v1/farmer/profile` | farmer | update profile / language |
| GET | `/api/v1/farmer/farms` | farmer | list farms |
| POST | `/api/v1/farmer/farms` | farmer | add farm |
| POST | `/api/v1/crop-recommendation/predict` | farmer | **the core endpoint** |
| GET | `/api/v1/crop-recommendation/history` | farmer | paginated history |
| GET | `/api/v1/crop-recommendation/history/{id}` | farmer | one prediction |
| GET | `/api/v1/modules` | ✓ | dashboard module registry |

Two additions to the spec's list, both small: `/auth/refresh` and `/auth/me` (a JWT
scheme without refresh forces either a very long token lifetime or constant re-login),
and `/modules` (the registry that makes "Coming Soon" tiles data rather than hardcoded
markup). Farms are included because `crop_predictions.farm_id` would otherwise be
permanently null.

**Validation** (`schemas/crop.py`, Pydantic v2) is mandatory server-side regardless of
what the frontend does:

| Field | Accepted range | Source |
|---|---|---|
| N | 0–140 | dataset observed range |
| P | 5–145 | dataset observed range |
| K | 5–205 | dataset observed range |
| temperature | 0–55 °C | widened beyond 8.8–43.7 to plausible physical range |
| humidity | 0–100 % | physical bound |
| ph | 0–14 | physical bound, warn outside 3.5–9.9 |
| rainfall | 0–500 mm | widened beyond 20–299 to plausible range |

Physical bounds are hard rejections. Values that are physically possible but **outside
the training range** are accepted and flagged `out_of_training_range` in the response —
the model is extrapolating and the farmer deserves to know, rather than silently
receiving a confident answer from a region the model never saw. NaN and infinity are
rejected explicitly (Pydantic's `allow_inf_nan=False`).

**Errors**: an `AppError` hierarchy mapped by exception handlers to the envelope above.
Codes: `INVALID_INPUT`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `MODEL_UNAVAILABLE`,
`PREDICTION_FAILED`, `DATABASE_UNAVAILABLE`, `INTERNAL_ERROR`. Stack traces go to the
structured log with a request id; the client gets the code, a safe message, and that id.

**Security**: bcrypt via passlib, JWT (HS256, short-lived access + refresh), role
dependency `require_role(...)`, CORS locked to configured origins, all secrets from
`.env` with `.env.example` committed and `.env` git-ignored, ORM-only queries.
Ownership is enforced in the service layer — `GET /history/{id}` must 404 for someone
else's prediction, not 403 (a 403 confirms the record exists).

Phase 1 uses **email + password**. Production SMS OTP is deliberately not built: no SMS
provider credentials exist, and per §18 no OTP gets hardcoded. The auth service is
structured so an OTP provider drops in behind the same interface.

## 6. Frontend

Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + Framer Motion. Mobile-first —
the realistic device is a mid-range Android phone on a patchy connection, so: large
touch targets, high contrast, minimal JS, no heavy animation.

| Route | Purpose |
|---|---|
| `/[locale]` | Landing — what AgriGuru does, in the farmer's language |
| `/[locale]/register` · `/login` | Auth |
| `/[locale]/dashboard` | Greeting, location, language selector, module cards |
| `/[locale]/crop-recommendation` | The 7-input form |
| `/[locale]/crop-recommendation/result` | Farmer-friendly result |
| `/[locale]/history` · `/history/[id]` | Past recommendations + detail |
| `/[locale]/profile` | Profile, farms, language |

**i18n**: locale as a route segment (`/mr/dashboard`) — shareable, indexable, and
correct on first paint with no flash of English. `mr` is the default. Three flat JSON
files (`en/hi/mr`), typed against the `en` keys so a missing Marathi string is a
**build error**, not a runtime blank. Language persists in the DB
(`farmer_profiles.preferred_language`) for logged-in farmers and a cookie for guests.
Zero hardcoded UI strings in components. Crop names are translated through the
dictionary, keyed by the model's English class name — the model never emits Marathi.

**The input form** is the farmer-facing surface, and §10 and §6.5 of the inspection
both land here. Each field shows a plain-language label (`माती मधील नायट्रोजन` /
"Soil Nitrogen"), a one-line explanation, the accepted range, and the unit **as the
dataset defines it**. N/P/K are labelled as soil-test ratio values with their range,
explicitly *not* kg/ha — mislabelling that unit is the most likely cause of a wrong
real-world prediction, and it is a UI bug, not a model bug. Values come only from
farmer input in Phase 1; the form is structured so weather/soil-test/profile
auto-fill can populate fields later, but **nothing is auto-filled with fake data now**.

**The result page** shows the recommended crop, confidence as a percentage with a
plain-language qualifier, the top-3 alternatives (per §6.4 of the inspection — a single
confident "apple" for a Nashik farmer is a credibility failure; showing it as one of
three is honest), a "why this recommendation" panel that restates *the farmer's own
inputs* and says the model matched them against trained patterns, a clear note that
this is a data-driven suggestion and not agronomic advice, and Save / View History.

**The dashboard** renders from `/api/v1/modules`: Crop Recommendation as
**Available Now**, Disease Detection / Weather / Market / Fertiliser as visibly
disabled **Coming Soon** cards. Coming-soon cards are not clickable.

## 7. Development sequence

Each step is verifiable before the next begins. Nothing moves forward on a broken step.

| # | Step | Done when |
|---|---|---|
| 0 | Dataset inspection | ✅ **complete** — this document + `DATASET_INSPECTION.md` |
| 1 | Repo skeleton, `.env.example`, docker-compose, README | `docker compose up` starts Postgres |
| 2 | Backend skeleton: config, logging, errors, `/health` | `/health` returns the envelope; OpenAPI renders |
| 3 | Database: models + first Alembic migration | `alembic upgrade head` creates 4 tables |
| 4 | Auth: register, login, refresh, me, roles | register → login → `/me` works; bad password 401 |
| 5 | Farmer profile + farms | profile round-trips; language persists |
| 6 | **Train the model** | artifacts + `metadata.json` written; metrics in the model card |
| 7 | Inference service | unit-tested: loads, correct feature order, rejects bad input |
| 8 | `POST /predict` + history endpoints | prediction saved and retrievable; ownership enforced |
| 9 | Frontend skeleton + i18n + auth pages | all three languages render; login persists |
| 10 | Dashboard + module registry | Coming Soon cards inert |
| 11 | Crop recommendation form + result | full flow in the browser |
| 12 | History UI | list + detail |
| 13 | End-to-end test + hardening | backend tests green; error paths verified |
| 14 | Docs: README, API.md, MODEL_CARD.md | a stranger can clone and run it |

Steps 1–5 build the foundation, 6–8 are the ML slice, 9–12 the farmer experience.
Step 6 can be done earlier if you would rather see model results first — it has no
dependency on the backend. **Say the word and I will reorder it.**

## 8. Dependencies

**Backend** (`requirements.txt`) — every entry justified, nothing speculative:
`fastapi` · `uvicorn[standard]` · `pydantic` · `pydantic-settings` (typed .env config) ·
`sqlalchemy>=2.0` · `alembic` · `psycopg[binary]` (actively maintained, unlike
psycopg2) · `passlib[bcrypt]` · `python-jose[cryptography]` (JWT) ·
`python-multipart` (form login) · `joblib` · `scikit-learn` · `numpy`

`pandas` and `matplotlib`/`seaborn` go in **`requirements-dev.txt`** with `pytest`,
`httpx`, `pytest-asyncio`, `ruff`, `mypy` — training and EDA only. The API container
has no reason to carry pandas. `xgboost` is added **only if step 6 shows it winning by
a margin that justifies the dependency**; on this dataset that is unlikely, and adding
it anyway would be exactly the "chose it because it's popular" §8 warns against.

**Frontend**: `next` · `react` · `typescript` · `tailwindcss` · shadcn/ui primitives
(`class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`) ·
`framer-motion` · `zod` (mirrors backend validation) · `react-hook-form` ·
`next-intl` (i18n) · `recharts` **deferred** — nothing in Phase 1 needs a chart yet;
it arrives with history analytics.

**Infra**: PostgreSQL 16, Docker + Compose.

## 9. Testing

**Backend** — `/health`; register/login/duplicate-email/wrong-password; each validation
boundary (below min, above max, NaN, infinity, missing field, wrong type); predict
happy path; predict without a token → 401; another farmer's history id → 404; model
unavailable → 503 with a clean envelope.

**ML** — artifacts load; `metadata.feature_names` matches the training feature order;
a known input predicts a stable class; probabilities sum to 1 and top-3 are ordered;
scrambled feature order produces a *different* result (proves order is enforced, not
coincidental).

**Frontend** — the flows that matter: register → login → dashboard, form submission
with validation errors, result rendering, language switch persisting across reload.

---

## 10. What I need from you before implementation starts

1. **Confirm the plan**, or tell me what to change.
2. **Structure changes** — the two deviations in §2 (`artifacts/` instead of `models/`,
   training excluded from the API import path). Both are justified above; say if you
   disagree.
3. **Top-3 alternatives on the result page** (§6.4 of the inspection). I recommend it
   strongly — it is the honest way to present a model that can suggest apple to a
   farmer in Nashik. Confirm, or say single-result-only.
4. **Step 6 ordering** — train the model at step 6 as listed, or move it to step 1 so
   you see real metrics before the app is built?
5. **Nothing needed from you on secrets.** No external API keys are required in
   Phase 1. When weather or SMS arrives, I will tell you exactly which `.env` values
   to supply and never invent one.
