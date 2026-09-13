# API Reference — v1

Base URL: `http://localhost:8000/api/v1`
Interactive docs: `/api/v1/docs` (Swagger) · `/api/v1/redoc` · `/api/v1/openapi.json`

## Response envelope

Every endpoint returns one of two shapes, so the client has exactly one
success contract and one error contract to handle.

**Success**
```json
{ "success": true, "data": { } }
```

**Paginated success** (history list only)
```json
{ "success": true, "data": [], "meta": { "total": 12, "limit": 20, "offset": 0, "has_more": false } }
```

**Error**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "Some of the values you entered are not valid. Please check and try again.",
    "details": [{ "field": "ph", "message": "Input should be less than or equal to 14" }],
    "request_id": "b1d063f1-5b15-4f26-b011-068745e7881c"
  }
}
```

`code` is the contract — clients map it to a message in the farmer's language.
`message` is English and is a fallback, not something to show directly in a
localised UI. `request_id` also appears in the `X-Request-ID` response header
and in the server logs, which is how a support report is traced.

### Error codes

| Code | HTTP | Meaning |
|---|---|---|
| `INVALID_INPUT` | 422 | Validation failed; `details` names the fields |
| `UNAUTHORIZED` | 401 | Missing, expired or invalid token |
| `FORBIDDEN` | 403 | Authenticated but not permitted |
| `NOT_FOUND` | 404 | No such resource, **or** it belongs to someone else |
| `CONFLICT` | 409 | Email or mobile already registered |
| `MODEL_UNAVAILABLE` | 503 | Model artifacts missing; other features still work |
| `PREDICTION_FAILED` | 500 | Inference failed |
| `DATABASE_UNAVAILABLE` | 503 | Database unreachable |
| `INTERNAL_ERROR` | 500 | Unexpected; details are in the logs only |

`NOT_FOUND` is returned for another farmer's record rather than `FORBIDDEN`,
because a 403 would confirm that the record exists.

## Authentication

Bearer JWT: `Authorization: Bearer <access_token>`.

Access tokens are short-lived (default 60 min); refresh tokens last 30 days.
Both carry a `type` claim, and the server rejects a refresh token presented as
an access token — without that check, a long-lived refresh token would work
anywhere an access token does.

> **Phase 1 token storage.** The frontend keeps tokens in `localStorage`.
> httpOnly cookies are stronger against XSS, but need the API and frontend on
> one origin (or configured `SameSite` plus CSRF protection). That is a
> deployment decision for Phase 2, recorded here rather than left implicit.

---

## Endpoints

### `GET /health`
No auth. Reports each dependency separately.

```json
{ "success": true, "data": {
    "status": "ok",
    "environment": "development",
    "checks": {
      "database": { "status": "available" },
      "crop_recommendation_model": {
        "status": "available", "model_version": "v1.0.0", "algorithm": "RandomForest"
      }
    }
} }
```

`status` is `ok`, `degraded` (model unavailable, everything else fine) or
`down` (database unreachable; returns HTTP 503). A missing model is
deliberately *not* `down` — login and history still work.

### `POST /auth/register` → 201
```json
{ "email": "ramesh@example.com", "password": "Shetkari123", "full_name": "Ramesh Patil",
  "mobile": "9876543210", "preferred_language": "mr", "district": "Nashik" }
```
`password`: 8–72 bytes, at least one letter and one digit. `mobile` optional,
10-digit Indian format. Creates the user and farmer profile in one transaction.
Returns user, profile and a token pair.

### `POST /auth/login`
```json
{ "email": "ramesh@example.com", "password": "Shetkari123" }
```
Returns the same shape as register. The response is identical for an unknown
email and a wrong password, and a hash comparison runs either way, so login
cannot be used to enumerate accounts.

### `POST /auth/refresh`
```json
{ "refresh_token": "eyJ..." }
```

### `GET /auth/me` · auth
Current user, name, preferred language, and whether a farmer profile exists.

### `GET /farmer/profile` · farmer
### `PUT /farmer/profile` · farmer
Partial update — only the fields present in the body are changed. Omitted
fields keep their stored value; send `null` to clear one.
```json
{ "preferred_language": "hi", "district": "Nashik", "pincode": "422001" }
```

### `GET /farmer/farms` · farmer
### `POST /farmer/farms` · farmer → 201
```json
{ "name": "Mala che shet", "area_value": 2.5, "area_unit": "guntha", "soil_type": "black" }
```
`area_unit` is one of `acre`, `hectare`, `guntha`. Area is stored as value +
unit rather than normalised, because forcing hectares at input is how you
collect silently wrong data from farmers who think in guntha.

### `POST /crop-recommendation/predict` · farmer

```json
{ "nitrogen": 90, "phosphorus": 42, "potassium": 43,
  "temperature": 20.9, "humidity": 82.0, "ph": 6.5, "rainfall": 202.9,
  "farm_id": null }
```

**N, P and K are unitless soil-test ratio values, not kg/ha.** A value taken
straight from a soil health card is on a different scale.

| Field | Accepted | Model trained on |
|---|---|---|
| `nitrogen` | 0 – 200 | 0 – 140 |
| `phosphorus` | 0 – 200 | 5 – 145 |
| `potassium` | 0 – 250 | 5 – 205 |
| `temperature` | 0 – 55 °C | 8.8 – 43.7 |
| `humidity` | 0 – 100 % | 14.3 – 100 |
| `ph` | 0 – 14 | 3.5 – 9.9 |
| `rainfall` | 0 – 500 mm | 20.2 – 298.6 |

Values outside the *accepted* range are rejected (422). Values inside accepted
but outside *trained on* are accepted and listed in `out_of_training_range` —
the model is extrapolating and the caller is told, rather than being handed a
silently confident answer. NaN and ±Infinity are rejected explicitly.

**Response**
```json
{ "success": true, "data": { "prediction": {
    "id": "9f3b…", "recommended_crop": "rice", "confidence": 0.95,
    "alternatives": [{ "crop": "jute", "probability": 0.05 }],
    "model_name": "crop_recommendation", "model_version": "v1.0.0",
    "created_at": "2026-09-13T10:08:00Z",
    "inputs": { "nitrogen": 90.0, "…": 0 },
    "out_of_training_range": []
} } }
```

`recommended_crop` is the English class name from the model; the frontend
translates it. `confidence` is the forest's vote fraction — real, but it
measures tree agreement on the training distribution, **not** the probability
that the crop will succeed. It can be `null` if a model without meaningful
probabilities is ever deployed; clients must handle that rather than assume a
number. `alternatives` may be empty when the model puts all mass on one class.

### `GET /crop-recommendation/history?limit=20&offset=0` · farmer
Newest first, scoped to the caller. `limit` 1–100.

### `GET /crop-recommendation/history/{id}` · farmer
Full record including inputs. Another farmer's id returns 404.

### `GET /crop-recommendation/model-info` · farmer
Which model is serving, its metrics, the crop list, input ranges, and the
honesty caveat — so the caveat travels with the numbers instead of being
lost in a README.

### `GET /modules` · auth
Drives the dashboard. Each entry is `{ key, icon, status, route, phase }` with
`status` of `available` or `coming_soon`. A `coming_soon` module always has
`route: null`, so the UI cannot link to a feature that does not exist.
Activating a future module is a status change here, not a frontend rewrite.
