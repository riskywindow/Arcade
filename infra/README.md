# Infra

Local infrastructure for Phase 1 uses Docker Compose only.

Services:

- Postgres
- Redis
- MinIO

These containers exist to support local bootstrapping and connectivity checks. They do not imply final schemas or storage behavior.

## Phase 2 migrations

The Phase 2 run spine uses raw SQL migrations stored in `infra/migrations/`.

Apply migrations against the local Postgres container:

```bash
make infra-up
make db-migrate
```

Check migration status:

```bash
uv run atlas-db status
```

Roll back the latest migration:

```bash
make db-rollback
```
