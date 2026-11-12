# Security verification matrix
Model 23. Conceptual operations only; concrete endpoints/session mechanism unknown. All checks not_run.
| Action | Boundary/control | Positive | Negative / side effect assertion |
|---|---|---|---|
| Internal read/write | Server authentication | Signed-in internal user accesses shared functions | Anonymous request denied without record disclosure/write |
| Claim INT-001 | Valid input/current assignment version | Atomic valid claim | Stale/invalid claim cannot overwrite |
| Accept INT-002 | Acceptance identity/valid transition | Named recipient/coordinator accepts | Another signed-in colleague cannot impersonate recipient acceptance; no write |
| Intake integration | Narrow authenticated/validated integration | Valid signed/authorized intake accepted | Invalid payload/replay rejected or deduplicated; CRM read access not granted |
| Notification INT-004 | Trusted worker intent and validated recipients | Enabled due action executes | Opt-out/replied/invalid recipient suppresses as policy requires; secrets absent from logs |
| Provider callback | Signature/replay controls if callback is used | Valid outcome correlates to delivery | Forged/replayed result cannot fake conversation or delivery |
| Profile/history text | Validation and context-safe output | Normal notes render | Untrusted markup cannot execute; persistence uses parameterized approach appropriate to selected stack |

No restrictive internal user roles are adopted. Recipient validation protects integrity of acceptance, not a hidden role hierarchy. Cross-company access tests are not applicable to this single-workspace release; add when tenancy exists. Customer portal tests deferred with portal.
Session/CSRF/CORS, rate limits, uploads and database-level policies must be assessed against actual chosen implementation; no blanket RLS or framework-specific mandate. Record evidence, observed response and data side effects, not just UI button visibility.
