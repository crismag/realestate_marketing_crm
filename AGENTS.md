# Realstate CRM — coding agent instructions

Read `CLAUDE.md` for the implementation rules, then `context/cursor-cloud/README.md` for the current cloud handoff. This is an existing Django CRM, not a greenfield app.

## Cursor Cloud specific instructions

- Execute in a Cursor-hosted cloud environment connected to `crismag/realestate_marketing_crm`. Do not require the owner's laptop, local repository, local drive, browser session or local credential manager.
- The cloud VM's Git checkout is the working copy; GitHub commits/branches/PRs are the durable record. Use the selected remote branch and preserve concurrent work. Never reset or force-push another agent's changes.
- Run `bash scripts/cursor-cloud-setup.sh` for dependency preparation. Saved Cursor environments can override repository configuration: verify the active Build actually uses `.cursor/environment.json` or the same install command.
- Prefer Python 3.13 (3.12 supported), Node 22+, repository-pinned Python dependencies and the e2e lockfile. Do not copy `.env` or seed data into an environment Build.
- Start web/worker on demand after migration in a disposable demo database. Use fictional data. Do not confuse a remote development preview with production deployment.
- For parallel tests, allocate a distinct `CRM_TEST_DB_PATH` per worker. Never share writable SQLite databases between independent agents or load tests.
- Preserve ADR-001/002, shared internal customer visibility, sandbox customer messages, configurable policy and audit/transaction invariants in CLAUDE.md.
- Advance through `context/cursor-cloud/WORK_QUEUE.md` autonomously. Do not stop after planning, a single test run or a task summary while actionable work remains. Record assumptions and proceed on reversible engineering decisions.
- Delegate independent tasks when cloud subagents are available. Use `MULTI_AGENT_PROTOCOL.md`; serialize shared files and migrations. Otherwise execute sequentially and record the capability limit.
- Checkpoint and push reviewable commits after each verified slice. Maintain `RUN_STATE.json` and `RUN_LOG.md`. Repository state must be enough for another cloud agent to resume without this chat.
- Do not bypass provider limits, spend caps, permissions or stop controls, and do not manufacture indefinite keepalive loops. On a hard limit or blocker, checkpoint, push what is safe and report the exact next action; continue other independent work first.
- No automatic production rollout or merge to protected branches. Provider integrations remain sandboxed until credentials and the relevant owner choices are supplied. Missing credentials block only the dependent task.
