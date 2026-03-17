#!/bin/zsh
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$REPO_ROOT"

RUN_ID="${RUN_ID:-phase4-agent-demo-001}"
SCENARIO_ID="${SCENARIO_ID:-mfa-reenrollment-device-loss}"
SEED="${SEED:-seed-phase3-demo}"
BROWSER_MODE="${BROWSER_MODE:-stub}"
RESET_DB="${RESET_DB:-0}"
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"

if [[ "$RESET_DB" == "1" ]]; then
  UV_CACHE_DIR="$UV_CACHE_DIR" uv run atlas-db down --steps 1 || true
fi

UV_CACHE_DIR="$UV_CACHE_DIR" uv run atlas-db up
UV_CACHE_DIR="$UV_CACHE_DIR" uv run atlas-worker agent-demo \
  --run-id "$RUN_ID" \
  --scenario-id "$SCENARIO_ID" \
  --seed "$SEED" \
  --browser-mode "$BROWSER_MODE"

cat <<EOF

Phase 4 seeded agent demo completed.

Run ID: $RUN_ID
Scenario: $SCENARIO_ID
Seed: $SEED
Browser mode: $BROWSER_MODE

If the API is running in another terminal via \`make api-dev\`, inspect it with:
  curl http://127.0.0.1:8000/runs/$RUN_ID
  curl http://127.0.0.1:8000/runs/$RUN_ID/events
  curl http://127.0.0.1:8000/runs/$RUN_ID/artifacts
EOF
