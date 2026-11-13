# Cloud multi-agent execution protocol

## Roles
| Role | Owns | Delivers |
|---|---|---|
| Coordinator | Queue, contracts, integration branch, migration allocation, shared docs/state | Ordered ready tasks, integrated checks, checkpoint and PR |
| Workflow engineer | Scoped capture/work/attention/reporting changes | Source-linked fixes/features and meaningful tests |
| Security/reliability engineer | Scoped auth/comms/worker/backup audit and fixes | Reproductions, safe fixes, concurrency/security evidence |
| UI/QA engineer | Scoped templates/app CSS/browser tests | Accessible/mobile workflows, screenshots and failure-state verification |
| Independent reviewer | Read-only integrated diff/source/tests | Prioritized verified defects; no unapproved editing of owned files |

Start with 2–3 implementation agents and one coordinator/reviewer as actual platform capacity and existing account budget permit. Never assume ChatGPT tools/models are available in Cursor. Use Cursor's supported subagent/cloud-agent controls; if unavailable, complete tasks sequentially.

## Worker task contract
Every delegation includes task ID, source requirement, exact allowed files, prohibited files, interfaces/migration dependencies, acceptance scenarios, test commands with unique DB path, expected output and checkpoint branch. Give the worker enough context to proceed independently, not the entire unrelated chat history.

Example task: audit stale opportunity handover behavior; own only named services plus a new regression file; preserve current owner until acceptance; reproduce before fixing; use `/tmp/crm-worker-a-tests.sqlite3`; return changed files, red/green evidence, commit and remaining risks.

## Isolation and integration
- Prefer separate cloud branches/worktrees for independent agents. Assign one owner per file. A shared VM does not imply safe shared writes.
- Coordinator serializes schema changes, reserves the next migration name and checks graph conflicts. Never let two agents generate competing migration numbers independently.
- Workers do not edit shared run state, queue, requirement matrix or log concurrently; they report evidence to the coordinator, who writes those records.
- No shared writable test/load databases, runtime ports, preview directories or screenshots filenames across workers.
- Integrate one verified task at a time. Compare remote heads first; inspect incoming changes and resolve conflicts by behavior, not blanket ours/theirs.
- Review every agent's diff and run the integrated suite. A worker's green focused tests do not prove the integration is green.
- No automatic merge of the integration PR to main. Keep ready commits pushed for review and continue the next authorized task on the working branch.

## Review gate
Reviewer checks accepted business rules, transaction/audit coupling, source reconciliation, privacy/secrets, idempotency, optimistic conflicts, migration portability, accessibility/mobile behavior and whether tests exercise real outcomes. Coordinator reproduces ambiguous findings before acting. Fix verified defects before moving a task to done.

## Stop and recovery
If one worker hits a limit, checkpoint its work and reassign from the durable task record. Do not leave background edits unmanaged. At whole-run limit, save all task statuses, pushed commits, blockers, services and exact next action. A future run reads RESUME_PROMPT.md; no unsupported automatic self-restart is assumed.
