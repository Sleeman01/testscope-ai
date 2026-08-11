#!/usr/bin/env bash
# kubernetes/dev/smoke-test.sh
set -euo pipefail
NAMESPACE="${1:-dev}"
HOST="${2:-dev.testscope.local}"

kubectl -n "$NAMESPACE" wait --for=condition=available --timeout=120s deployment/api deployment/worker deployment/frontend deployment/mcp-test-analysis deployment/mcp-github

response=$(curl -s -o /dev/null -w "%{http_code}" --retry 3 --retry-delay 2 --retry-connrefused "http://$HOST/api/health/live")
if [ "$response" != "200" ]; then
  echo "Smoke test failed: /api/health/live returned $response"
  exit 1
fi
echo "Smoke test passed."
