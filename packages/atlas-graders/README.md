# packages/atlas-graders

Deterministic hidden grader helpers for seeded helpdesk scenarios.

Current Phase 3 scope:

- private observed-evidence contract for deterministic checks
- hidden-state-driven graders for the first 5 helpdesk scenarios
- `GradeResult` output compatible with the Phase 2 run spine
- no benchmark runner and no LLM judge

Allowed imports:
- may import `atlas-core` and environment packages such as `atlas-env-helpdesk`
- should not be imported by environment packages
- should not import app or service packages
