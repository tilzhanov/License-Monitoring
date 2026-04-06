---
phase: 1
slug: infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | none — Wave 0 creates `tests/conftest.py` and adds pytest to `requirements.txt` |
| **Quick run command** | `docker compose exec web python -m pytest tests/ -x -q` |
| **Full suite command** | `docker compose exec web python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec web python -m pytest tests/ -x -q`
- **After every plan wave:** Run `docker compose up -d && curl -sf http://localhost:8080/health && docker compose exec web python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green + manual Docker restart persistence check
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INFRA-01, INFRA-02 | integration | `docker compose build && docker compose up -d && curl -sf http://localhost:8080/health` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | LIC-04 | unit | `docker compose exec web python -m pytest tests/test_models.py -x -q` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | INFRA-03 | unit | `docker compose exec web python -m pytest tests/test_models.py::test_wal_mode -x -q` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | INFRA-01 | integration | `docker compose exec web python -m pytest tests/test_health.py -x -q` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 2 | INFRA-02 | unit | `docker compose exec web python -m pytest tests/test_config.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — package init
- [ ] `tests/conftest.py` — shared fixtures (in-memory SQLite engine, TestClient with override)
- [ ] `tests/test_models.py` — covers LIC-04 (License columns, AppSettings KV, WAL mode, bootstrap logic)
- [ ] `tests/test_health.py` — covers INFRA-01 (GET /health returns 200 + {"status": "ok"}, GET / returns 200 HTML)
- [ ] `tests/test_config.py` — covers INFRA-02 (.env.example contains all required vars, .env is in .gitignore)
- [ ] `pytest==9.0.2` added to `requirements.txt`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SQLite persists across `docker compose restart` | INFRA-03 | Requires Docker volume lifecycle | 1. `docker compose up -d` 2. Note health OK 3. `docker compose restart` 4. `curl http://localhost:8080/health` must still return 200 |
| `.env` not committed to git | INFRA-02 | git state check | `git status` must not show `.env` as tracked; `git ls-files .env` must return empty |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
