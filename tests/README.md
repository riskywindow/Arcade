# Tests

This directory already contains Phase 1 scaffold validation.

Current coverage:

- API `/health` smoke
- worker boot smoke
- top-level smoke-check entrypoint
- Phase 2 migration integration coverage for the run spine when local Postgres is available

Phase 2 should expand this directory with real domain and integration tests without bypassing the existing smoke path.
