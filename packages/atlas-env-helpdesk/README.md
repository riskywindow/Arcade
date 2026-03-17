# packages/atlas-env-helpdesk

Deterministic helpdesk environment package for the Phase 3 and Phase 4 synthetic company path.

Current scope:

- internal scenario catalog with public and hidden state separation
- seeded helpdesk, directory, wiki, and inbox services
- typed environment-owned adapters for seeded helpdesk ticket operations
- typed environment-owned adapters for deterministic wiki/doc lookup and employee directory lookup
- private hidden-scenario state records for grader consumption
- no Bastion policy enforcement
- no in-package agent loop; Phase 4 worker orchestration consumes these environment-owned adapters

Start with:

- [phase-3-environment-overview.md](/Users/rishivinodkumar/Arcade/docs/environments/phase-3-environment-overview.md)
- [scenario-authoring.md](/Users/rishivinodkumar/Arcade/docs/environments/scenario-authoring.md)

Allowed imports:
- may import `atlas-core` and `atlas-synth`
- should not import `atlas-graders`, app packages, or service packages
