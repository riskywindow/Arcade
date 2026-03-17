# apps/worker

Background orchestration worker for the Phase 4 execution path.

Current scope:

- bootable worker process
- config loading
- structured startup and shutdown logging
- deterministic dummy run execution through the shared `RunService`
- temporary Phase 3 scripted smoke flow for two seeded tasks
- deterministic Phase 4 agent demo loop for `mfa-reenrollment-device-loss`
- deterministic Phase 5 policy-protected demo loop for `travel-lockout-recovery`
- typed in-process tool registry for browser, helpdesk ticket, doc lookup, directory lookup, and screenshot capture
- a seeded `identity_api` tool path for policy-gated recovery actions
- Bastion-mediated interception for worker tool execution before tool executors run
- approval-request recording and explicit `waiting_approval` run pausing for Bastion-gated actions
- a narrow same-process approval wait/resume path for the Phase 5 flagship demo
- an optional Bastion-owned `isolated_command` executor exists for Docker-sandboxed helper commands, but it is not part of the default seeded demo tool list
- default deterministic demo browser mode for the seeded Phase 4 smoke path

Still deferred:

- generic persisted post-approval re-dispatch for arbitrary paused runs
- any generic terminal tool or unconstrained shell execution surface
- production agent abstraction

Local run:
```bash
uv run atlas-worker
```

Deterministic dummy execution:
```bash
uv run atlas-worker dummy-run --run-id dummy-run-001
```

Phase 3 scripted smoke flow:
```bash
uv run atlas-worker scripted-smoke --run-prefix phase3-smoke
```

Phase 4 seeded agent demo:
```bash
uv run atlas-worker agent-demo --run-id phase4-agent-demo-001
```

Optional live browser validation:
```bash
uv run atlas-worker agent-demo --run-id phase4-agent-demo-live-001 --browser-mode live
```

Phase 5 policy-protected demo:
```bash
uv run atlas-worker policy-demo --run-id phase5-policy-demo-001
```

One-command local demo reset:
```bash
make phase4-demo-reset
```

One-command policy-protected demo reset:
```bash
make phase5-demo-reset
```

Historical dummy-run reset:
```bash
make phase2-demo-reset
```
