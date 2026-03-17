# services/bastion-gateway

Bastion gateway service for the live Phase 5 interception path.

Current scope:

- shared Bastion request, policy, approval, secret-handle, and audit contracts come from `atlas-core`
- a concrete in-process gateway exists for `request -> policy -> execute or deny or require-approval -> audit`
- a deterministic rule-based evaluator loads a local JSON policy pack for the v1 helpdesk domain
- a deterministic local secrets broker resolves scoped handles for secret-aware tool adapters without exposing raw values to the model
- a Docker-based sandbox wrapper isolates the narrow `isolated_command` tool path without changing the rest of the worker runtime
- FastAPI exposes a typed interception endpoint at `POST /v1/tool-requests:intercept`
- the worker routes live tool calls through this gateway before execution
- approval-gated execution requires a resolved approved record for the same run and action before the action can execute

Still deferred:

- generic persisted continuation for arbitrary approval-paused runs
- broader sandbox coverage beyond the limited Docker-wrapped command path
