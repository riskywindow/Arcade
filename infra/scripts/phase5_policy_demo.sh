#!/bin/zsh
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$REPO_ROOT"

RUN_ID="${RUN_ID:-phase5-policy-demo-001}"
SEED="${SEED:-seed-phase3-demo}"
BROWSER_MODE="${BROWSER_MODE:-stub}"
RESET_DB="${RESET_DB:-0}"
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
APPROVAL_TIMEOUT_SECONDS="${APPROVAL_TIMEOUT_SECONDS:-180}"

if [[ "$RESET_DB" == "1" ]]; then
  UV_CACHE_DIR="$UV_CACHE_DIR" uv run atlas-db down --steps 1 || true
fi

UV_CACHE_DIR="$UV_CACHE_DIR" uv run atlas-db up

cat <<EOF
Phase 5 policy-protected demo starting.

Run ID: $RUN_ID
Scenario: travel-lockout-recovery
Seed: $SEED
Browser mode: $BROWSER_MODE

This worker will pause for operator approval. While it is waiting:
  1. Start the API in another terminal with: make api-dev
  2. Optionally inspect the approval in the console at /runs
  3. Approve it with:
     curl -X POST http://127.0.0.1:8000/runs/$RUN_ID/approvals/approval-toolreq-identity-approve-001/approve \\
       -H 'content-type: application/json' \\
       -d '{"operator_id":"local-operator","resolution_summary":"Approve the limited MFA recovery path."}'

EOF

UV_CACHE_DIR="$UV_CACHE_DIR" uv run atlas-worker policy-demo \
  --run-id "$RUN_ID" \
  --seed "$SEED" \
  --browser-mode "$BROWSER_MODE" \
  --approval-timeout-seconds "$APPROVAL_TIMEOUT_SECONDS"

cat <<EOF

Phase 5 policy-protected demo completed.

Inspect the stored run with:
  curl http://127.0.0.1:8000/runs/$RUN_ID
  curl http://127.0.0.1:8000/runs/$RUN_ID/events
  curl http://127.0.0.1:8000/runs/$RUN_ID/audit
  curl http://127.0.0.1:8000/runs/$RUN_ID/approvals
  curl http://127.0.0.1:8000/runs/$RUN_ID/artifacts
EOF
