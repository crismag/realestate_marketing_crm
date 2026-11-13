# Autonomous run plan — 2026-11-13T02:36Z

Run id `autonomous-build-2026-11-13T02:36Z`. Fixed window: **2026-11-13T02:36:00Z → 2026-11-13T14:36:00Z**.
The deadline is fixed at start. Restarts do not extend it. Branch
`cursor/sales-board-crisgen-behaviors-77d9` from `fda56b3` (main, baseline already implemented).

The 2026-11-12 plan (stages A–J, deadline 2026-11-13T07:08:03Z) belongs to that run. Its software is on main.
This run does not regenerate it.

## This run

| Slice | Scope | Status |
|---|---|---|
| Design rule | `.cursor/rules/design-system.mdc`: CrisGen pin, theme, reuse, screen map, MIT / Creative Tim notice, no vendor branding | Done |
| Behaviours | External `static/crm/behaviors.js` for Drawer, Modal and Tabs. No inline styles (CSP) | Done, browser-tested |
| Sales board | List/board tabs, filter drawer, stage-move modal. Stage change does not move responsibility or lifecycle | Done, pytest + e2e |

## Still open after this slice

- Dropdown, popover, tooltip, select listbox, accordion and collapse are not wired. Do not pretend they are.
- Staff digest email, retention/deletion, calendar, saved filters, bulk responsibility change (only through ADR-001 handover).
- Pilot hosting, real customer email, MySQL, usability and assistive-technology review.

Stop new features in the last 60–90 minutes. Finish integration, fixes and this handoff.
