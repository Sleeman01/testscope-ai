# TestScope AI — Design Specification

## 1. Problem Statement

QA engineers and developers already rely on automated code coverage tools (pytest-cov, Codecov, etc.) to know which lines of code execute during tests — but line/branch coverage doesn't answer whether a specific requirement is actually verified. Mapping acceptance criteria to existing tests, and judging whether a test's intent matches a criterion (not just its code path), remains a manual, repetitive task: reading the issue, searching the repo, opening candidate test files, and judging fit — one criterion at a time. This is time-consuming and error-prone at scale, especially for permission rules, boundary values, and negative cases that are easy to have partial or no test coverage for despite a high code-coverage percentage.

**TestScope AI** is an AI agent that automates the first pass of this analysis: given a repository and a GitHub issue number, it retrieves the issue, extracts structured acceptance criteria, finds and reads relevant automated tests, classifies coverage per criterion, generates a full test plan, recommends missing test scenarios, and stores the analysis — with an optional user-approved step to file a GitHub issue for the gaps it finds.

It does not replace a QA engineer's judgment; it reduces the repetitive analysis work so a human can review and act faster.

**Target users:** manual QA engineers, automation engineers, developers, tech leads, and small teams without dedicated QA.

**Example scenario:** *"Analyze GitHub issue 42 and check whether the repository tests cover all acceptance criteria."* → The agent retrieves issue 42 via the GitHub MCP server, extracts requirements, searches the repo for relevant tests, reads matching tests, compares each requirement against existing tests, generates a test plan, produces a coverage matrix (Covered / Partially covered / Not covered / Unable to determine per criterion), suggests missing scenarios, saves the analysis, and — only if the user approves — creates a GitHub issue listing the missing tests.

**Measurable value:** target reducing the initial requirement/coverage analysis pass from ~30–60 minutes of manual work to under 5 minutes agent-assisted. Tracked via: time saved, % of acceptance criteria analyzed, missing scenarios identified, % of recommendations accepted, average analysis duration, user rating.

## 2. Scope

**v1 will:** read a GitHub issue and its comments, extract structured acceptance criteria (flagging gaps instead of inventing requirements), search a repository for Python/pytest test files relevant to those criteria, classify each criterion's coverage with evidence, generate a full categorized test plan, recommend missing scenarios with justification and priority, persist the analysis (DynamoDB + S3), and optionally create a GitHub issue for missing coverage — only after explicit user approval.

**v1 will not:** write test code, open PRs, modify application code, merge branches, approve releases, execute production changes, analyze arbitrarily large repos in full, support SCM platforms other than GitHub, or auto-create GitHub issues without confirmation. It targets **Python/pytest only** for test-file understanding in v1; the architecture (MCP tool boundaries, deterministic metadata extraction separate from semantic matching) is kept generic enough to add JS/Jest/Playwright support later without a redesign.

## 3. Architecture Overview

```
┌─────────────┐      enqueue       ┌──────────┐
│  React UI   │ ─────────────────▶ │  FastAPI │──▶ DynamoDB (status/read)
│ (frontend)  │ ◀───status/report──│   (api)  │──▶ S3 (report read)
└─────────────┘                    └────┬─────┘
                                         │ SQS (analysis job)
                                         ▼
                                   ┌──────────┐      MCP (HTTP)        ┌──────────────────────┐
                                   │  worker  │ ───────────────────▶  │ mcp-github            │
                                   │(LangGraph│                        │ (official GitHub MCP) │
                                   │  agent)  │                        └──────────────────────┘
                                   │          │      MCP (HTTP)        ┌──────────────────────┐
                                   │          │ ───────────────────▶  │ mcp-test-analysis     │
                                   └────┬─────┘                        │ (custom, this repo)   │
                                        │                              └──────────┬────────────┘
                                        ▼                                         ▼
                                  DynamoDB + S3                          shallow git clone
                                  (report write)                        (temp workspace, per job)
```

**Services:** a FastAPI `api` service (HTTP surface, enqueues jobs, reads status/reports), a `worker` service (runs the LangGraph agent, consumes SQS, calls both MCP servers), the custom `mcp-test-analysis` MCP server (this repo's domain-specific tools), the official `mcp-github` MCP server (read-only GitHub access plus gated issue creation), and a React `frontend`.

The API/worker split lets the worker scale independently on its (CPU-bound-for-MVP) load without coupling to HTTP request volume, and keeps the LLM/MCP-heavy work off the request-serving path.

## 4. Agent Workflow (LangGraph, runs in `worker`)

Steps 2–12 are `StateGraph` nodes. Job Intake (1) and Cleanup (13) are numbered alongside them here because they're conceptually part of the same per-analysis workflow, but they're implemented as plain wrapper code around `graph.ainvoke(...)` rather than as graph nodes themselves — Job Intake has to run *before* the graph starts (so a malformed job is recorded even if the graph never runs), and Cleanup has to run in a `finally` block so it fires on a timeout or an unhandled exception, not just on normal graph completion. A `StateGraph` node can't guarantee either of those on its own.

| # | Node | Does | Failure handling |
|---|------|------|-------------------|
| 1 | Job Intake | Dequeue SQS message, upsert `status=running` to DynamoDB keyed by `analysis_id` | Malformed message → log, ack, skip (no infinite redrive). Idempotent: redelivery just re-upserts the same item |
| 2 | Request Validator | GitHub MCP `get_repository` — confirms repo exists/accessible, gets default branch | Not found / access denied → terminate, `status=failed`, clear user-facing reason |
| 3 | Requirement Retriever | GitHub MCP `get_issue`, `get_issue_comments` | Comments fetch fails → fall back to issue body only |
| 4 | Requirement Parser (LLM) | Extracts feature name, objective, acceptance criteria (each gets an ID), validation rules, roles, constraints. Flags gaps instead of inventing them | Zero extractable criteria → terminate gracefully, `status=failed`, reason="no acceptance criteria found" (partial report still saved) |
| 5 | Test Search Planner (LLM) | Generates search keywords per criterion (function/endpoint/component names, domain terms) | — |
| 6 | Test File Retriever | Test MCP `find_test_files` (clones on first call for the job, ranks/caps at 30 files) | No matches → continue; all criteria eligible for "Not covered" |
| 7 | Test File Classifier | Test MCP `extract_test_metadata` per candidate file (deterministic, no LLM) | Single file fails to parse → skip it, log warning, continue |
| 8 | Coverage Analyzer (LLM) | Maps each criterion to test metadata; classifies Covered / Partially covered / Not covered / Unable to determine with evidence. Calls `read_test_file` for full content only on ambiguous matches (bounds token cost) | Still ambiguous after reading full file → "Unable to determine", never guesses |
| 9 | Test Plan Generator (LLM) | Full scenario list: positive, negative, validation, boundary-value, permission/role, API, UI, integration, error-handling, regression | — |
| 10 | Missing-Test Recommender (LLM) | Per gap: missing behavior, why it matters, suggested type/priority, related criterion, risk if not added | — |
| 11 | Quality Validator | Cross-checks: every criterion has a status, every cited file path came from actual `find_test_files` results (no fabrication), flags low-confidence output | Fabricated reference detected → stripped, warning added to report |
| 12 | Report Saver | Test MCP `save_coverage_report` → DynamoDB + S3, upsert by `analysis_id` (idempotent) | Save fails → analysis still returned to caller; `storage_status=failed` logged/alerted, not silently dropped |
| 13 | Cleanup (`finally`) | Test MCP `cleanup_workspace(analysis_id)` | Always runs, regardless of which node failed |

**Overall timeout:** the entire LangGraph run is wrapped in a 10-minute wall-clock timeout, independent of per-node retries — a hung LLM call or stuck node cannot occupy a worker indefinitely. On timeout, cleanup still runs (via `finally`), `status=failed` with reason `"analysis timed out"`, and the SQS message is left to redeliver/DLQ per the existing policy.

**Retries:** transient errors (timeouts, 5xx, GitHub rate limit) get 3 attempts with exponential backoff (1s/2s/4s) at the tool-call level. Validation/not-found/access-denied errors fail fast, no retry. This distinction is implemented once, in the MCP/GitHub client wrapper itself (not duplicated per node): a classifier inspects the error and only retries when it doesn't look terminal, so every node that calls an MCP or GitHub tool gets both behaviors automatically. SQS redrive policy sends a job to a DLQ after 3 receive attempts; DLQ arrival triggers an alert and the job is marked `failed`.

**Idempotency:** Job Intake and Report Saver are both plain upserts keyed on `analysis_id`. SQS's at-least-once delivery means a job may be processed more than once; last-write-wins is accepted as sufficient for v1 — reprocessing costs an extra LLM call but never corrupts state.

## 5. MCP Tooling

### 5.1 Test Analysis MCP (custom, built in this repo)

| Tool | Signature | Notes |
|---|---|---|
| `find_test_files` | `(analysis_id, repository, ref, keywords) → [{path, size_bytes, matched_keywords}]` | Clones on first call for that `analysis_id`, reuses the workspace on subsequent calls |
| `read_test_file` | `(analysis_id, path) → {content, truncated}` | Truncates files over 50KB, sets `truncated=true` |
| `extract_test_metadata` | `(analysis_id, path) → {tests: [{name, framework, decorators, docstring, fixtures_used, assert_count, string_literals, line_range}]}` | Deterministic (Python `ast` parse) — no LLM involved, fully unit-testable in isolation. Semantic interpretation ("is this criterion covered?") happens later in the Coverage Analyzer LLM node |
| `save_coverage_report` | `(analysis_id, repository, issue_number, requirement, coverage_matrix, missing_tests, test_plan, status, tool_call_trace) → {s3_report_key, dynamodb_status}` | Writes the DynamoDB record and the S3 `.md`/`.json` report |
| `get_previous_analysis` | `(repository, issue_number) → [{analysis_id, created_at, status, coverage_summary, s3_report_key}]` | Queries DynamoDB GSI1 |
| `cleanup_workspace` | `(analysis_id) → {deleted: bool}` | Called by the worker in a `finally` block at the end of every job |

**Workspace lifecycle (shallow git clone):**

- Each `mcp-test-analysis` pod mounts a k8s `emptyDir` volume at `/workspace` (`sizeLimit: 2Gi` — a node-level disk guard alongside the application-level check below). Every job gets `/workspace/{analysis_id}`, so concurrent jobs never collide.
- The **MCP server holds its own GitHub token via its own K8s Secret** — the token is never passed as a per-call parameter from the worker, minimizing where it could leak into logs or traces.
- Before cloning, the tool calls GitHub (via `mcp-github`) for repo metadata and rejects repos over 500MB without cloning at all (`REPO_TOO_LARGE`).
- Clone: `git clone --depth 1 --single-branch --branch <default_branch> ...`, run via `subprocess` with a 30s timeout.
- Failure codes: `REPO_NOT_FOUND`, `REPO_ACCESS_DENIED`, `REPO_TOO_LARGE`, `CLONE_TIMEOUT`, `CLONE_FAILED` (stderr excerpt, secrets redacted). Any failure removes the partial directory immediately, inside the tool handler.
- **Primary cleanup:** the worker calls `cleanup_workspace(analysis_id)` in a `finally` block at the end of every job, success or failure.
- **Backstop:** a background sweeper thread in the MCP server deletes any workspace directory older than 1 hour, on a 15-minute interval, catching orphans from crashed workers.

### 5.2 GitHub MCP (official server)

Deployed as its own `mcp-github` service (Docker image `ghcr.io/github/github-mcp-server`, run in `http` subcommand mode — the default invocation starts an stdio server, not HTTP; the container must be started as `... github-mcp-server http --port 8100 --listen-host 0.0.0.0`, and the client must send the token as an `Authorization: Bearer <token>` header, not just the `GITHUB_PERSONAL_ACCESS_TOKEN` env var, which HTTP mode ignores for request auth).

**Verified against the real deployed server (plan.md Task 8, `v1.8.0`, checked with both the default toolset and `--toolsets=all` — 54 tools total):** this design's original tool-name assumption was wrong, not just approximately right. `get_repository`, `get_issue`, `get_issue_comments`, and `create_issue` **do not exist** under those names in any toolset combination. The actual tool surface is a smaller set of consolidated, multi-method tools:

| Assumed (v1, never existed) | Actual tool | Fit |
|---|---|---|
| `get_repository` (→ `default_branch`, `size`) | **No direct equivalent.** Closest: `search_repositories` with `query: "repo:{owner}/{repo}"`, `minimal_output: false` → `items[0].default_branch` / `items[0].size` (KB). Confirmed working. | Usable, but it's a *search* endpoint — separate rate limits and index lag from a direct per-repo lookup, and can return zero items. |
| `get_issue` (→ `body`) | Closest: `issue_read` with `method: "get"`. | **Does not work** — `issue_read(method="get")` never returns the issue body, confirmed against a real populated issue (`microsoft/vscode#1`), not just a sparse test fixture. No MCP tool in this server returns a single issue's body by direct number lookup; `search_issues` includes `body` but only via a free-text search query, and GitHub search has no reliable "exact issue number" operator. |
| `get_issue_comments` | `issue_read` with `method: "get_comments"`. | Confirmed working — returns a list of comments, each with `body` intact. |
| `create_issue` (→ `html_url`) | `issue_write` with `method: "create"` (also handles `update`). | Schema accepts `owner`/`repo`/`title`/`body`/`labels`/etc. Not called during verification (same no-side-effects policy as the original plan — avoids creating a real GitHub issue), so the success response's field names (in particular, whether it returns `html_url`) are **unconfirmed**. Must be verified for real (or against the installed image's docs) before Task 22 ships. |

**Standing architectural decision — issue body fetch bypasses MCP:** since no MCP tool on this server returns an issue's body via direct lookup, `backend/worker/app/mcp_clients.py` (Task 11) fetches the issue body via a **direct GitHub REST API call** (`GET https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}`, `Authorization: Bearer <token>`) instead of through `mcp-github`, using the same token the MCP server would otherwise receive. Everything else GitHub-related — comments, repo metadata, issue creation — continues to route through `mcp-github` via MCP as originally designed; only the single body-fetch call is a direct REST exception. This keeps GitHub token custody exactly where §5.1 already requires it (worker/mcp-test-analysis Secrets only), it's just one more caller of that same token. `backend/api/app/mcp_client.py` (Task 22) is unaffected — issue *creation* still goes through `issue_write` over MCP.

`mcp-server/github_client.py` (Task 3/8) only ever needed `get_repo_size_bytes` — its real implementation uses the `search_repositories` substitute above. It has no issue-related methods; those belong to the worker's and api's separate, independently-implemented MCP clients (Task 11, Task 22), not yet built as of Task 8.

**SDK version note:** the installed `mcp` Python SDK resolved to `2.0.0` (plan.md pinned only `mcp>=1.1`, allowing an unpinned major-version jump that turned out to carry breaking changes) — `mcp.server.fastmcp.FastMCP` no longer exists at all; it's `mcp.server.MCPServer` now (same `.tool()`/`.run()` pattern, but `.run(transport="streamable-http")` needs explicit `host=`/`port=` kwargs, it does not read `MCP_HOST`/`MCP_PORT` itself). Client-side: `streamablehttp_client` → `streamable_http_client`; its context manager now yields `(read_stream, write_stream)`, not a 3-tuple; `Tool.inputSchema` → `Tool.input_schema`; `CallToolResult.structuredContent` → `structured_content`. **`structured_content` is `None` by default for any tool whose return type is a plain `dict`** — confirmed both for `github-mcp-server`'s tools and for `mcp-server`'s own `@mcp.tool()`-decorated functions (all of which are annotated `-> dict`), so this isn't an external-server quirk, it's this SDK's general structured-output behavior: it needs a schema-bearing return type (Pydantic model, `TypedDict`, dataclass) to auto-populate `structured_content`; a bare `dict` doesn't qualify. Every caller — `mcp-server/github_client.py` and `mcp-server/tests/test_mcp_integration.py` — parses `content[0].text` as JSON instead of relying on `structured_content`, and Tasks 11/22's future MCP clients should do the same rather than assume it's populated.

## 6. Data Model

**DynamoDB — table `testscope-analyses-{env}`** (PK: `analysis_id`, UUID):

| Attribute | Notes |
|---|---|
| `repository`, `issue_number` | |
| `status` | `pending \| running \| completed \| failed` |
| `created_at`, `updated_at` | ISO8601 |
| `requirement_summary`, `coverage_summary` | compact fields for list/detail views (% covered, counts per status) |
| `missing_tests_count` | |
| `s3_report_key` | pointer to the full report |
| `error_message`, `storage_status` | surfaces partial failures instead of hiding them |
| `tool_call_trace` | `[{node, tool, duration_ms, status}]`, recorded during the run — powers the UI's "tool-call history" |
| `github_issue_url` | nullable, set after `/github-issue` |
| `user_feedback` | nullable, stretch goal |

- **GSI1** — PK `repository#issue_number`, SK `created_at`: powers `get_previous_analysis` and repo/issue-scoped lookups.
- **GSI2** — PK constant `"ANALYSIS"`, SK `created_at`: powers the chronological History page listing without a table scan.

**S3 — bucket `testscope-reports-{env}`:** `{repository}/{issue_number}/{analysis_id}.md` and `.json`, written once by `save_coverage_report`.

## 7. HTTP API (FastAPI, `api` service)

| Endpoint | Behavior |
|---|---|
| `POST /api/analyses` | `{repository, issue_number, notes?}` → writes DynamoDB item `status=pending`, enqueues SQS job, returns `202 {analysis_id, status}` |
| `GET /api/analyses/{id}` | Current status + summary fields (poll target) |
| `GET /api/analyses/{id}/report` | Full report JSON (matrix, test plan, warnings, tool trace) + a short-lived presigned S3 URL for raw `.md` download; `409` if not yet `completed` |
| `GET /api/analyses?repository=&issue_number=&limit=&cursor=` | Paginated list via GSI1/GSI2 |
| `POST /api/analyses/{id}/github-issue` | Requires `status=completed`; user-approved trigger → GitHub MCP `create_issue` with the missing-tests summary; returns `{github_issue_url}` |
| `GET /health/live`, `GET /health/ready` | Readiness checks the API's own dependencies (DynamoDB, SQS reachability) |

**De-duplication:** v1 does **not** check for an existing pending/running analysis on the same `repository+issue_number` before enqueueing — a race-safe check adds complexity disproportionate to v1's needs. Duplicate concurrent submissions are accepted as a stated v1 limitation; each gets its own `analysis_id` and nothing corrupts.

**Authentication:** v1 has **no authentication**. The API is treated as internal-only (reachable within the cluster/demo network), and auth is explicitly out of scope for this project — a stated decision, not an oversight.

## 8. Web UI (React)

- **Home:** repo + issue number + optional notes → "Analyze test coverage" → navigates to Results, which polls `GET /api/analyses/{id}` until a terminal status.
- **Results:** requirement summary, acceptance criteria, coverage % + matrix table, existing tests found, missing scenarios (with priority), agent warnings, tool-call history (from `tool_call_trace`), "Create GitHub issue" button (confirms before calling `/github-issue`), "Download report" button (uses the presigned URL).
- **History:** table of past analyses (repo, issue, date, status, coverage result, link to report), backed by `GET /api/analyses`.

## 9. Infrastructure — AWS (Terraform)

- **Networking:** one VPC, public subnet, IGW, route table, one security group shared by both nodes (SSH restricted to admin IP; Kubernetes API 6443 internal-only; node-to-node cluster traffic — etcd, kubelet, scheduler/controller-manager, Calico BGP/VXLAN — self-referencing, not open to the internet; ingress 80/443 open).
- **Compute:** two EC2 instances — one control-plane node and one worker node — joined via `kubeadm`. Container runtime: containerd. CNI: Calico. `dev`, `prod`, and `monitoring` are namespaces on this one cluster, not separate clusters.
- **Access:** the SSH key pair both instances use is generated by Terraform itself (`tls_private_key` + `aws_key_pair`, private key written to a gitignored local file) — no "create a key pair in the console first" manual step, consistent with the "no manual clicking" requirement. The AMI is likewise resolved via a `data "aws_ami"` lookup (latest Ubuntu 22.04), not a hardcoded/manually-found id.
- **IAM:** the worker EC2 instance (where all application pods are scheduled — the control-plane's default `NoSchedule` taint is left in place) carries an attached IAM instance profile; pods get AWS access via instance-metadata credentials — no static AWS keys stored as k8s Secrets. Policy scoped to the specific per-env S3 buckets/DynamoDB tables/SQS queues below. The control-plane node runs no application workloads and does not need this profile.
- **S3:** `testscope-reports-dev`, `testscope-reports-prod`.
- **DynamoDB:** `testscope-analyses-dev`, `testscope-analyses-prod` (+ GSI1/GSI2 each).
- **SQS:** `testscope-jobs-dev` (+ DLQ), `testscope-jobs-prod` (+ DLQ), redrive after 3 receives.
- **CloudWatch:** log groups + alarms (§11).

```
terraform/
├── modules/ (networking, ec2, iam, s3, dynamodb, sqs, monitoring)
├── environments/
│   ├── shared/  (VPC, EC2 control-plane + worker, kubeadm bootstrap — provisioned once)
│   ├── dev/     (s3, dynamodb, sqs, iam policy, monitoring — dev-scoped)
│   └── prod/    (same, prod-scoped)
└── variables.tf
```

**Stated tradeoff — two-node kubeadm cluster (one control-plane, one worker) shared by dev, prod, and monitoring:** running all three environments on one cluster is a deliberate v1 choice, not an implicit gap. It saves significant cost and setup complexity (one VPC, two instances, one kubeadm install) relative to genuinely isolated clusters per environment. The cost: no real environment isolation (a `prod` resource-exhaustion event can affect `dev`, and vice versa) and a single point of failure (the control-plane going down takes the cluster API out for every environment at once, including monitoring, and — since all application pods run on the sole worker node — the worker going down takes out every workload). The worker is also where ingress itself lives (§10's `hostNetwork: true` binds ingress-nginx to that specific node), so `dev.testscope.local`/`testscope.local` must resolve to the worker's IP, not the control-plane's — pointing DNS at the control-plane leaves nothing listening on 80/443 at all. Acceptable for a course project's scale and demo needs; a production deployment would put at least `prod` on isolated infrastructure with multiple worker nodes.

## 10. Kubernetes Design (kubeadm, two-node EC2 cluster)

Two EC2 instances joined via `kubeadm`: one control-plane node (etcd, API server, scheduler, controller-manager) and one worker node (all workloads scheduled here — the control-plane's default `node-role.kubernetes.io/control-plane:NoSchedule` taint is left in place). Container runtime: containerd (systemd cgroup driver). CNI: Calico, applied once after `kubeadm init`.

Namespaces `dev`, `prod`, `monitoring`. Per env: `frontend`, `api`, `worker`, `mcp-test-analysis` (custom), `mcp-github` (official image, its own Deployment+Service — the worker reaches both MCP servers over MCP-over-HTTP).

- **Secrets:** GitHub token mounted only in `mcp-github`/`mcp-test-analysis`; Anthropic API key mounted only in `worker`. Neither reaches `api` or `frontend`.
- **ConfigMaps:** env name, log level, S3 bucket, DynamoDB table, SQS queue URL, MCP server addresses.
- **Resources (requests/limits):** `api` 100m/256Mi–500m/512Mi; `worker` 250m/512Mi–1000m/1Gi; MCP servers 200m/256Mi–500m/512Mi; `frontend` 50m/64Mi–200m/256Mi.
- **`mcp-test-analysis` volume:** `emptyDir` at `/workspace`, `sizeLimit: 2Gi`.
- **Probes:** `api`/`frontend`/both MCP servers expose `/health/live`, `/health/ready`. `worker` runs a minimal embedded health endpoint (checks SQS reachability) for its own liveness/readiness probes, since its main loop isn't HTTP-driven.
- **HPA:** `api` scales on CPU (min 1/max 3). `worker` scales on CPU as the MVP signal (metrics-server installed manually via its standard manifest, since kubeadm — unlike k3s — doesn't bundle one). True SQS-queue-depth-based scaling would need KEDA or a CloudWatch metrics adapter — documented as a post-MVP enhancement, not built now.
- **Ingress:** nginx-ingress controller (`ingress-nginx`), host-based routing (`dev.testscope.local`, `testscope.local`) for the demo environment. The controller is patched to `hostNetwork: true` so it binds host ports 80/443 directly on the worker node — the baremetal `ingress-nginx` manifest defaults to a `NodePort` Service (a random high port), and unlike k3s's bundled Traefik there's no `ServiceLB`-style component to auto-bind 80/443 for it. Both demo hostnames must resolve to the **worker's** IP, not the control-plane's (§9). Because `hostNetwork: true` binds directly to the worker's own network namespace, only one process on that host can hold 80/443 at a time — nothing else in this design binds those ports there, but it's a real constraint if anything ever does.

## 11. CI/CD Pipeline (GitHub Actions)

- **PR pipeline** (GitHub-hosted runners): install deps → lint/format (ruff/black, eslint/prettier) → unit tests (pytest + coverage, Jest) → MCP integration tests → build images (`api`, `worker`, `mcp-test-analysis`, `frontend`) → Trivy image scan → publish results via GitHub Actions job summary + Codecov → required check, blocks merge on failure.
- **Deploy jobs** (dev on merge to `main`; prod on manual approval via a GitHub Environment protection rule) run on a **self-hosted runner registered on the control-plane EC2 node** (holds the kubeadm admin kubeconfig) — avoids exposing the Kubernetes API server to the internet or storing a broadly-scoped kubeconfig as a GitHub secret. Deploy = push versioned images to GHCR → `kubectl apply` (via `kustomize`) to the target namespace → smoke test → report status.

## 12. Observability

- **Stack:** Prometheus + Grafana + Loki/Promtail, self-hosted in the `monitoring` namespace (one Grafana pane for metrics and logs), plus native CloudWatch metrics/alarms for AWS-managed resources (EC2, DynamoDB throttles, SQS queue age/DLQ count, S3 errors). Prometheus runs under its own `ServiceAccount` with a `ClusterRole` granting `get`/`list`/`watch` on pods (required for its `kubernetes_sd_configs`-based scrape discovery across `dev`/`prod`; without it, discovery calls return `403` and nothing gets scraped). Grafana's Prometheus/Loki datasources and the System Health dashboard are both provisioned via mounted ConfigMaps (Grafana's file-based provisioning, not the Grafana UI) so the pane is populated automatically on first boot — no manual "Add data source"/"Import dashboard" clicking.
- **App metrics** (`prometheus_client` `/metrics` on `api`/`worker`/both MCP servers): request rate/latency/errors, analyses started/succeeded/failed, analysis duration histogram, LLM call count/latency/failures, MCP tool-call count/latency/timeouts *by tool name*, clone duration/failures, storage save failures.
- **Logs:** structured JSON (`analysis_id`, `request_id`, `repository`, `issue_number`, node/tool name, duration, retry count, error type, final status) shipped to Loki. Secrets are never logged.
- **Alerts:** API error rate >5%/5min; worker analysis failure rate >20%/15min; elevated LLM/MCP timeout rate; SQS DLQ count >0 (CloudWatch → SNS); queue backlog age; pod restarts > N/10min; CPU/memory >85% sustained; readiness failing >2min.
- **Dashboard:** one "TestScope AI — System Health" Grafana dashboard: request volume/error rate, analysis latency p50/p95, LLM & MCP latency/timeouts by tool, SQS depth/DLQ, pod health, resource usage, recent failures (from Loki).

## 13. Error Handling (consolidated)

| Scenario | Handling |
|---|---|
| Repo/issue not found, private repo without permission | Request Validator terminates early, clear `status=failed` reason |
| GitHub rate limit | Retried with exponential backoff (3 attempts); fails fast beyond that |
| No acceptance criteria found | Graceful termination, partial report saved, reason recorded |
| No related tests found | Continue; all criteria eligible for "Not covered" |
| Unsupported framework (no pytest-style tests found) | Report explicitly states "No supported test framework detected; results may be incomplete" rather than reporting false "Not covered" confidence |
| MCP server unavailable/timeout | Retried (3x, backoff); node-level failure surfaces in `tool_call_trace` |
| LLM timeout/invalid response | Retried (3x, backoff); overall 10-minute wall-clock cap prevents indefinite hangs |
| S3/DynamoDB save failure | Analysis still returned to the caller; `storage_status=failed` logged and alerted, not silently dropped |
| Partial analysis / ambiguous coverage | "Unable to determine" used instead of guessing |

## 14. Testing Strategy

- **Unit tests** (mock LLM + AWS + GitHub): requirement extraction/parsing, search-query generation, coverage-matrix construction, missing-test formatting, retry/timeout/idempotency logic. `extract_test_metadata`'s `ast`-based parsing is fully deterministic and unit-tested with zero mocking.
- **MCP tool tests** (per tool, all 6 custom tools): valid/invalid input, missing repo/file, empty results, oversized files/repos, storage failure, timeout, access-denied.
- **MCP integration tests:** real MCP transport against a local fixture repo (a small bare git repo checked into test fixtures — cloned from a local path, not the network, keeping CI hermetic and offline).
- **API tests:** create-analysis validation, status/report retrieval, simulated GitHub/LLM/MCP/storage failures, health endpoints.
- **E2E:** fixture repo + a stub LLM client returning canned JSON (not live Claude calls) — deterministic, fast, no API cost or flakiness in CI. Runs the job through the real end-to-end pipeline (SQS intake → LangGraph agent → real MCP transport → storage) and asserts the final coverage matrix via the API/DynamoDB record — not a browser-driven UI test; no Playwright/Selenium/Cypress is used anywhere in this project.
- **Success criteria:** ≥80% unit coverage on core agent/MCP logic; all PR-pipeline checks green pre-merge; MCP integration suite passes against real transport; post-deploy smoke test passes in `dev` and `prod`.

This section is the design-time testing *strategy*. The standalone `docs/test-plan.md` deliverable the assignment requires separately — what's tested, how, and success criteria, traceable to the specific task that built each layer — is written last (plan.md's Task 44), after the suite described here actually exists to document.

## 15. Agent System Prompt

```
You are a software quality analysis agent.

Your role is to analyze software requirements, inspect available test files,
and produce evidence-based test plans and coverage reports.

You must:
- Base coverage decisions on retrieved repository evidence.
- Distinguish covered, partially covered, not covered, and unknown requirements.
- Identify uncertainty clearly.
- Avoid inventing repository files, requirements, or existing tests.
- Recommend missing tests with clear justification.
- Never modify code or create GitHub resources without user approval.
- Stop gracefully when required information is unavailable.
```

## 16. Repository Structure

```
testscope-ai/
├── docs/
│   ├── 2026-07-30-testscope-ai-design.md
│   ├── 2026-07-30-testscope-ai-plan.md
│   └── test-plan.md
├── backend/
│   ├── api/            (FastAPI service — routes, request/response models, main.py)
│   │   ├── app/
│   │   ├── tests/
│   │   └── Dockerfile
│   ├── worker/         (LangGraph agent — nodes, SQS consumer, main.py)
│   │   ├── app/
│   │   ├── tests/
│   │   └── Dockerfile
│   └── shared/         (common models, DynamoDB/S3 clients, config — imported by both api/ and worker/)
├── mcp-server/
│   ├── tools/
│   ├── server.py
│   ├── tests/
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── tests/
│   └── Dockerfile
├── kubernetes/ (base, dev, prod, monitoring)
├── terraform/ (modules, environments)
├── .github/workflows/
├── docker-compose.yml
└── README.md
```

## 17. Post-MVP / Stretch

Compare two analyses, export PDF reports, PR-level analysis, multi-framework support (JS/Jest/Playwright), test-code skeleton generation, user feedback capture, changed-requirement detection, KEDA/queue-depth-based worker autoscaling, specialized sub-agent decomposition, reusable project skill (per the assignment's optional extra-credit track).

## 18. Known Security Limitations (v1)

`npm audit` on `frontend/` reports 7 findings (1 critical, 1 high, 5 moderate) as of Task 1's scaffolding. Accepted as a documented v1 limitation rather than fixed, for the following reasons:

- **`vitest` (critical, `GHSA-5xrq-8626-4rwp`), `vite` (high, `fs.deny` bypass) and `esbuild` (moderate, dev-server request forwarding):** all three are dev-tooling-only — the vulnerable surface is either the Vitest `--ui` server (never invoked; the `test` script runs `vitest run`, and `@vitest/ui` isn't even installed) or the Vite dev server (`npm run dev`, used only for local development). None of these packages or code paths are present in the production artifact — `frontend/Dockerfile` builds static assets via `vite build` and serves them from `nginx:1.27-alpine`, which never runs vite/vitest/esbuild. Unreachable in CI or production.
- **`react-router-dom` (moderate, open-redirect via `<Link>`/`useNavigate`, `GHSA-jjmj-jmhj-qwj2`):** a real runtime dependency that does ship to production, but accepted for v1 because the API (§7) has no authentication and is explicitly internal-only — there's no session/credential for an open redirect to help exfiltrate, and the app is not exposed to the public internet. Fixing requires a v6→v7 migration (the entire `6.x` line, including the latest `6.30.4`, is within the vulnerable range; no patch exists short of the major version); deferred to post-MVP if this project continues past the course.

None of the 7 findings have a fix available via plain `npm audit fix` (verified — it changes nothing without `--force`); resolving any of them means bumping a dependency past the major version this plan pins (`vite ^5.4.10`, `vitest ^2.1.4`, `react-router-dom ^6.27.0`).
