# Roadmap: License Monitoring Dashboard

## Overview

Four phases deliver a working internal license monitoring tool from scratch. Phase 1 lays the project skeleton — Docker Compose, SQLite schema, project structure — so every subsequent phase has a running container to extend. Phase 2 builds the read-only dashboard that makes license status visible. Phase 3 adds full CRUD so the team can manage their license records. Phase 4 closes the loop with Telegram notifications and a settings page, making the core value (never miss a renewal) real and observable.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Infrastructure** - Project skeleton, Docker Compose, SQLite schema, .env config (completed 2026-04-06)
- [x] **Phase 2: Dashboard** - Read-only main page with stats, expiring widget, color-coded license table (completed 2026-04-06)
- [ ] **Phase 3: License CRUD** - Add, edit, delete licenses via web forms; license detail page
- [ ] **Phase 4: Notifications & Settings** - Telegram bot, daily scheduler, settings page, per-license thresholds

## Phase Details

### Phase 1: Infrastructure
**Goal**: A running containerized application with a defined schema that the team can `docker-compose up` on any Linux host
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, LIC-04
**Success Criteria** (what must be TRUE):
  1. `docker-compose up` starts the application with no manual steps beyond copying `.env.example` to `.env`
  2. The app responds at the configured host port with a placeholder page (no 500 errors)
  3. The SQLite database file is created automatically on startup inside the Docker volume and persists across `docker-compose restart`
  4. All license fields (product/system, purchase date, expiry date, responsible person, cost, comment) exist as columns in the `licenses` table
  5. `.env.example` documents every configurable variable; `.env` is git-ignored
**Plans**: 3 plans

Plans:
- [x] 01-01: Initialize project structure — `app/`, `static/`, `templates/`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `.env.example`, `.gitignore`
- [x] 01-02: Implement database layer — SQLAlchemy models for `License` and `AppSettings`, engine config with WAL mode, `create_all()` on lifespan startup
- [x] 01-03: Wire FastAPI app skeleton — `main.py` with lifespan, health endpoint, base Jinja2 template, static file serving, placeholder index route

### Phase 2: Dashboard
**Goal**: Users can see the full state of all licenses at a glance without needing to open any records
**Depends on**: Phase 1
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, LIC-05
**Success Criteria** (what must be TRUE):
  1. The main page shows three summary counters: total licenses, expiring soon, already expired
  2. A "Expiring Soon" widget on the main page lists licenses approaching their threshold with product name, expiry date, and days remaining
  3. The license table rows are color-coded: red for expired or critical, yellow for expiring soon, green for active — visible without any interaction
  4. Status (active / expiring soon / expired) is computed server-side from today's date and the expiry date; no manual status field exists
  5. The table can be filtered by product name or status, and sorted by expiry date or product name, without a full page reload
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Status computation service with unit tests (days_until_expiry, get_license_status, threshold fallback chain, enrich_licenses)
- [x] 02-02-PLAN.md — Dashboard route, templates, and CSS (stats counters, expiring-soon widget, color-coded license table, responsive styling)
- [x] 02-03-PLAN.md — HTMX filter/sort partial endpoint and integration tests (product/status filter, column sort, full test coverage)
**UI hint**: yes

### Phase 3: License CRUD
**Goal**: Users can add, edit, and delete licenses through the web interface without touching the database directly
**Depends on**: Phase 2
**Requirements**: LIC-01, LIC-02, LIC-03, DASH-05
**Success Criteria** (what must be TRUE):
  1. A user can submit a form to add a new license; the new row appears in the table immediately without a full page reload
  2. A user can click Edit on any license row, change any field inline, and save — the row updates in place
  3. A user can delete a license; a confirmation dialog appears before the row is removed
  4. The license detail page shows all fields for a single license (product, purchase date, expiry date, responsible, cost, comment, computed status)
  5. Form validation prevents saving a license with a missing product name or expiry date; the user sees an inline error message
**Plans**: 3 plans

Plans:
- [x] 03-01: Implement license router — GET/POST for create, GET/PUT for edit (HTMX inline row swap), DELETE with confirmation, row and edit-row fragment templates
- [x] 03-02: Build license detail page — full-page view of all fields, breadcrumb back to dashboard, edit link
- [x] 03-03: Add form validation — server-side field validation, HTMX-friendly error fragment return, client-side date picker for expiry/purchase fields
**UI hint**: yes

### Phase 03.1: UI Polish (INSERTED) ✅

**Goal:** Transform the raw browser-default UI into a polished, data-first internal ops dashboard (Linear / Grafana / Vercel style) using ui-ux-pro-max design intelligence, without breaking existing HTMX functionality or Phase 2/3 integration tests
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09, UI-10, UI-11, UI-12, UI-13, UI-14, UI-15, UI-16, UI-17, UI-18
**Depends on:** Phase 3
**Status:** Complete (2026-04-16) — 18/18 requirements verified, 41 smoke tests, 103 passed locally, visual UAT approved
**Plans:** 4/4 plans executed

Plans:
- [x] 03.1-01-PLAN.md — CSS design-system foundation: token-driven app.css rewrite, Google Fonts + skip-link + SVG icon sprite wiring in base.html, status_badge macro, smoke test scaffold, append UI-01..UI-18 to REQUIREMENTS.md
- [x] 03.1-02-PLAN.md — Dashboard polish: stats cards (label-first), expiring widget with alert icon, table-container + keyboard-accessible sortable headers with chevrons, filter bar with search icon, row fragment using status_badge macro, locked empty-state copy
- [x] 03.1-03-PLAN.md — Forms + detail + 404 polish: form-card with required markers and field-error icons, detail page with arrow-left breadcrumb + verb+noun CTAs, 404 page with dynamic h1 resolving test_licenses.py:215 conflict
- [x] 03.1-04-PLAN.md — HTMX polish + a11y gate + visual UAT: htmx-request/fadeIn indicators, focus-visible + reduced-motion verification, full regression, VALIDATION.md sign-off, human UAT checkpoint + UI-13 filter-no-match empty state gap fix

### Phase 4: Notifications & Settings
**Goal**: The system automatically alerts the team on Telegram before licenses expire, and operators can configure all notification parameters through the UI
**Depends on**: Phase 3
**Requirements**: NOTF-01, NOTF-02, NOTF-03, NOTF-04, NOTF-05, NOTF-06, SETT-01, SETT-02, SETT-03, LIC-06, INFRA-04
**Success Criteria** (what must be TRUE):
  1. A daily Telegram digest is sent automatically at the configured time listing all licenses within the notification threshold, grouped by urgency (critical / warning / notice)
  2. Each license entry in the digest shows product name, expiry date, days remaining, and responsible person
  3. The Settings page lets an operator save Telegram bot token, chat ID, and global notification threshold; values persist in the database and survive container restarts
  4. The "Send Test Notification" button delivers a real message to the configured chat and shows success or a descriptive error inline — no page reload required
  5. A per-license threshold field overrides the global default for that license; the scheduler respects the override when deciding whether to include the license in the digest
  6. The scheduler starts inside the Python process on app startup; no separate container or external cron is required
**Plans**: 4 plans

Plans:
- [x] 04-01: Implement settings service and router — `AppSettings` key-value table, DB-over-env precedence chain, settings page with HTMX form save, `GET /settings` and `POST /settings`
- [x] 04-02: Build Telegram notification service — `send_telegram_message()` with httpx, HTML parse mode, `html.escape()` for all user strings, error classification (401/400/403/timeout)
- [ ] 04-03: Implement daily scheduler job — APScheduler `BackgroundScheduler` in lifespan, `CronTrigger` at 09:00 team timezone, digest formatter grouping licenses by urgency, per-license threshold override logic
- [ ] 04-04: Wire test notification endpoint and per-license threshold — `POST /settings/test-notification` HTMX endpoint with user-visible error messages, `notification_threshold_days` column on `License` model, field on edit form

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure | 3/3 | Complete   | 2026-04-06 |
| 2. Dashboard | 3/3 | Complete | 2026-04-06 |
| 3. License CRUD | 3/3 | Complete | 2026-04-09 |
| 03.1. UI Polish | 4/4 | Complete | 2026-04-16 |
| 4. Notifications & Settings | 2/4 | In Progress|  |
