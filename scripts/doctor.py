#!/usr/bin/env python3
"""AgriGuru AI setup doctor.

Checks every dependency the app needs and says exactly what is wrong and how
to fix it. Run it whenever something does not start:

    python scripts/doctor.py

Uses only the standard library, so it works before (and regardless of) the
backend virtualenv being set up.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
ENV_FILE = BACKEND / ".env"

GREEN, RED, YELLOW, BLUE, DIM, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[36m", "\033[2m", "\033[0m"
)
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    GREEN = RED = YELLOW = BLUE = DIM = RESET = ""

problems: list[str] = []

IS_WINDOWS = os.name == "nt"


def in_dir(directory: str, command: str) -> str:
    """Format a "cd X then run Y" instruction for the current shell.

    Windows PowerShell 5.1 (still the default on Windows 10/11) does not
    support `&&`, so a copy-pasted `cd backend && uvicorn ...` fails with a
    confusing parser error. Print two lines there instead.
    """
    if IS_WINDOWS:
        return f"cd {directory}\n         {command}"
    return f"cd {directory} && {command}"


def postgres_start_hint() -> str:
    if IS_WINDOWS:
        return (
            "start the PostgreSQL service:\n"
            '         Get-Service -Name "postgresql*"        # find the exact name\n'
            '         Start-Service -Name "postgresql-x64-16"  # then start it\n'
            "         (or open services.msc and start it there)"
        )
    if sys.platform == "darwin":
        return "start PostgreSQL:  brew services start postgresql@16"
    return (
        "start PostgreSQL:  sudo service postgresql start\n"
        "         (macOS: brew services start postgresql@16)"
    )


def ok(msg: str) -> None:
    print(f"  {GREEN}[ok]{RESET}   {msg}")


def fail(msg: str, fix: str) -> None:
    print(f"  {RED}[FAIL]{RESET} {msg}")
    print(f"         {YELLOW}fix:{RESET} {fix}")
    problems.append(msg)


def warn(msg: str, note: str = "") -> None:
    print(f"  {YELLOW}[warn]{RESET} {msg}")
    if note:
        print(f"         {DIM}{note}{RESET}")


def section(title: str) -> None:
    print(f"\n{BLUE}{title}{RESET}")


def read_env() -> dict[str, str]:
    """Parse backend/.env without needing python-dotenv installed."""
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_get(url: str, timeout: float = 5.0) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, str(e)


# --- 1. Configuration ---------------------------------------------------------

section("1. Configuration (backend/.env)")

env = read_env()

if not ENV_FILE.exists():
    fail(
        "backend/.env does not exist",
        "cp .env.example backend/.env   (then set SECRET_KEY, see below)",
    )
else:
    ok("backend/.env exists")

secret = env.get("SECRET_KEY", "")
if not secret:
    fail(
        "SECRET_KEY is not set",
        'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        "   then put it in backend/.env",
    )
elif "change-me" in secret.lower() or "your-secret" in secret.lower():
    fail(
        "SECRET_KEY is still the placeholder from .env.example",
        'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        "   then replace SECRET_KEY in backend/.env\n"
        "         (the backend REFUSES TO START with the placeholder, which is\n"
        "          why the app shows 'Cannot reach the server')",
    )
elif len(secret) < 32:
    fail(
        f"SECRET_KEY is too short ({len(secret)} chars, minimum 32)",
        'python -c "import secrets; print(secrets.token_urlsafe(48))"',
    )
else:
    ok(f"SECRET_KEY is set ({len(secret)} chars)")

cors = env.get("CORS_ORIGINS", "")
if cors:
    origins = [o.strip() for o in cors.split(",")]
    if "http://localhost:3000" in origins and "http://127.0.0.1:3000" in origins:
        ok(f"CORS_ORIGINS covers both dev hosts: {cors}")
    else:
        warn(
            f"CORS_ORIGINS = {cors}",
            "localhost and 127.0.0.1 are DIFFERENT origins to a browser. If you "
            "open the site on one and only the other is listed, every request is "
            "blocked and looks exactly like the server being down. Recommended: "
            "CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000",
        )

# --- 2. PostgreSQL ------------------------------------------------------------

section("2. PostgreSQL")

host = env.get("POSTGRES_HOST", "localhost")
port = int(env.get("POSTGRES_PORT", "5432") or 5432)
user = env.get("POSTGRES_USER", "agriguru")
password = env.get("POSTGRES_PASSWORD", "")
dbname = env.get("POSTGRES_DB", "agriguru")

if not port_open(host, port):
    fail(
        f"nothing is listening on {host}:{port}",
        postgres_start_hint(),
    )
else:
    ok(f"PostgreSQL is accepting connections on {host}:{port}")

    # Try a real authenticated connection, which is what the app does.
    psql = subprocess.run(
        ["psql", "-h", host, "-p", str(port), "-U", user, "-d", dbname,
         "-tAc", "SELECT current_user, current_database();"],
        capture_output=True,
        text=True,
        env={**os.environ, "PGPASSWORD": password, "PGCONNECT_TIMEOUT": "5"},
    )
    if psql.returncode == 0:
        who, db = (psql.stdout.strip().split("|") + ["", ""])[:2]
        ok(f"connected as '{who}' to database '{db}'")

        tables = subprocess.run(
            ["psql", "-h", host, "-p", str(port), "-U", user, "-d", dbname, "-tAc",
             "SELECT string_agg(tablename, ',' ORDER BY tablename) "
             "FROM pg_tables WHERE schemaname='public';"],
            capture_output=True, text=True,
            env={**os.environ, "PGPASSWORD": password, "PGCONNECT_TIMEOUT": "5"},
        )
        found = set((tables.stdout or "").strip().split(",")) - {""}
        expected = {"users", "farmer_profiles", "farms", "crop_predictions"}
        missing = expected - found
        if missing:
            fail(
                f"tables missing: {', '.join(sorted(missing))}",
                in_dir("backend", "alembic upgrade head"),
            )
        else:
            ok("all 4 Phase 1 tables exist")
    else:
        detail = psql.stderr.strip().splitlines()[-1] if psql.stderr.strip() else "unknown error"
        if "does not exist" in detail and "database" in detail:
            fail(f"database '{dbname}' does not exist",
                 f'psql -U postgres -c "CREATE DATABASE {dbname} OWNER {user};"')
        elif "role" in detail and "does not exist" in detail:
            fail(f"role '{user}' does not exist",
                 f"psql -U postgres -c \"CREATE USER {user} WITH PASSWORD '<your password>';\"")
        elif "authentication failed" in detail.lower() or "password" in detail.lower():
            # PostgreSQL deliberately does not say whether the role exists, so
            # this one message has to cover both causes.
            fail(f"authentication failed for '{user}'",
                 "either the role does not exist, or POSTGRES_PASSWORD in\n"
                 "         backend/.env does not match its password.\n"
                 f"         Create it:  psql -U postgres -c \"CREATE USER {user} "
                 "WITH PASSWORD '<password>';\"\n"
                 f"         Or reset:   psql -U postgres -c \"ALTER USER {user} "
                 "WITH PASSWORD '<password>';\"")
        else:
            fail(f"cannot connect: {detail}", "check POSTGRES_* values in backend/.env")

# --- 3. Model artifacts -------------------------------------------------------

section("3. Model artifacts")

artifacts = BACKEND / "app" / "ml" / "crop_recommendation" / "artifacts"
needed = ["model.joblib", "label_encoder.joblib", "metadata.json"]
missing_art = [n for n in needed if not (artifacts / n).exists()]
if missing_art:
    fail(
        f"missing artifacts: {', '.join(missing_art)}",
        in_dir("backend", "python -m app.ml.crop_recommendation.training.train")
        + "\n         (without these, login and history still work but "
        "predictions return 503)",
    )
else:
    meta = json.loads((artifacts / "metadata.json").read_text())
    ok(f"{meta['algorithm']} {meta['model_version']}, {len(meta['classes'])} crops")

# --- 4. Backend ---------------------------------------------------------------

section("4. Backend API (port 8000)")

if not port_open("127.0.0.1", 8000):
    fail(
        "nothing is listening on 127.0.0.1:8000 — the backend is NOT running",
        in_dir("backend", "uvicorn app.main:app --reload")
        + "\n         Run this in its OWN terminal and KEEP IT OPEN. The backend and\n"
        "         the frontend are two separate servers; both must stay running.\n"
        "         If it exits immediately, the error printed there is your real\n"
        "         problem (most often the SECRET_KEY placeholder checked above)."
        + (
            "\n         Activate the venv first: .\\.venv\\Scripts\\Activate.ps1"
            if IS_WINDOWS
            else ""
        ),
    )
else:
    status, body = http_get("http://127.0.0.1:8000/api/v1/health")
    if status == 0:
        fail(f"port 8000 is open but the health check failed: {body}",
             "check the uvicorn terminal for errors")
    else:
        try:
            data = json.loads(body)["data"]
            checks = data["checks"]
            ok(f"backend responding, status = {data['status']}")
            db_state = checks["database"]["status"]
            (ok if db_state == "available" else fail)(
                f"backend -> database: {db_state}",
                *([] if db_state == "available" else ["see the PostgreSQL section above"]),
            )
            model_state = checks["crop_recommendation_model"]["status"]
            if model_state == "available":
                ok(f"backend -> model: {checks['crop_recommendation_model']['algorithm']}")
            else:
                warn(f"backend -> model: {model_state}",
                     "predictions will return 503; train the model (section 3)")
        except (KeyError, ValueError):
            fail(f"unexpected health response: {body[:200]}", "check the uvicorn terminal")

# --- 5. Frontend --------------------------------------------------------------

section("5. Frontend (port 3000)")

if not port_open("127.0.0.1", 3000):
    warn("nothing is listening on 127.0.0.1:3000",
         "start it in a SECOND terminal: " + in_dir("frontend", "npm run dev"))
else:
    ok("frontend is running on port 3000")

api_base = None
for candidate in (FRONTEND / ".env.local", FRONTEND / ".env"):
    if candidate.exists():
        for line in candidate.read_text().splitlines():
            if line.startswith("NEXT_PUBLIC_API_BASE_URL="):
                api_base = line.split("=", 1)[1].strip()
if api_base:
    ok(f"NEXT_PUBLIC_API_BASE_URL = {api_base}")
    if not api_base.rstrip("/").endswith("/api/v1"):
        fail(f"API base URL should end with /api/v1, got {api_base}",
             "set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 in frontend/.env.local")
else:
    warn("no NEXT_PUBLIC_API_BASE_URL found in frontend/.env.local",
         "defaults to http://localhost:8000/api/v1, which is usually correct")

# --- summary ------------------------------------------------------------------

print()
if problems:
    print(f"{RED}{len(problems)} problem(s) found:{RESET}")
    for p in problems:
        print(f"  - {p}")
    print(f"\n{DIM}Fix these in order — earlier ones often cause the later ones.{RESET}")
    sys.exit(1)

print(f"{GREEN}Everything checks out.{RESET}")
print(f"{DIM}If registration still fails, open your browser devtools -> Network tab,{RESET}")
print(f"{DIM}submit the form, and look at the /auth/register request.{RESET}")
sys.exit(0)
