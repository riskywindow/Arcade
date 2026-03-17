# Tests

This directory contains the Phase 2 spine safety net plus the Phase 3 environment hardening checks.

Current coverage:

- API `/health` smoke
- worker boot smoke
- top-level smoke-check entrypoint
- Phase 2 migration integration coverage for the run spine when local Postgres is available
- schema and serialization validation for `Run`, `RunEvent`, and `Artifact`
- run state-machine unit coverage for valid and invalid transitions
- repository and API integration coverage for run/event/artifact retrieval
- worker dummy execution coverage for the deterministic local demo path
- worker agent execution coverage for the deterministic Phase 4 seeded demo path
- Phase 3 determinism and reset coverage for seeded helpdesk, directory, wiki, and inbox state
- hidden/public separation coverage for public scenario metadata and API payloads
- deterministic grader coverage for the first 5 seeded tasks
- worker scripted smoke coverage for two seeded Phase 3 tasks when local Postgres is available

Future phases should extend this directory without bypassing the existing smoke path or the Phase 2 run/event spine tests.

Phase 3 contributors should also read:

- [phase-3-environment-overview.md](/Users/rishivinodkumar/Arcade/docs/environments/phase-3-environment-overview.md)
- [helpdesk-graders.md](/Users/rishivinodkumar/Arcade/docs/evals/helpdesk-graders.md)
