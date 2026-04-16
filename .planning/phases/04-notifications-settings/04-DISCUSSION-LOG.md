# Phase 4: Notifications & Settings - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 04-notifications-settings
**Areas discussed:** Digest Format, Scheduler Timing, Settings Page UX, Per-License Threshold Field

---

## Digest Format

| Option | Description | Selected |
|--------|-------------|----------|
| Urgency tiers | 🔴 Истекло / 🟡 Истекает скоро — separate sections with emoji headers | ✓ |
| Flat list sorted by days remaining | Single list ascending by urgency | |
| Grouped by responsible person | Each person's licenses in their own section | |

**User's choice:** Urgency tiers

---

| Option | Description | Selected |
|--------|-------------|----------|
| Only within global threshold | expired + days ≤ threshold | ✓ |
| All non-active | expired + warning regardless of threshold | |
| All three tiers every day | critical/warning/notice tiers always shown | |

**User's choice:** Only within global threshold

---

| Option | Description | Selected |
|--------|-------------|----------|
| Russian plain text with emoji headers | `• Product — DD.MM.YYYY (N дней) — Responsible` | ✓ |
| Russian HTML formatting | Bold product names, monospace dates, parse_mode=HTML | |
| Russian + English bilingual labels | For international teams | |

**User's choice:** Russian plain text with emoji headers

---

## Scheduler Timing

| Option | Description | Selected |
|--------|-------------|----------|
| 09:00 hardcoded | Simple, timezone via TZ env var | |
| 09:00 default, configurable in Settings | Stored in AppSettings, operator can change | ✓ |
| Configurable time + timezone in Settings | Full control but more complex | |

**User's choice:** Configurable in Settings (default 09:00)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Send nothing | Skip message entirely when 0 licenses qualify | ✓ |
| Send "all clear" | ✅ Все лицензии в порядке | |
| Claude's discretion | | |

**User's choice:** Send nothing

---

## Settings Page UX

| Option | Description | Selected |
|--------|-------------|----------|
| Single save button | One POST /settings, HTMX replaces form section | ✓ |
| Per-field save on blur | Each field saves independently | |
| Two sections with separate save buttons | Telegram config + Notification config | |

**User's choice:** Single save button

---

| Option | Description | Selected |
|--------|-------------|----------|
| Inline below button | HTMX swaps div#test-result | ✓ |
| Flash banner at page top | Dismissible alert | |
| Modal dialog | Overlay with result | |

**User's choice:** Inline below button via HTMX

---

| Option | Description | Selected |
|--------|-------------|----------|
| Telegram only + threshold + time (no toggle) | bot_token, chat_id, notify_days_before, notify_time | ✓ |
| Same + scheduler enable/disable toggle | Operator can turn off digest | |

**User's choice:** No toggle — runs when token+chat_id set

---

## Per-License Threshold Field

| Option | Description | Selected |
|--------|-------------|----------|
| Edit form only | notify_days_before on /licenses/{id}/edit only | |
| Both Add and Edit forms | Present on /licenses/new and edit page | |
| Claude's discretion | | ✓ |

**User's choice:** Claude's discretion

---

| Option | Description | Selected |
|--------|-------------|----------|
| Placeholder text | Shows current global value | |
| Helper text below field | Explains empty = global default | |
| Claude's discretion | | ✓ |

**User's choice:** Claude's discretion

---

## Claude's Discretion

- Where `notify_days_before` override field appears (add, edit, or both forms)
- Placeholder/helper text for empty override field
- Exact HTML structure of Settings page
- Error message copy for Telegram API failures
- Whether to show last-sent timestamp on Settings page
