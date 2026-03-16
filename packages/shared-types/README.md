# packages/shared-types

Shared TypeScript contracts shell.

Real runtime contracts are deferred until Phase 2.

Ownership:

- browser-facing and API-facing TypeScript contracts live here
- Python-internal models do not belong here
- contracts should stay additive and transport-oriented

Allowed imports:

- console code may import from this package
- this package should not depend on app code
