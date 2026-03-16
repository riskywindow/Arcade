# apps/console

Next.js operator console shell.

Phase 1 scope:

- app boot,
- minimal layout,
- placeholder routes for home, runs, scenarios, and system status,
- no replay or task UI yet.

Local run:

```bash
pnpm --filter @atlas/console dev
```

Future replay UI insertion points:

- `app/runs/` for run list and run detail routes
- `components/` for replay panels and event timeline primitives
- `lib/api/` for typed console-to-API boundaries
