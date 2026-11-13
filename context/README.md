# CRM development context
Updated: 13 November 2026. Stage: implementation hardening and pilot preparation.

## Start here
1. Read the root [README](../README.md) and [CLAUDE.md](../CLAUDE.md) for the implemented stack and commands.
2. Read [Development execution](09_development/DEVELOPMENT_EXECUTION.md) for current scope, agent ownership and remaining stages.
3. Read [Current run report](09_development/CURRENT_RUN_REPORT.md) and [Run log](09_development/RUN_LOG.md) for observed evidence.
4. Read [Requirement matrix](../docs/REQUIREMENTS_MATRIX.md) and [Known limitations](../docs/KNOWN_LIMITATIONS.md).
5. Load the relevant requirements, module contract and tests before changing a subsystem.

## Current system
Django 5.2 LTS, SQLite WAL, database-backed job worker, server-rendered CrisGen UI, sandbox customer email. Eight apps implement customer capture, responsibility/pools/handovers, interactions/tasks, attention, automation, communications, reporting and configuration. MySQL is a documented future migration, not verified support.

## Product authority
The [requirements baseline](04_requirements/CRM_Requirements_Baseline_v0.1.md) is preserved. [Open decisions](04_requirements/OPEN_DECISIONS.md) and accepted ADR-001/002 supersede historical pending wording. Sender responsibility continues until acceptance; pool claims are exclusive and coordinator acceptance is required for release. Engineer-selected policy defaults remain configurable and do not imply business approval.

## Boundaries
One internal company workspace with shared customer visibility. Customer portals, multi-company SaaS, property inventory and payout accounting remain excluded/deferred. Sandbox captures are not email deliveries. Deployment, real providers and production data require actual configuration and evidence.

## History
Revision 24 documents and task briefs describe the original proposed design. They remain useful requirement sources but their claims of no code, no selected stack or no runtime tests are historical. The current implementation and this run's evidence supersede those status claims. Historical autonomous-run deadlines govern only their named runs; use the current execution context for continuation.

[Full context index](CONTEXT_INDEX.md)
