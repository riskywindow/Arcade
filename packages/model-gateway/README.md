# packages/model-gateway

Provider-agnostic model invocation boundary for Phase 4.

Current scope:

- validated `AgentConfig` and `RetryPolicy` contracts
- provider-agnostic `ModelInvocation`, `ModelResponse`, and `ModelToolDefinition` contracts
- `ModelGateway` wrapper used by worker-side orchestration
- deterministic `FakeModelProvider` for tests and seeded demo runs

Phase 4 contract note:

- execution-domain contracts such as `ExecutionContext`, `AgentTurn`, `ToolRequest`, `ToolResult`, and `RunExecutionSummary` live in `atlas-core`
- `model-gateway` consumes those contracts and adds only model/provider-facing types
- tool execution remains outside this package
- policy interception and approvals still belong to Bastion and remain out of scope for the model gateway

Real provider note:

- a future provider can implement the `ModelProvider` protocol and plug into `ModelGateway` without changing the worker runner contract
- secrets and provider-specific credentials should remain external configuration, not hard-coded in this package

Allowed imports:
- may import `atlas-core`
- should not import environment or grader packages
- app and service packages may depend on this package later
