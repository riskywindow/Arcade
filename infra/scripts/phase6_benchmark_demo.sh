#!/bin/zsh
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$REPO_ROOT"

CATALOG_ID="${CATALOG_ID:-helpdesk-v0}"
BASELINE_BENCHMARK_RUN_ID="${BASELINE_BENCHMARK_RUN_ID:-benchmark-helpdesk-v0-baseline}"
CANDIDATE_BENCHMARK_RUN_ID="${CANDIDATE_BENCHMARK_RUN_ID:-benchmark-helpdesk-v0-regressed}"
SAMPLE_REPORT_PATH="${SAMPLE_REPORT_PATH:-docs/demos/phase6-benchmark-sample-report.md}"
RESET_DB="${RESET_DB:-0}"
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"

if [[ "$RESET_DB" == "1" ]]; then
  UV_CACHE_DIR="$UV_CACHE_DIR" uv run atlas-db down --steps 1 || true
fi

UV_CACHE_DIR="$UV_CACHE_DIR" uv run atlas-db up

cat <<EOF
Phase 6 benchmark fixture flow starting.

Catalog: $CATALOG_ID
Baseline benchmark run: $BASELINE_BENCHMARK_RUN_ID
Candidate benchmark run: $CANDIDATE_BENCHMARK_RUN_ID
Sample report path: $SAMPLE_REPORT_PATH

This flow will:
  1. execute the deterministic helpdesk benchmark as a clean baseline
  2. execute the same benchmark as a candidate
  3. apply a synthetic regression fixture to the candidate
  4. write a markdown sample report for docs and review

EOF

UV_CACHE_DIR="$UV_CACHE_DIR" uv run atlas-worker benchmark-fixture \
  --catalog-id "$CATALOG_ID" \
  --baseline-benchmark-run-id "$BASELINE_BENCHMARK_RUN_ID" \
  --candidate-benchmark-run-id "$CANDIDATE_BENCHMARK_RUN_ID" \
  --sample-report-path "$SAMPLE_REPORT_PATH"

cat <<EOF

Phase 6 benchmark fixture flow completed.

Inspect with the API:
  curl "http://127.0.0.1:8000/benchmarks/catalogs/$CATALOG_ID/runs/$BASELINE_BENCHMARK_RUN_ID"
  curl "http://127.0.0.1:8000/benchmarks/catalogs/$CATALOG_ID/runs/$CANDIDATE_BENCHMARK_RUN_ID"
  curl "http://127.0.0.1:8000/benchmarks/catalogs/$CATALOG_ID/compare?baseline_benchmark_run_id=$BASELINE_BENCHMARK_RUN_ID&candidate_benchmark_run_id=$CANDIDATE_BENCHMARK_RUN_ID"

Inspect in the console:
  http://127.0.0.1:3000/reports/benchmarks/$CATALOG_ID/$CANDIDATE_BENCHMARK_RUN_ID?baseline=$BASELINE_BENCHMARK_RUN_ID

Sample markdown report:
  $SAMPLE_REPORT_PATH
EOF
