# Isolated test environment
Model 23. Proposed requirements; actual runtime/services/ports/versions and commands unresolved.
Use dedicated local/test storage with synthetic contacts, users, pools, fixed clock and separate credentials. No production customer data. Provider stubs validate orchestration only; provider sandbox validates integration separately.

Fixture set: two agents, coordinator, recipient; one available pool client; one pending transfer; one client toured with no follow-up/task; one client with overlapping attention reasons; opt-out/replied client; due notification; absent financial data.
Deterministic IDs/time let boundary and retry tests be reproduced. Seed/reset must be repeatable and verify allowlisted test database/namespace before writes. If target identity is uncertain, block reset/migration.
Before implementation fill actual host/runtime, lockfile install, services, readiness/start/stop, test URL, safe environment-variable names, secret injection, migration and seed/teardown commands from evidence. None is invented here.
Teardown stops test workers/services and deletes only owned synthetic data/resources. Never treat setup failure as application failure or a skipped provider as tested delivery.
