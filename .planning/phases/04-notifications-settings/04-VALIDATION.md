---
phase: 4
slug: notifications-settings
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-16
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | `pyproject.toml` / `pytest.ini` (existing) |
| **Quick run command** | `pytest tests/test_settings.py tests/test_telegram.py tests/test_scheduler.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_settings.py tests/test_telegram.py tests/test_scheduler.py -q`
- **After every plan wave:** Run `pytest tests/ -q` (must stay green — no regressions in Phase 2/3 tests)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 04-01-01 | 01 | 1 | SETT-01, SETT-03 | integration | `pytest tests/test_settings.py -q` | ⬜ |
| 04-01-02 | 01 | 1 | NOTF-04, NOTF-06 | integration | `pytest tests/test_settings.py -q && pytest tests/ -q` | ⬜ |
| 04-02-01 | 02 | 1 | NOTF-01, NOTF-03 | unit+mock | `pytest tests/test_telegram.py -q` | ⬜ |
| 04-02-02 | 02 | 1 | NOTF-01 | unit+mock | `pytest tests/test_telegram.py -q && pytest tests/ -q` | ⬜ |
| 04-03-01 | 03 | 2 | INFRA-04, NOTF-02 | unit | `pytest tests/test_scheduler.py -q` | ⬜ |
| 04-03-02 | 03 | 2 | NOTF-02, NOTF-03, NOTF-05 | unit | `pytest tests/test_scheduler.py -q && pytest tests/ -q` | ⬜ |
| 04-04-01 | 04 | 3 | SETT-02 | integration | `pytest tests/test_settings.py::test_test_notification -q` | ⬜ |
| 04-04-02 | 04 | 3 | LIC-06, NOTF-05 | integration | `pytest tests/test_settings.py tests/test_telegram.py -q && pytest tests/ -q` | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_settings.py` — stub file with placeholders for SETT-01..03, NOTF-04, NOTF-06
- [ ] `tests/test_telegram.py` — stub file with placeholders for NOTF-01..06
- [ ] `tests/test_scheduler.py` — stub file with placeholders for INFRA-04, NOTF-02, LIC-06
- [ ] Existing `tests/conftest.py` reused — no new fixtures expected initially

*Existing pytest install — no framework setup needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real Telegram message delivered to chat | NOTF-01 | Requires live bot token + chat ID | Configure bot in .env, click "Отправить тестовое уведомление", verify message arrives in Telegram |
| Daily digest fires at configured time | NOTF-02 | Scheduler timing requires waiting or clock manipulation | Set notify_time to 1 min from now in Settings, watch Telegram for message |
| Scheduler survives container restart | INFRA-04 | Docker lifecycle test | `docker compose restart`, verify scheduler re-registers at startup |
| Test notification inline result displays | SETT-02 | HTMX DOM interaction needs browser | Click button in browser, verify div#test-result populates without page reload |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (`tests/test_settings.py`, `tests/test_telegram.py`, `tests/test_scheduler.py`)
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter after planner fills task map

**Approval:** approved
