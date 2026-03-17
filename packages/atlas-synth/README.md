# packages/atlas-synth

Deterministic synthetic company models and the canonical Northstar fixture builder.

Current Phase 3 scope:

- explicit typed world records for company, departments, employees, devices, accounts, tickets, wiki pages, inbox threads, and suspicious events
- deterministic seed-driven IDs and timestamps
- canonical `Northstar Health Systems` base-world fixture
- diffable world snapshot output with scenario overlays kept separate
- fixture session utilities for load, reset, rehydrate, and baseline diffing

Example:

```python
from atlas_synth import build_canonical_world, summarize_world

snapshot = build_canonical_world("seed-phase3-demo")
summary = summarize_world(snapshot)
```

Reset workflow:

```python
from atlas_synth import CanonicalFixtureSession

session = CanonicalFixtureSession.load("seed-phase3-demo")
baseline = session.snapshot()

# ...replace or mutate a copied snapshot in a higher-level environment package...

reset_snapshot = session.reset()
assert reset_snapshot == baseline
```

Example summary:

- company: `Northstar Health Systems`
- employees: `10`
- tickets: `9`
- wiki pages: `8`
- inbox threads: `5`
- suspicious events: `2`

Allowed imports:
- may import `atlas-core`
- should not import `atlas-env-helpdesk`, `atlas-graders`, or app/service packages
