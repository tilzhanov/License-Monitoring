# Technology Stack Research: License Monitoring Dashboard

**Project:** Internal license monitoring dashboard for cloud infrastructure team
**Stack:** Python FastAPI + HTMX + Jinja2 + SQLite + APScheduler + Docker Compose
**Researched:** 2026-04-03
**Sources:** FastAPI official docs (verified), SQLAlchemy 2.0 docs, training knowledge (labeled by confidence)

---

## 1. FastAPI + Jinja2 + HTMX Patterns

### Setup (HIGH confidence — verified against FastAPI official docs)

```python
# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
```

`TemplateResponse` always requires `request` in its arguments. Pass it explicitly:

```python
@app.get("/licenses", response_class=HTMLResponse)
async def list_licenses(request: Request, db: SessionDep):
    licenses = db.exec(select(License)).all()
    return templates.TemplateResponse(
        request=request,
        name="licenses/list.html",
        context={"licenses": licenses},
    )
```

### HTMX Partial Response Pattern (MEDIUM confidence — HTMX docs not directly accessible, based on training + community patterns)

The core HTMX pattern for server-rendered apps: every route that can be triggered by HTMX should detect `HX-Request` header and return only the changed fragment, not the full page.

```python
@app.get("/licenses/{id}/edit", response_class=HTMLResponse)
async def edit_license_form(request: Request, id: int, db: SessionDep):
    license = db.get(License, id)
    # If HTMX request, return only the form fragment
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request=request,
            name="licenses/_edit_row.html",
            context={"license": license},
        )
    # Full page fallback for direct browser nav
    return templates.TemplateResponse(
        request=request,
        name="licenses/detail.html",
        context={"license": license},
    )
```

### Inline Table Row Editing Pattern

This is the standard HTMX pattern for inline editing in a table. It requires two template fragments:

**`templates/licenses/_row.html`** — read-only row:
```html
<tr id="license-row-{{ license.id }}">
  <td>{{ license.name }}</td>
  <td>{{ license.expires_at }}</td>
  <td>
    <button
      hx-get="/licenses/{{ license.id }}/edit"
      hx-target="#license-row-{{ license.id }}"
      hx-swap="outerHTML"
    >Edit</button>
  </td>
</tr>
```

**`templates/licenses/_edit_row.html`** — inline edit form:
```html
<tr id="license-row-{{ license.id }}">
  <form
    hx-put="/licenses/{{ license.id }}"
    hx-target="#license-row-{{ license.id }}"
    hx-swap="outerHTML"
  >
    <td><input name="name" value="{{ license.name }}"></td>
    <td><input type="date" name="expires_at" value="{{ license.expires_at }}"></td>
    <td>
      <button type="submit">Save</button>
      <button
        hx-get="/licenses/{{ license.id }}/row"
        hx-target="#license-row-{{ license.id }}"
        hx-swap="outerHTML"
      >Cancel</button>
    </td>
  </form>
</tr>
```

**PUT route returns the updated read-only row:**
```python
@app.put("/licenses/{id}", response_class=HTMLResponse)
async def update_license(request: Request, id: int, db: SessionDep):
    form = await request.form()
    license = db.get(License, id)
    license.name = form["name"]
    license.expires_at = form["expires_at"]
    db.commit()
    db.refresh(license)
    return templates.TemplateResponse(
        request=request,
        name="licenses/_row.html",
        context={"license": license},
    )
```

### Adding Rows Without Full Page Reload

For new record submission that appends to an existing table:

```html
<!-- In the table body -->
<tbody id="license-table-body">
  {% for license in licenses %}
    {% include "licenses/_row.html" %}
  {% endfor %}
</tbody>

<!-- Add form, outside the table -->
<form
  hx-post="/licenses"
  hx-target="#license-table-body"
  hx-swap="beforeend"
>
  <input name="name" placeholder="License name">
  <input type="date" name="expires_at">
  <button type="submit">Add</button>
</form>
```

The POST route returns only the new `<tr>` fragment:
```python
@app.post("/licenses", response_class=HTMLResponse)
async def create_license(request: Request, db: SessionDep):
    form = await request.form()
    license = License(name=form["name"], expires_at=form["expires_at"])
    db.add(license)
    db.commit()
    db.refresh(license)
    return templates.TemplateResponse(
        request=request,
        name="licenses/_row.html",
        context={"license": license},
    )
```

### Key HTMX Attributes Reference (MEDIUM confidence)

| Attribute | Purpose |
|-----------|---------|
| `hx-get` / `hx-post` / `hx-put` / `hx-delete` | HTTP method to use |
| `hx-target` | CSS selector for the element to update |
| `hx-swap` | How to swap content: `innerHTML`, `outerHTML`, `beforeend`, `afterend`, `delete` |
| `hx-trigger` | When to fire: `click` (default), `change`, `submit`, `keyup delay:500ms` |
| `hx-include` | Include additional form fields in request |
| `hx-indicator` | Element to show while request is in flight (spinner) |
| `hx-push-url` | Update browser URL bar after swap |
| `hx-confirm` | Show browser confirm dialog before request |
| `hx-boost` | Upgrade all `<a>` and `<form>` to AJAX without attributes |

**Response headers** the server can send to control HTMX behavior:
- `HX-Redirect`: Force full page redirect
- `HX-Retarget`: Override `hx-target` from server side
- `HX-Trigger`: Fire a client-side event after response
- `HX-Refresh`: Force full page refresh

### HTMX Delete Pattern

```html
<button
  hx-delete="/licenses/{{ license.id }}"
  hx-target="#license-row-{{ license.id }}"
  hx-swap="delete"
  hx-confirm="Delete this license?"
>Delete</button>
```

Server returns empty 200 or uses `hx-swap="delete"` to remove the row with no response body needed.

### Gotchas

- **Form PUT/DELETE methods**: HTML forms only support GET and POST. HTMX handles PUT/DELETE natively — use `hx-put` / `hx-delete` on the form, not a hidden `_method` field.
- **Fragment template inheritance**: Jinja2 fragments used as partials should NOT `{% extends "base.html" %}`. Keep them as bare HTML fragments.
- **`hx-swap="outerHTML"` requires the target to have an `id`**: If you swap the outer element, you lose the reference. Always ensure the replacement HTML includes the same `id`.
- **CSRF**: HTMX sends all requests as AJAX, but browsers still enforce same-origin. For an internal-only tool with no auth, this is fine. If you add sessions later, use `hx-headers` to inject a CSRF token.

---

## 2. SQLAlchemy + SQLite for FastAPI

### Async vs Sync Decision (HIGH confidence — documented FastAPI recommendation)

**Recommendation: Use synchronous SQLAlchemy with SQLite for this project.**

FastAPI supports both, but async SQLAlchemy with SQLite has a meaningful gotcha: `aiosqlite` (the async SQLite driver) runs all I/O through a single thread pool under the hood anyway. There is no true async benefit for SQLite — it's a file, not a network socket. The complexity cost of async SQLAlchemy (asyncpg session patterns, `AsyncSession`, `async with`) is not worth it for an internal dashboard with low concurrency.

Use `create_engine` with sync `Session` and wrap database routes in `run_in_executor` if needed, or simply accept that FastAPI will run sync database operations in a thread pool (FastAPI does this automatically when you use `def` routes instead of `async def`).

**Use `def` (not `async def`) for routes that touch the database:**
```python
# Correct: FastAPI runs this in a thread pool automatically
@app.get("/licenses")
def list_licenses(db: SessionDep):
    return db.exec(select(License)).all()

# Avoid: This blocks the event loop if using sync SQLAlchemy
async def list_licenses(db: SessionDep):
    ...
```

### SQLAlchemy 2.0 Model Definition (HIGH confidence — verified against SQLAlchemy docs)

```python
# app/models.py
from datetime import date
from typing import Optional
from sqlalchemy import String, Date, Integer, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

class Base(DeclarativeBase):
    pass

class License(Base):
    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor: Mapped[Optional[str]] = mapped_column(String(255))
    expires_at: Mapped[date] = mapped_column(Date, nullable=False)
    seat_count: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(String(1000))
```

### Engine Configuration for SQLite + Docker

```python
# app/database.py
import os
from typing import Annotated
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import Depends
from app.models import Base

# Use an env var so Docker volume path is configurable
DB_PATH = os.getenv("DB_PATH", "/data/licenses.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite with FastAPI
    echo=False,  # Set True for SQL query logging during development
)

def create_db_tables():
    Base.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
```

`check_same_thread=False` is mandatory because FastAPI routes can run in different threads. Without it, SQLite raises `ProgrammingError: SQLite objects created in a thread can only be used in that same thread`.

### Alembic vs Simple Schema Init (MEDIUM confidence)

**Recommendation: Start with `Base.metadata.create_all()` on startup. Add Alembic only when the schema stabilizes and you need to preserve data across schema changes.**

For a new internal tool:
- `create_all()` is zero-config, runs at startup, idempotent (won't drop existing tables)
- Alembic adds meaningful complexity: `alembic.ini`, `env.py`, migration scripts, version table
- The tradeoff shifts when you first need to alter an existing column or add a column to a live database with real data

**Call `create_db_tables()` inside the lifespan startup:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_tables()  # Runs once at startup
    yield

app = FastAPI(lifespan=lifespan)
```

**Alembic setup when you need it:**
```bash
pip install alembic
alembic init alembic
# Edit alembic/env.py: set target_metadata = Base.metadata
# Edit alembic.ini: set sqlalchemy.url = sqlite:////data/licenses.db
alembic revision --autogenerate -m "add_seat_count"
alembic upgrade head
```

Gotcha: Alembic autogenerate does not detect all changes (e.g., column type changes on SQLite are difficult because SQLite does not support `ALTER COLUMN`). For SQLite schema evolution, sometimes dropping and recreating the table is the only path.

### SQLite + Docker Volume Mounting

Mount a named volume to a fixed path inside the container. Set `DB_PATH` via environment variable so it points to the mounted path:

```yaml
# docker-compose.yml
volumes:
  - licenses_db:/data

environment:
  - DB_PATH=/data/licenses.db
```

The `/data` directory is inside the container. The `licenses_db` Docker volume persists across container restarts and rebuilds.

**Gotcha:** SQLite WAL mode is recommended for containerized deployments. Enable it once per connection:
```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()
```

WAL mode allows concurrent reads while a write is in progress, which matters even for a single-container app with a scheduler running alongside the web server.

---

## 3. APScheduler in FastAPI

### Version Selection (MEDIUM confidence)

There are two major APScheduler API versions in active use:

- **APScheduler 3.x**: Stable, widely documented, synchronous-first API. Use `BackgroundScheduler` for embedding in a web app.
- **APScheduler 4.x**: Async-native rewrite, still maturing (released ~2024). Preferred for pure async apps.

**Recommendation: Use APScheduler 3.x (`apscheduler>=3.10,<4`)** for this project. It is more stable, better documented, and straightforward to integrate with a sync-leaning FastAPI app.

```bash
pip install "apscheduler>=3.10,<4"
```

### Integration via Lifespan (HIGH confidence for the lifespan pattern, MEDIUM for APScheduler specifics)

Integrate APScheduler using the `lifespan` context manager (the modern FastAPI approach, replacing deprecated `@app.on_event`):

```python
# app/main.py
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import create_db_tables, engine
from app.notifications import send_expiry_notifications

scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_db_tables()
    scheduler.add_job(
        send_expiry_notifications,
        trigger=CronTrigger(hour=9, minute=0),  # 09:00 daily
        id="daily_expiry_check",
        replace_existing=True,
    )
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
```

### Notification Job Design

```python
# app/notifications.py
import os
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import date, timedelta
from app.database import engine
from app.models import License

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NOTIFY_DAYS_BEFORE = int(os.getenv("NOTIFY_DAYS_BEFORE", "30"))

def send_expiry_notifications():
    """Called by APScheduler. Creates its own DB session (not injected)."""
    threshold = date.today() + timedelta(days=NOTIFY_DAYS_BEFORE)
    with Session(engine) as db:
        expiring = db.exec(
            select(License).where(License.expires_at <= threshold)
        ).all()
    
    if not expiring:
        return

    lines = [f"*License Expiry Alert*\n"]
    for lic in expiring:
        days_left = (lic.expires_at - date.today()).days
        lines.append(f"- {lic.name}: expires in {days_left} days ({lic.expires_at})")
    
    message = "\n".join(lines)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    httpx.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
```

**Key design decision:** The scheduled job creates its own `Session` directly from `engine`. It cannot use FastAPI's `Depends(get_session)` injection because it runs outside of a request context.

### Gotchas

- **`BackgroundScheduler` runs in a daemon thread**: It will terminate when the main process exits. The `scheduler.shutdown(wait=False)` in the lifespan teardown prevents blocking on in-progress jobs during shutdown.
- **Duplicate scheduler starts**: If you use `uvicorn --reload` in development, the lifespan runs twice (in the reloader parent and the worker). This causes two schedulers to run simultaneously, doubling notification sends. Disable `--reload` or add a guard. In production with Docker this is not an issue.
- **Time zones**: By default APScheduler uses local time. Set `timezone` explicitly:
  ```python
  from pytz import timezone
  scheduler = BackgroundScheduler(timezone=timezone("Europe/Moscow"))
  ```
- **Missed jobs on restart**: If the container restarts at exactly 09:00, the job may be missed. APScheduler 3.x `BackgroundScheduler` has `misfire_grace_time` (default 1 second). For a notification job, consider setting it higher or using `coalesce=True`:
  ```python
  scheduler.add_job(
      ...,
      misfire_grace_time=3600,  # Fire if missed by up to 1 hour
      coalesce=True,            # Run once even if multiple misfires occurred
  )
  ```

---

## 4. Project Structure

### Recommended Directory Layout

```
license-monitor/
├── app/
│   ├── __init__.py
│   ├── main.py             # App factory, lifespan, router includes
│   ├── database.py         # Engine, SessionDep, create_db_tables
│   ├── models.py           # SQLAlchemy ORM models
│   ├── notifications.py    # APScheduler job functions
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── licenses.py     # CRUD routes for licenses
│   │   └── dashboard.py    # Main dashboard / index routes
│   └── templates/
│       ├── base.html       # Base layout (nav, head, htmx CDN include)
│       ├── dashboard/
│       │   └── index.html
│       └── licenses/
│           ├── list.html           # Full page: table + add form
│           ├── _row.html           # Fragment: single read-only <tr>
│           ├── _edit_row.html      # Fragment: single editable <tr>
│           └── _add_form.html      # Fragment: add new license form
├── static/
│   ├── css/
│   │   └── app.css
│   └── js/
│       └── (optional custom JS)
├── alembic/                # Add later when schema stabilizes
│   ├── env.py
│   └── versions/
├── alembic.ini             # Add later
├── Dockerfile
├── docker-compose.yml
├── .env                    # Local secrets (not committed)
├── .env.example            # Template for .env (committed)
├── requirements.txt
└── pyproject.toml          # Optional: tool config (ruff, mypy)
```

### main.py Skeleton

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import create_db_tables, engine
from app.notifications import send_expiry_notifications
from app.routers import licenses, dashboard

scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_tables()
    scheduler.add_job(
        send_expiry_notifications,
        trigger=CronTrigger(hour=9, minute=0),
        id="daily_expiry_check",
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates are accessed from routers via dependency or global
# Simplest: make templates a module-level object in a shared module
from app.templates import templates  # see below

app.include_router(dashboard.router)
app.include_router(licenses.router, prefix="/licenses")
```

```python
# app/templates.py — single import point for templates
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="app/templates")
```

This prevents circular imports when routers need `templates`.

### Router Example

```python
# app/routers/licenses.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.database import SessionDep
from app.templates import templates
from app.models import License
from sqlalchemy import select

router = APIRouter(tags=["licenses"])

@router.get("/", response_class=HTMLResponse)
def list_licenses(request: Request, db: SessionDep):
    licenses = db.execute(select(License).order_by(License.expires_at)).scalars().all()
    return templates.TemplateResponse(
        request=request,
        name="licenses/list.html",
        context={"licenses": licenses},
    )
```

### Template Inheritance Pattern

```html
<!-- app/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{% block title %}License Monitor{% endblock %}</title>
  <script src="https://unpkg.com/htmx.org@1.9.12"></script>
  <link rel="stylesheet" href="{{ url_for('static', path='/css/app.css') }}">
</head>
<body>
  <nav><!-- navigation --></nav>
  <main>
    {% block content %}{% endblock %}
  </main>
</body>
</html>
```

```html
<!-- app/templates/licenses/list.html -->
{% extends "base.html" %}
{% block content %}
<table>
  <tbody id="license-table-body">
    {% for license in licenses %}
      {% include "licenses/_row.html" %}
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

Fragment templates (`_row.html`, `_edit_row.html`) do NOT extend base. They are bare HTML snippets returned as HTMX partial responses.

---

## 5. Docker Compose Setup

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create data directory (will be overridden by volume mount)
RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
# docker-compose.yml
version: "3.9"

services:
  web:
    build: .
    ports:
      - "${HOST_PORT:-8080}:8000"
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

### .env.example (commit this)

```bash
# .env.example — copy to .env and fill in values
HOST_PORT=8080
DB_PATH=/data/licenses.db

TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
NOTIFY_DAYS_BEFORE=30

# Optional: "true" to enable SQL echo logging
SQL_ECHO=false
```

### Health Check Endpoint

Add a simple health route so Docker's healthcheck can verify the app is up:

```python
# app/routers/health.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/health")
def health():
    return JSONResponse({"status": "ok"})
```

### Docker Compose Gotchas

- **Volume ownership**: The `/data` directory in the container is owned by root by default. If you switch to a non-root user in the Dockerfile (recommended for security), ensure the volume is owned correctly:
  ```dockerfile
  RUN useradd -m appuser && chown appuser /data
  USER appuser
  ```
- **`env_file` vs `environment`**: `env_file` loads all variables from `.env`. `environment` can override specific ones. `DB_PATH` is set explicitly under `environment` so it is not accidentally overridden by a typo in `.env`.
- **No bind-mount for code in production**: Use a named volume for the database, not a bind-mount (`./data:/data`). Named volumes are portable and do not depend on the host directory structure. Use bind-mounts only in development for hot-reloading.
- **Static files and templates are baked into the image**: They are copied via `COPY app/ ./app/`. Do not mount them at runtime unless doing active development. Use a bind-mount override in a `docker-compose.override.yml` for dev.
- **`.env` file must not be committed**: Add `.env` to `.gitignore`. Commit only `.env.example`.
- **Port conflicts**: Parameterize the host port with `${HOST_PORT:-8080}` so it is configurable without editing the Compose file.

### Development Compose Override (optional)

```yaml
# docker-compose.override.yml — for local development only, not committed
services:
  web:
    volumes:
      - ./app:/app/app  # Hot-reload templates and code
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - SQL_ECHO=true
```

---

## Summary of Key Decisions

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Async vs Sync SQLAlchemy | Sync (`Session`) | SQLite has no async benefit; sync is simpler |
| Schema migration | `create_all()` at startup | Zero-config for new project; add Alembic when schema stabilizes |
| APScheduler version | 3.x (`BackgroundScheduler`) | Stable, well-documented, sync-compatible |
| APScheduler integration | `lifespan` context manager | Modern FastAPI pattern; replaces deprecated `@app.on_event` |
| Template fragments | Separate `_partial.html` files | Do not extend base; return as bare HTML from HTMX routes |
| HTMX CDN vs local | Pinned CDN version (`@1.9.12`) | Simple; pin the version to avoid surprise upgrades |
| SQLite WAL mode | Enable via `PRAGMA journal_mode=WAL` | Prevents lock contention between web requests and scheduler |
| Docker volumes | Named volume (`licenses_db:/data`) | Persistent, portable, survives `docker compose down` |

## Confidence Notes

- FastAPI lifespan, template, and router patterns: **HIGH** (verified against official docs)
- SQLAlchemy 2.0 model syntax: **HIGH** (verified against official quickstart)
- `check_same_thread=False` requirement: **HIGH** (explicitly documented in FastAPI SQL tutorial)
- APScheduler 3.x + lifespan integration pattern: **MEDIUM** (APScheduler docs inaccessible during research; pattern is well-established in community)
- HTMX attribute reference: **MEDIUM** (HTMX docs inaccessible; based on training knowledge + htmx.org patterns)
- Docker Compose best practices: **MEDIUM** (Docker Compose docs inaccessible; based on training knowledge)
- SQLite WAL mode recommendation: **MEDIUM** (well-established practice, consistent with SQLite docs)
