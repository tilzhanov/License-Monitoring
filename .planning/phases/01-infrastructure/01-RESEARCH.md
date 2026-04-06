# Phase 1: Infrastructure - Research

**Researched:** 2026-04-06
**Domain:** FastAPI + SQLAlchemy + SQLite + Docker Compose project scaffolding
**Confidence:** HIGH

## Summary

Phase 1 is a greenfield scaffolding phase: create the project structure, Docker Compose configuration, SQLAlchemy models for `licenses` and `app_settings` tables, FastAPI application skeleton with lifespan-based DB initialization, and a placeholder index page. No existing code exists -- everything is created from scratch.

The stack is fully decided (FastAPI + Jinja2 + HTMX + SQLite + sync SQLAlchemy), so research focuses on verified current versions, correct configuration patterns, Docker Compose best practices for SQLite named volumes, and the `app_settings` bootstrap-from-env pattern. The notification/scheduler functionality is NOT part of this phase -- only the DB schema and app skeleton are needed.

**Primary recommendation:** Use pinned versions of all dependencies, sync SQLAlchemy `Session` with `def` routes, WAL mode via event listener, `Base.metadata.create_all()` in lifespan startup, and a named Docker volume for SQLite persistence.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Host port 8080. Port set via `APP_PORT` in `.env` (default 8080), docker-compose maps `${APP_PORT}:8080`.
- **D-02:** Container restart policy `unless-stopped`.
- **D-03:** SQLite volume -- named Docker volume (not bind-mount).
- **D-04:** Required fields (NOT NULL): `product_name`, `purchase_date`, `expiry_date`. Optional (nullable): `responsible`, `cost`, `comment`, `notify_days_before`.
- **D-05:** `cost` field is VARCHAR (text). User enters freeform: "1 500 000 tenge", "$5000/year". No numeric aggregation.
- **D-06:** Date fields (`purchase_date`, `expiry_date`) -- type DATE (date only, no time).
- **D-07:** `notify_days_before` (INTEGER, nullable) -- overrides global threshold per license. NULL = use global.
- **D-08:** `app_settings` table stores 4 settings: `telegram_bot_token`, `telegram_chat_id`, `notify_days_before` (global threshold, default 60), `notifications_enabled` (BOOLEAN, default true).
- **D-09:** On first startup: if `.env` contains `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, write them to `app_settings` as initial values (only when table is empty). Global threshold default is 60 days.
- **D-10:** Priority: `app_settings` (DB) always overrides `.env`. `.env` is bootstrap only.

### Claude's Discretion
- Exact `app_settings` structure (key-value table vs separate columns -- Claude chooses simpler option)
- Healthcheck endpoint format (/health -> {"status": "ok"} or just 200)
- Directory structure inside `app/`
- Module/file names

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Application starts via `docker-compose up` | Docker Compose config with named volume, Dockerfile with Python 3.12-slim, uvicorn CMD |
| INFRA-02 | Configuration via `.env` file: port, secrets, defaults | `.env.example` template, `env_file` in compose, `APP_PORT` variable expansion |
| INFRA-03 | SQLite as data store (file mounted as volume) | Named volume `licenses_db:/data`, `DB_PATH=/data/licenses.db`, WAL mode pragma |
| LIC-04 | License contains fields: product/system, purchase date, expiry date, responsible, cost, comment | SQLAlchemy `License` model with all columns per D-04 through D-07 |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.135.3 | Web framework | Verified latest on PyPI 2026-04-06 |
| uvicorn | 0.43.0 | ASGI server | Standard FastAPI production server |
| sqlalchemy | 2.0.49 | ORM / database toolkit | Verified latest; 2.0 style with `Mapped`/`mapped_column` |
| jinja2 | 3.1.6 | Template engine | Required by FastAPI `Jinja2Templates` |
| python-multipart | 0.0.24 | Form data parsing | Required for `request.form()` in FastAPI |
| httpx | 0.28.1 | HTTP client (for Telegram later) | Include now to avoid adding mid-project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| apscheduler | 3.11.2 | Job scheduler | Phase 4 -- but pin in requirements now for consistency |
| pytest | 9.0.2 | Test framework | Validation of models and routes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sync SQLAlchemy Session | async aiosqlite | No real async benefit for SQLite file I/O; adds complexity |
| `create_all()` | Alembic migrations | Overkill for greenfield; add when schema stabilizes and data preservation matters |
| Named Docker volume | Bind mount | Named volumes avoid host permission issues across different Linux hosts |

**Installation (requirements.txt):**
```
fastapi==0.135.3
uvicorn==0.43.0
sqlalchemy==2.0.49
jinja2==3.1.6
python-multipart==0.0.24
httpx==0.28.1
apscheduler==3.11.2
```

## Architecture Patterns

### Recommended Project Structure
```
License-Monitoring/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, router includes
│   ├── config.py            # Settings from env vars
│   ├── database.py          # Engine, SessionDep, create_db_tables
│   ├── models.py            # SQLAlchemy ORM models (License, AppSettings)
│   ├── routers/
│   │   ├── __init__.py
│   │   └── pages.py         # Placeholder index route (Phase 1)
│   └── templates.py         # Jinja2Templates singleton (avoids circular imports)
├── templates/
│   ├── base.html            # Base layout with HTMX CDN, nav
│   └── index.html           # Placeholder page (extends base)
├── static/
│   └── css/
│       └── app.css          # Minimal styles
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Test fixtures (in-memory SQLite engine, test client)
│   ├── test_models.py       # Model creation tests
│   └── test_health.py       # Health endpoint test
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── .dockerignore
```

**Key structural decisions:**
- `templates/` and `static/` at project root (not inside `app/`) -- simpler Docker COPY and path resolution
- `app/templates.py` as a single import point for the `Jinja2Templates` instance prevents circular imports when routers need templates
- `app/config.py` centralizes environment variable reads

### Pattern 1: Sync SQLAlchemy Session with FastAPI Dependency Injection

**What:** Use `def` routes (not `async def`) for all routes that touch the database. FastAPI automatically runs sync `def` routes in a thread pool.

**When to use:** Always, for this project -- SQLite has no async benefit.

```python
# app/database.py
import os
from typing import Annotated
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, DeclarativeBase
from fastapi import Depends

DB_PATH = os.getenv("DB_PATH", "/data/licenses.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=bool(os.getenv("SQL_ECHO", "").lower() == "true"),
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

class Base(DeclarativeBase):
    pass

def create_db_tables():
    Base.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
```

### Pattern 2: Lifespan for DB Init and Bootstrap

**What:** Use FastAPI `lifespan` context manager for startup tasks (create tables, bootstrap settings from env).

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import create_db_tables, engine, Base
from app.models import AppSettings  # ensure models are imported
from sqlalchemy.orm import Session
import os

def bootstrap_settings():
    """Write Telegram credentials from .env to app_settings on first run only."""
    with Session(engine) as db:
        existing = db.query(AppSettings).first()
        if existing is not None:
            return  # Table already has data, skip bootstrap

        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

        defaults = [
            AppSettings(key="telegram_bot_token", value=token),
            AppSettings(key="telegram_chat_id", value=chat_id),
            AppSettings(key="notify_days_before", value="60"),
            AppSettings(key="notifications_enabled", value="true"),
        ]
        db.add_all(defaults)
        db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_tables()
    bootstrap_settings()
    yield

app = FastAPI(lifespan=lifespan)
```

### Pattern 3: app_settings as Key-Value Table

**What:** Use a simple key-value table rather than separate columns. This is simpler to extend and query.

```python
# In app/models.py
class AppSettings(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
```

**Rationale:** Key-value is simpler than a single-row table with 4 columns. Adding new settings requires no schema migration. Reading a setting is `db.get(AppSettings, "key_name")`.

### Anti-Patterns to Avoid
- **Using `async def` for routes that call sync SQLAlchemy:** This blocks the event loop. Always use `def` for DB-touching routes.
- **Importing models after `create_all()`:** All model classes must be imported before `Base.metadata.create_all()` is called, or their tables will not be created. Import `app.models` in `main.py` before calling `create_db_tables()`.
- **Putting templates inside `app/` and using relative paths:** Leads to path confusion inside Docker. Keep templates at project root and use absolute or well-defined relative paths.
- **Forgetting `check_same_thread=False`:** Causes `ProgrammingError` because FastAPI routes can run in different threads.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form data parsing | Manual request body parsing | `python-multipart` + `request.form()` | FastAPI requires it; handles encoding edge cases |
| Template rendering | String concatenation | `Jinja2Templates` | Autoescaping, inheritance, fragment includes |
| DB session lifecycle | Manual `try/finally/close` | `get_session()` generator with `yield` | FastAPI `Depends` handles cleanup automatically |
| SQLite WAL mode | Manual PRAGMA in every function | SQLAlchemy `event.listens_for(engine, "connect")` | Runs once per connection, guaranteed |
| Health check | Custom TCP/socket check | FastAPI route + Docker healthcheck | Simple, standard, compose-integrated |

## Common Pitfalls

### Pitfall 1: Models Not Imported Before create_all()
**What goes wrong:** Tables are not created at startup. App starts, but first DB query fails with "no such table".
**Why it happens:** `Base.metadata.create_all()` only creates tables for models that have been imported and registered on `Base`.
**How to avoid:** In `main.py`, explicitly import `app.models` before the lifespan calls `create_db_tables()`. A single `from app.models import License, AppSettings` at module level is sufficient.
**Warning signs:** App starts without errors but first request returns 500.

### Pitfall 2: SQLite File Not Created in Docker Volume
**What goes wrong:** Database file is created in a non-mounted path and lost on container restart.
**Why it happens:** `DB_PATH` env var is not set or does not point to the volume mount point.
**How to avoid:** Hardcode `DB_PATH=/data/licenses.db` in docker-compose.yml `environment` section (not just in `.env`), and mount the named volume to `/data`.
**Warning signs:** Data disappears after `docker-compose restart`.

### Pitfall 3: uvicorn Internal Port Mismatch
**What goes wrong:** Container starts but is unreachable from host.
**Why it happens:** uvicorn listens on port 8000 but docker-compose maps to a different internal port.
**How to avoid:** Keep uvicorn on 8000 (hardcoded in Dockerfile CMD), and map `${APP_PORT:-8080}:8000` in docker-compose.yml. The internal port never needs to change.
**Warning signs:** `docker-compose up` succeeds but `curl localhost:8080` times out.

### Pitfall 4: .env File Committed to Git
**What goes wrong:** Secrets (Telegram token) leaked to repository.
**Why it happens:** `.gitignore` missing or `.env` added before `.gitignore`.
**How to avoid:** Create `.gitignore` with `.env` entry as the very first file. Commit `.env.example` (with placeholder values) instead.
**Warning signs:** `git status` shows `.env` as tracked.

### Pitfall 5: Docker Compose `version` Key Deprecation
**What goes wrong:** Warning messages on `docker compose up`.
**Why it happens:** Docker Compose v2+ ignores the `version:` key in compose files. It is deprecated.
**How to avoid:** Omit the `version:` key entirely from `docker-compose.yml`. Docker Compose v5.1.1 (installed on this machine) does not need it.
**Warning signs:** "version is obsolete" warning in compose output.

### Pitfall 6: Bootstrap Runs on Every Restart
**What goes wrong:** User-configured settings in DB are overwritten by `.env` values on restart.
**Why it happens:** Bootstrap check does not properly detect existing data.
**How to avoid:** Bootstrap function must check if ANY row exists in `app_settings` before writing. If at least one row exists, skip entirely. Per D-09, bootstrap only writes to an empty table.
**Warning signs:** Telegram settings revert to `.env` values after container restart.

## Code Examples

### License Model (per D-04 through D-07)

```python
# app/models.py
from datetime import date
from typing import Optional
from sqlalchemy import String, Date, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class License(Base):
    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    responsible: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cost: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # D-05: freeform text
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notify_days_before: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # D-07
    created_at: Mapped[date] = mapped_column(Date, default=date.today)
    updated_at: Mapped[date] = mapped_column(Date, default=date.today, onupdate=date.today)


class AppSettings(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
```

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/

RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
services:
  web:
    build: .
    ports:
      - "${APP_PORT:-8080}:8000"
    volumes:
      - licenses_db:/data
    env_file:
      - .env
    environment:
      - DB_PATH=/data/licenses.db
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  licenses_db:
    driver: local
```

### .env.example

```bash
# Application port (host-side)
APP_PORT=8080

# Database path (inside container, matches volume mount)
DB_PATH=/data/licenses.db

# Telegram bot credentials (bootstrap only -- DB takes priority after first run)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Global notification threshold in days (bootstrap default)
NOTIFY_DAYS_BEFORE=60

# SQL query logging (true/false)
SQL_ECHO=false
```

### .gitignore

```
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.db
*.sqlite3
.venv/
```

### Health Endpoint

```python
# app/routers/pages.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.templates import templates

router = APIRouter()

@router.get("/health")
def health():
    return JSONResponse({"status": "ok"})

@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
```

### Base Template

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}License Monitor{% endblock %}</title>
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
  <link rel="stylesheet" href="{{ url_for('static', path='/css/app.css') }}">
</head>
<body>
  <nav>
    <a href="/">License Monitor</a>
  </nav>
  <main>
    {% block content %}{% endblock %}
  </main>
</body>
</html>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93+ (2023) | `on_event` is deprecated; use `lifespan` always |
| SQLAlchemy 1.x `Column()` style | 2.0 `Mapped[]` + `mapped_column()` | SQLAlchemy 2.0 (2023) | Type-safe, better IDE support |
| `docker-compose.yml` with `version:` key | Omit `version:` entirely | Docker Compose v2+ (2023) | `version` is ignored and produces deprecation warning |
| HTMX 1.x | HTMX 2.0.4 | 2024 | Minor API changes; 2.x is current stable |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none -- Wave 0 creates `pytest.ini` or `pyproject.toml [tool.pytest]` |
| Quick run command | `docker compose exec web python -m pytest tests/ -x -q` |
| Full suite command | `docker compose exec web python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | `docker-compose up` starts the app | integration (manual) | `docker compose up -d && curl -sf http://localhost:8080/health` | -- Wave 0 |
| INFRA-02 | `.env.example` documents all vars; `.env` is gitignored | unit (file check) | `python -m pytest tests/test_config.py -x` | -- Wave 0 |
| INFRA-03 | SQLite DB created in volume, persists across restart | integration (manual) | `docker compose restart && curl -sf http://localhost:8080/health` | -- Wave 0 |
| LIC-04 | `licenses` table has all required columns | unit | `python -m pytest tests/test_models.py -x` | -- Wave 0 |

### Specific Validation Steps per Plan

**Plan 01-01 (Project structure, Dockerfile, docker-compose):**
- `docker compose build` completes without errors
- `docker compose up -d` starts container, reaches "healthy" state
- `curl http://localhost:8080/health` returns 200
- `.env` is listed in `.gitignore`
- `.env.example` contains all documented variables

**Plan 01-02 (Database layer -- models, engine, WAL, create_all):**
- Unit test: create in-memory SQLite engine, run `create_all()`, verify `licenses` table columns match spec (product_name, purchase_date, expiry_date, responsible, cost, comment, notify_days_before)
- Unit test: create in-memory engine, run `create_all()`, verify `app_settings` table has `key` and `value` columns
- Unit test: insert a `License` row with only required fields (product_name, purchase_date, expiry_date), verify nullable fields default to None
- Unit test: WAL mode is set -- connect to engine, execute `PRAGMA journal_mode`, assert result is "wal"
- Unit test: bootstrap_settings writes 4 rows to empty `app_settings`, skips if rows already exist

**Plan 01-03 (FastAPI app skeleton -- main.py, routes, templates):**
- Integration test with `TestClient`: GET `/health` returns 200 and `{"status": "ok"}`
- Integration test with `TestClient`: GET `/` returns 200 with HTML content
- Manual: `docker compose up -d`, open browser to `http://localhost:8080/`, verify placeholder page renders without 500

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q` (quick run)
- **Per wave merge:** `docker compose up -d && curl -sf http://localhost:8080/health && docker compose exec web python -m pytest tests/ -v`
- **Phase gate:** Full suite green + manual Docker restart persistence check

### Wave 0 Gaps
- [ ] `tests/__init__.py` -- package init
- [ ] `tests/conftest.py` -- shared fixtures (in-memory SQLite engine, TestClient)
- [ ] `tests/test_models.py` -- covers LIC-04 (column verification)
- [ ] `tests/test_health.py` -- covers INFRA-01 (app starts and responds)
- [ ] `tests/test_config.py` -- covers INFRA-02 (env var documentation check)
- [ ] `pytest` added to `requirements.txt` (dev dependency)

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Runtime | Yes (host) | 3.12.3 | Docker image `python:3.12-slim` is the actual runtime |
| Docker | Containerization | Yes | 29.3.1 | -- |
| Docker Compose | Orchestration | Yes | v5.1.1 | -- |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

All required tooling is available on the development machine.

## Open Questions

1. **HTMX version: 1.9.x vs 2.0.x**
   - What we know: HTMX 2.0 is the current stable line. STACK.md references 1.9.12. HTMX 2.0 has minor breaking changes (attribute defaults).
   - Recommendation: Use HTMX 2.0.4 (current stable) since this is a greenfield project with no legacy HTMX code. Pin the CDN version.

2. **`created_at` / `updated_at` columns on License**
   - What we know: Not in the user's field list (D-04), but standard for auditing. Phase 3 (DASH-05) mentions "history of changes".
   - Recommendation: Include `created_at` and `updated_at` timestamp columns now -- costs nothing, avoids schema migration later.

## Sources

### Primary (HIGH confidence)
- PyPI registry -- verified current versions of fastapi (0.135.3), sqlalchemy (2.0.49), uvicorn (0.43.0), jinja2 (3.1.6), httpx (0.28.1), apscheduler (3.11.2), python-multipart (0.0.24)
- Docker/Docker Compose -- verified installed versions (Docker 29.3.1, Compose v5.1.1)

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md` -- project-specific research from 2026-04-03, patterns verified against official FastAPI and SQLAlchemy documentation
- `.planning/research/NOTIFICATIONS.md` -- app_settings precedence pattern, bootstrap logic

### Tertiary (LOW confidence)
- HTMX 2.0.4 version recommendation -- based on training knowledge; CDN URL should be verified at implementation time

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against PyPI on 2026-04-06
- Architecture: HIGH -- patterns from project research (STACK.md) cross-checked with official FastAPI/SQLAlchemy docs
- Pitfalls: HIGH -- common issues well-documented in FastAPI and Docker communities
- Validation: MEDIUM -- test patterns are standard pytest but specific commands untested

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable stack, 30-day validity)
