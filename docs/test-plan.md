# TestScope AI — Test Plan

## Philosophy

Every layer mocks the layer below it except one: MCP tool calls, which are always tested
against the real MCP transport (streamable-HTTP) rather than mocked, per the assignment's
explicit integration-test requirement. The LLM is never called for real outside Task 43's
one deliberate manual smoke test — every automated test (unit, MCP integration, worker E2E,
API, frontend) uses a stub LLM client returning canned structured output.

## Test Layers

| Layer | What's tested | How | Built in |
|---|---|---|---|
| Unit — MCP tools | `extract_test_metadata` (`ast` parsing), `find_test_files`, `read_test_file`, `cleanup_workspace`, `save_coverage_report`, `get_previous_analysis` — valid/invalid input, empty results, oversized files/repos, storage failure, access-denied | Zero mocking for `extract_test_metadata` (pure `ast`, deterministic); `moto` for S3/DynamoDB; a local bare git repo fixture (no network) for clone-dependent tools | Tasks 2–7 |
| Integration — MCP transport | The full `mcp-test-analysis` server over real streamable-HTTP, not function calls | Spins up `server.py` as a subprocess, connects a real `ClientSession`, calls tools by name exactly as `worker`/`api` would | Task 8 |
| Unit — `backend/shared` | `AnalysisRecord` round-trip, `AnalysisStore`/`ReportStore`/`JobQueue` CRUD, idempotent upsert, GSI queries | `moto` for DynamoDB/S3/SQS — never real AWS | Task 9 |
| Unit — retry/classification | `with_retry`'s backoff/exhaustion behavior; `mcp_clients._is_retryable_tool_error`'s terminal-vs-transient classification | Fake flaky/always-failing async functions, no network | Task 11 |
| Unit — worker LangGraph nodes | All 11 nodes (Request Validator through Report Saver) individually: happy path, each documented failure-handling behavior from design.md §4/§13 (graceful termination, non-fatal warnings, fabricated-evidence stripping) | `call_llm`/`call_github_tool`/`call_test_mcp_tool` mocked per-node via `unittest.mock.patch`; stub Pydantic model instances stand in for LLM output | Tasks 10–17 |
| Integration/E2E — worker | Full `run_analysis(...)` pipeline reaching `status=completed`, including a real `mcp-test-analysis` subprocess | Stub LLM (`app.llm_client.call_llm` patched at the module level), stub GitHub tool responses, real MCP transport, `moto`-mocked AWS | Task 17 |
| Unit — `backend/api` | Every route: validation, 404/409 status codes, presigned URL generation, GitHub-issue gating on `status=completed` | `TestClient` + `moto` | Tasks 18–22 |
| Unit — observability | `/metrics` exposes and increments expected counters | `TestClient`, no external Prometheus needed | Task 39 |
| Unit — frontend | API client (`fetch` calls), Home/Results/History page behavior (form submission, polling, rendering, confirm-before-create-issue) | Vitest + Testing Library, `fetch` stubbed | Tasks 23–26 |
| Infrastructure verification (not unit tests — live checks against real infra) | Terraform `validate`/`plan` on every module; post-`apply` `kubectl get nodes` cluster-convergence check; live Prometheus-targets and Grafana-datasources check; CloudWatch alarm fire/clear cycle | Real `terraform`, real `kubectl`/`ssh`, real `aws` CLI against the actually-provisioned `dev` environment | Tasks 27–31 (Terraform), 40 (Prometheus/Grafana), 42 (CloudWatch) |
| Infrastructure verification — live CI/CD deploy | Real `kubectl apply` (via `kustomize`) + post-deploy smoke test against the actually-deployed `dev` and `prod` clusters | GitHub Actions `deploy-dev.yml`/`deploy-prod.yml`, self-hosted runner on the control-plane EC2 node, `production` Environment manual-approval gate | Tasks 36–38 (pipeline itself) + PRs #22–28 (post-Phase-10 hardening that got real deploys actually passing — see `project-log.md`) |
| Local full-stack E2E | One real request through every service (`frontend`→`api`→SQS→`worker`→MCP servers→DynamoDB/S3), plus exactly one real Claude API call as final hand-verification | `docker-compose` with LocalStack standing in for AWS; the one real LLM call is manual, not part of any CI job | Task 43 |

## Success Criteria

- ≥80% line coverage on `mcp-server/`, `backend/shared/`, `backend/worker/app/`, `backend/api/app/` (enforced by `--cov-fail-under=80` in Task 36's PR pipeline; a failing threshold blocks merge).
- All PR-pipeline checks green pre-merge: lint, unit tests, MCP integration test, image builds, Trivy scan (Task 36).
- MCP integration suite (Task 8) passes against real transport, not mocks — this is the assignment's specific integration-test requirement and is never skipped or weakened to a mock in CI.
- Post-deploy smoke test (`kubernetes/dev/smoke-test.sh` / `kubernetes/prod/smoke-test.sh`, Tasks 37/38) passes in both `dev` and `prod` after every deploy — verified, not aspirational: `dev` has been green since PR #24 (4+ consecutive runs); `prod`'s first genuine green run is tag `v1.0.3` (run `31473796895`, 2026-08-11), reached only after diagnosing and fixing three distinct real deploy-time failures along the way (GHCR permissions/tag-casing, a kustomize/kubectl-version mismatch, and a smoke-test timeout too short for prod's constrained-capacity rolling-update surge) — full detail in `project-log.md`'s post-Phase-10 CI/infra saga entries (PRs #22–28).
- Task 40's live Prometheus-targets/Grafana-datasources check passes at least once before the presentation (this is what the live "show your observability dashboard" demo depends on).
- Task 43's local full-stack smoke test passes, including the one deliberate real Claude API call, as the final proof the live LLM integration works end-to-end.

## Out of Scope

Load/performance testing, chaos/fault-injection testing beyond the specific failure-handling
paths in design.md §13, and browser/cross-device compatibility testing beyond what Vitest +
Testing Library's jsdom environment exercises — all stated v1 limitations, not gaps.
