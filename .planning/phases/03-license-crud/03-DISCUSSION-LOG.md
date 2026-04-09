# Phase 3: License CRUD - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 03-license-crud
**Areas discussed:** Add/Edit form UX, Delete confirmation

---

## Add/Edit Form UX

### Add form presentation

| Option | Description | Selected |
|--------|-------------|----------|
| Separate page | Dedicated /licenses/new page with full form. Clean, simple, works well with HTMX. | ✓ |
| Modal overlay | Form appears as modal over dashboard. Keeps context visible but more complex. | |
| Inline above table | Form slides in above the license table on dashboard. Quick but clutters main view. | |

**User's choice:** Separate page
**Notes:** None

### Edit form approach

| Option | Description | Selected |
|--------|-------------|----------|
| Same form page | GET /licenses/{id}/edit — same form layout as Add, pre-filled. Reuses template. | ✓ |
| Inline row editing | Click Edit, row transforms into input fields in-place. Tight for 7 fields. | |
| Edit from detail page | Navigate to detail first, then click Edit. Extra click. | |

**User's choice:** Same form page
**Notes:** None

### After save redirect

| Option | Description | Selected |
|--------|-------------|----------|
| Back to dashboard | Redirect to / after save. User sees updated table immediately. | ✓ |
| License detail page | Redirect to /licenses/{id} after save. User verifies fields. | |
| Stay on form | Show success banner on same page. Good for batch adding. | |

**User's choice:** Back to dashboard
**Notes:** None

### Add button placement

| Option | Description | Selected |
|--------|-------------|----------|
| Above the table | Button above license table on dashboard, near filter controls. | ✓ |
| In the nav bar | Persistent link in top navigation. Always accessible. | |
| Both nav and above table | Nav link + prominent button above table. | |

**User's choice:** Above the table
**Notes:** None

---

## Delete Confirmation

### Confirmation method

| Option | Description | Selected |
|--------|-------------|----------|
| Browser confirm() | Simple JS confirm() via hx-confirm. Minimal code, familiar UX. | ✓ |
| Inline confirmation row | Row replaced with "Delete? [Yes] [Cancel]". More polished, extra template. | |
| Modal dialog | Custom modal overlay. Most polished but heaviest to implement. | |

**User's choice:** Browser confirm()
**Notes:** None

### After deletion behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Row disappears | Deleted row fades out. Stats update via OOB swap or table reload. | ✓ |
| Full page reload | Redirect to dashboard with flash message. Simpler but heavier. | |
| Row disappears + toast | Row fades out plus temporary success toast. Needs toast component. | |

**User's choice:** Row disappears
**Notes:** None

---

## Claude's Discretion

- Detail page layout (DASH-05) — card design, field display, breadcrumbs
- Validation feedback approach — inline vs summary
- Date input UX
- Form field ordering
- Action button placement in table rows

## Deferred Ideas

None — discussion stayed within phase scope.
