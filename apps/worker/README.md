# apps/worker

Background orchestration shell.

Phase 1 scope:
- bootable worker process,
- config loading,
- structured startup and shutdown logging,
- no job execution or real run orchestration.

Local run:
```bash
uv run atlas-worker
```

Deterministic dummy execution:
```bash
uv run atlas-worker dummy-run --run-id dummy-run-001
```

One-command local demo reset:
```bash
make phase2-demo-reset
```
