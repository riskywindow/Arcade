# packages/shared-types

Shared TypeScript transport contracts.

Current ownership:

- browser-facing and API-facing TypeScript contracts live here
- run, event, artifact, and API response/request transport shapes live here
- Python-internal models and DB schema do not belong here
- contracts should stay additive and transport-oriented

Allowed imports:

- console code may import from this package
- this package should not depend on app code
