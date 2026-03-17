# packages/atlas-core

Shared Python domain and run-spine package.

Current ownership:

- typed domain models for `Environment`, `Scenario`, `Task`, `Run`, `RunStep`, `ToolCall`, `PolicyDecision`, `Artifact`, `GradeResult`, and `RunEvent`
- centralized `Run` lifecycle validation
- run/event/artifact serialization helpers
- Postgres migration runner and run repository/service contracts

Allowed imports:

- should not import apps, services, environments, graders, or `model-gateway`
- should stay environment-agnostic and policy-agnostic
