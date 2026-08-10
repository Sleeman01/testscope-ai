#!/usr/bin/env bash
# kubernetes/prod/smoke-test.sh (copy of kubernetes/dev/smoke-test.sh with prod defaults)
set -euo pipefail
NAMESPACE="${1:-prod}"
HOST="${2:-testscope.local}"

kubectl -n "$NAMESPACE" wait --for=condition=available --timeout=120s deployment/api deployment/worker deployment/frontend deployment/mcp-test-analysis deployment/mcp-github

response=$(curl -s -o /dev/null -w "%{http_code}" "http://$HOST/api/health/live")
if [ "$response" != "200" ]; then
  echo "Smoke test failed: /api/health/live returned $response"
  exit 1
fi
echo "Smoke test passed."
