# Cursor Cloud development handoff

Prepared 13 November 2026 for Cris Magalang. Repository: https://github.com/crismag/realestate_marketing_crm

## Objective
Continue building, reviewing, testing and refining the complete internal real estate sales/marketing CRM using Cursor-hosted agents. Work from GitHub, with durable commits and PRs. The user's computer may be offline. This package does not itself start a Cursor run or grant an unlimited runtime.

## Package
| File | Purpose |
|---|---|
| `MASTER_PROMPT.md` | Full instruction to paste into a new Cursor Cloud run |
| `PROJECT_CONTEXT.md` | Product, implementation, decisions, source map and evidence |
| `CLOUD_SETUP.md` | Connect GitHub, select branch, build environment, run web/worker and verify |
| `WORK_QUEUE.md` | Ordered development stages and checkable task completion criteria |
| `MULTI_AGENT_PROTOCOL.md` | Coordinator, worker ownership, integration and independent review |
| `RUN_STATE.json` | Initial machine-readable checkpoint; update during execution |
| `RUN_LOG.md` | Append-only cloud execution record |
| `RESUME_PROMPT.md` | Recover a stopped or context-limited cloud run |
| root `AGENTS.md`, `.cursor/rules/realstate-crm.mdc` | Automatic entry instructions |
| `.cursor/environment.json`, `scripts/cursor-cloud-setup.sh` | Cloud Build dependency preparation |

## Read order
1. Root AGENTS.md and CLAUDE.md.
2. PROJECT_CONTEXT.md and RUN_STATE.json.
3. WORK_QUEUE.md; load the specific requirement/module/test context for the next task.
4. MULTI_AGENT_PROTOCOL.md and CLOUD_SETUP.md as needed.

The full requirement/specification folder already exists under `context/`. Do not replace it with this handoff. Accepted decisions and latest code supersede historical planning status. `context/09_development/CURRENT_RUN_REPORT.md` documents an earlier hardening snapshot, not every later feature.

## Branch selection
This package is prepared on `codex/cursor-cloud-handoff-20261113` from inspected `main` commit `fda56b3`. Start Cursor from the branch containing this package. Once its PR is merged, start from updated `main`. At launch fetch current refs and inspect the actual selected commit; repository work may have advanced again. Create a Cursor implementation branch from that selected base. Do not replay merged PRs or silently drop newer code.

## Continuous execution
Work task → verify → independent review → fix → checkpoint/push → next ready task. Stop only when the scoped queue is complete, the user stops work, the platform imposes a limit, or all remaining tasks depend on unavailable input/access. Checkpoint/resume supports continuation across runs; a prompt cannot guarantee perpetual execution or restart a provider-stopped agent.

## Launch
Open https://cursor.com/agents, connect GitHub access to this repo, select the cloud environment and handoff branch, then paste MASTER_PROMPT.md. The account connection, plan access and run submission happen in the user's Cursor account. No local repository setup is required.
