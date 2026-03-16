# apps/api

FastAPI control-plane shell.

Phase 1 scope:
- bootable app shell,
- config loading,
- `/health` endpoint only.

Local run:
```bash
uv run uvicorn atlas_api.main:app --factory --host 127.0.0.1 --port 8000
```
