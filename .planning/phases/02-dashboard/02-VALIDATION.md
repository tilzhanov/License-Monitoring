---
phase: 02
slug: dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 (already installed) |
| **Config file** | none — tests run from project root |
| **Quick run command** | `python3 -m pytest tests/ -q --tb=short` |
| **Full suite command** | `python3 -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/ -q --tb=short`
- **After every plan wave:** Run `python3 -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | LIC-05 | unit | `python3 -m pytest tests/test_status.py -v` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | DASH-01 | integration | `python3 -m pytest tests/test_dashboard.py -v` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | DASH-02 | integration | `python3 -m pytest tests/test_dashboard.py -v` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 2 | DASH-03 | integration | `python3 -m pytest tests/test_dashboard.py -v` | ❌ W0 | ⬜ pending |
| 02-02-04 | 02 | 2 | DASH-04 | integration | `python3 -m pytest tests/test_dashboard.py -v` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | DASH-03 | manual | Visual inspection of color-coded rows | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_status.py` — stubs for status computation (LIC-05)
- [ ] `tests/test_dashboard.py` — stubs for dashboard routes (DASH-01..04)

*Existing infrastructure (conftest.py, test fixtures) covers shared needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Color-coded row visibility | DASH-03 | Visual rendering | Open dashboard, verify red/yellow/green rows visible |
| Responsive table layout | DASH-03 | CSS visual check | Resize browser, verify table doesn't overflow |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
