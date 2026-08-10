#!/usr/bin/env bash
# scripts/local-e2e-smoke-test.sh
#
# Targets Sleeman01/testscope-ai#20 over real github.com (via the mcp-github/
# mcp-github-upstream auth-proxy pair in docker-compose.yml, using GITHUB_PAT) — accepted
# scope change from the original "local fixture repo" plan text; the official
# github-mcp-server image has no way to target a local git repository instead of github.com
# (confirmed: no such CLI flag or env var exists in the image).
#
# Issue #20 is a purpose-built, permanent fixture in this repo (title: "[Smoke Test Fixture]
# Sample acceptance criteria for local E2E test") — not octocat/Hello-World, the plan's
# original literal target. octocat/Hello-World structurally cannot produce a `completed`
# result: every issue on that repo (confirmed directly via the GitHub API, not assumed) has
# an empty or near-empty body — it's GitHub's generic tutorial/practice repo, so there is no
# issue anywhere on it with real acceptance-criteria content for the Requirement Parser node
# to extract. Do not close or edit issue #20 except when updating this smoke test
# intentionally — this script depends on its exact content staying stable.
#
# Requires ANTHROPIC_API_KEY and GITHUB_PAT already exported when `docker compose up` was
# run — see docker-compose.yml's header comment.
set -euo pipefail

echo "Submitting analysis..."
RESPONSE=$(curl -s -X POST http://localhost:8001/api/analyses \
  -H "Content-Type: application/json" \
  -d '{"repository": "Sleeman01/testscope-ai", "issue_number": 20}')
ANALYSIS_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['analysis_id'])")
echo "Analysis ID: $ANALYSIS_ID"

for i in $(seq 1 60); do
  STATUS=$(curl -s "http://localhost:8001/api/analyses/$ANALYSIS_ID" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
  echo "Status: $STATUS"
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  sleep 5
done

if [ "$STATUS" != "completed" ]; then
  echo "Smoke test FAILED: final status was $STATUS"
  exit 1
fi

curl -s "http://localhost:8001/api/analyses/$ANALYSIS_ID/report" | python3 -m json.tool
echo "Smoke test PASSED."
