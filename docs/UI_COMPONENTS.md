# UI component map (CrisGen UI 1.1)

All screens are server-rendered Django templates using the **vanilla target** of CrisGen UI 1.1,
vendored unmodified from `crismag/development_design_systems` (`crisgen-ui`) at commit
`e1c1a4f1e98ecc4dec9ae4eb16fa646069e94278` (see `crm/core/static/vendor/crisgen-ui/PROVENANCE.md`).
CRM-specific layout lives in `static/crm/crm.css` and uses CrisGen tokens only. Components were used by
their documented class and `data-*` attributes; none were invented under the `cg-` prefix.

## Shell and shared parts

| Part | CrisGen source | Notes |
|---|---|---|
| Page shell | `CrisGen/dashboard-shell` pattern (sidebar + navbar + content) | Sidebar from 1024px; below that a `<details>` "Menu" opens the same nav (no JavaScript) |
| Sidebar navigation | `List` (`cg-list`, `cg-list__item`) inside `Card` | `aria-current="page"` marks the active item |
| Top bar | `Navbar` (`cg-navbar`) + `Button` (ghost/outline) | Notifications count shown as a token-styled pill (gap below) |
| Flash messages | `Alert` (`cg-alert`, gradient variants) | `role="status"` |
| Buttons | `Button` (`cg-button`, `data-variant` solid/gradient/outline/ghost, `data-color`) | |
| Text inputs | `Input` (`cg-input`), `Textarea` (`cg-textarea`) | |
| Selects, checkboxes, radios | `Select`, `Checkbox`, `Radio` class names on native controls | Native elements keep keyboard and mobile behaviour |
| Status labels | `Chip` (`cg-chip`, `cg-chip__label`, `data-color`) via the `{% chip %}` template tag | One status → colour map in `crm/core/templatetags/crm_ui.py` |
| Headings | `Typography` (`cg-typography`, `data-variant` h4/h6) | |
| Tables | `CrisGen/data-table` pattern: `Table` (`cg-table`, `cg-table__table`, `__head-cell`, `__cell`) + filters + `Pagination` | Tables scroll sideways inside their card on phones; the page never does (browser-tested at 390px) |
| History | `Timeline` (`cg-timeline`, `__item`, `__indicator`, `__connector`, `__body`) | Ordered list semantics; colour by event kind |
| Breadcrumb | `Breadcrumb` | Contact profile |

## Screens

| Screen | Requirements | Components |
|---|---|---|
| Sign in, change password | NFR-001 | Card, Input, Button, Alert |
| Today | REQ-016, REQ-026 | Card (stat tiles), List, Chip, Button |
| Attention queue | REQ-016, REQ-017, REQ-026 | Card stat tiles, Select filters, Checkbox, Chip (reason + severity), Button, details disclosure for snooze |
| Contacts list + CSV export | FR-001, REQ-003–006 | data-table pattern (Input search, Select filters, Table, Pagination), Chip |
| Capture contact | REQ-003–006 | Card, Input, Textarea, Select, Radio, Checkbox, Alert (duplicate candidates) |
| Contact profile | FR-001, REQ-014–016, REQ-021 | Card, Chip, Timeline, List, Button, details disclosures for forms; Alert (info) for the pre-filled follow-up suggestion |
| Shared work (pools, handovers) | REQ-014, REQ-015 | data-table pattern, Chip, Button (claim/accept/decline) |
| Handover request | REQ-015, ADR-001/002 | Card, Radio, Select, Textarea, per-task disposition Selects |
| Tasks | REQ-015, REQ-017, REQ-020 | data-table pattern, Chip (overdue/critical) |
| Sales (opportunities) | REQ-022, REQ-024 | data-table pattern, Chip |
| Notifications | REQ-019 | List, Chip, Button |
| Automation rules, rule detail, jobs | REQ-020, REQ-023, NFR-003 | Table, Chip, Checkbox, Textarea (config), Button (preview/retry/cancel) |
| Customer messages, templates | REQ-018, REQ-020 | Card stat tiles, Table, Chip, Alert ("not sent" banner), Textarea + preview |
| Reports, drill-down, spend | REQ-017, REQ-022 | Card stat tiles, Table, Input (date), Select, details disclosure (definitions) |
| Settings, people, audit log | REQ-001/002, REQ-024, NFR-002 | Card, Input, Select, Checkbox, Table, Pagination |

## Gaps (CrisGen 1.1 has no matching component)

| Need | What was done | Suggested upstream addition |
|---|---|---|
| KPI / stat tile | `Card` + `.stat` layout in `crm.css` (tokens only) | A `Stat` component (value, label, link, trend) |
| Neutral status chip | `.chip-neutral` built from stone tokens, because `Chip` has no neutral colour | `data-color="neutral"` for `Chip` |
| Destructive button | Used `data-color="warning"`; `Button` has no `error` colour | `data-color="error"` for `Button` |
| Count badge in navigation | `.count-pill` from amber tokens; `Badge` is absolutely positioned for avatars/icons | An inline `Badge` placement |
| Disclosure / inline form | Native `<details>` styled with tokens | `Disclosure` (or `Drawer` usage guidance without JavaScript) |
| Fact list (label/value) | `dl.facts` grid | `DescriptionList` |
| Kanban/board for sales stages | Not built; stages are a table column | Board pattern, if the team wants a pipeline view |

`Drawer`, `Modal` and `Tabs` exist in CrisGen but need JavaScript behaviour; this build ships no JavaScript
(strict CSP), so they were not used. Adding a small, CSP-compatible script for them is a reasonable next step.
