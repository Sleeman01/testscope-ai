#!/usr/bin/env bash
# kubernetes/prod/smoke-test.sh (copy of kubernetes/dev/smoke-test.sh with prod defaults)
set -euo pipefail
NAMESPACE="${1:-prod}"
HOST="${2:-testscope.local}"

# 300s, not dev's 120s: every tagged prod deploy retags all 4 built images at once, and (unlike
# dev) prod's worker/mcp-github/auth-proxy CPU requests were deliberately cut thin to fit the
# shared worker node (see kubernetes/prod/worker-resources-patch.yaml /
# mcp-github-resources-patch.yaml) — so a real deploy triggers a simultaneous 5-Deployment
# rolling-update surge under constrained headroom, which a cold multi-image pull plus scheduling
# squeeze can genuinely take longer than 120s to clear even with no actual defect (confirmed:
# tag v1.0.2's deploy-prod.yml run timed out here on 4/5 Deployments, but a live kubectl check
# minutes later showed every Deployment Running/Ready — the work finished, the wait didn't).
kubectl -n "$NAMESPACE" wait --for=condition=available --timeout=300s deployment/api deployment/worker deployment/frontend deployment/mcp-test-analysis deployment/mcp-github

response=$(curl -s -o /dev/null -w "%{http_code}" "http://$HOST/api/health/live")
if [ "$response" != "200" ]; then
  echo "Smoke test failed: /api/health/live returned $response"
  exit 1
fi
echo "Smoke test passed."
