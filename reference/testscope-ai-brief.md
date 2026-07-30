# Test Plan and Coverage Agent (TestScope AI)

## 1. Project Overview

The **Test Plan and Coverage Agent** is an AI-powered software quality assistant that analyzes requirements from GitHub, examines the existing automated tests in a repository, generates a structured test plan, and identifies missing test coverage.

The agent helps QA engineers and development teams answer questions such as:

* What should be tested for this feature?
* Which acceptance criteria are already covered?
* Which requirements are not covered by automated tests?
* What positive, negative, edge, API, and UI test cases are missing?
* Is the current test coverage sufficient for this feature?

The system is not intended to replace a QA engineer. Its purpose is to reduce repetitive analysis and help the QA engineer make faster and more consistent testing decisions.

## 2. Business Problem

Software requirements are commonly written in GitHub issues, feature descriptions, or acceptance criteria.

Before testing a feature, a QA engineer usually needs to:

1. Read and understand the requirement.
2. Extract each acceptance criterion.
3. Search the repository for related automated tests.
4. Determine which scenarios are already covered.
5. Identify missing positive and negative cases.
6. Write a complete test plan.
7. Create follow-up tasks for missing coverage.

This process is repetitive and can take significant time, especially with many test files. It's also easy to miss edge cases, validation rules, error scenarios, permission scenarios, boundary values, API failures, integration cases, and regression risks.

## 3. Project Goal

Build an agent that can: read a GitHub requirement, extract structured acceptance criteria, inspect relevant test files, match requirements to existing tests, generate a test plan, produce a coverage matrix, identify missing scenarios, save the analysis, and optionally publish missing coverage as a GitHub issue.

## 4. Target Users

Manual QA engineers, automation engineers, software developers, technical leads, product teams, small teams without dedicated QA.

## 5. Example User Scenario

User: "Analyze GitHub issue 42 and check whether the repository tests cover all acceptance criteria."

Agent: retrieves issue 42 via GitHub MCP, extracts requirements, searches repo for relevant tests, reads matching tests, compares each requirement to existing tests, generates a test plan, produces a coverage matrix marking each criterion Covered / Partially covered / Not covered / Unable to determine, suggests missing scenarios, saves the analysis, and optionally creates a GitHub issue with missing tests.

## 6. Main Agent Capabilities

### 6.1 Requirement Analysis
Extracts feature name, business objective, functional requirements, acceptance criteria, validation rules, user roles, expected/error behavior, dependencies, constraints. Flags missing info instead of inventing requirements.

### 6.2 Test Repository Analysis
Searches for unit, API, integration, UI, e2e (Playwright), pytest, Jest tests, and fixtures — only files relevant to the selected requirement.

### 6.3 Test Plan Generation
Generates scenarios across categories: positive, negative, validation, boundary-value, permission/role, API, UI, integration, error-handling, regression. Each test case includes ID, title, requirement tested, preconditions, steps, test data, expected result, type, priority, automation recommendation.

### 6.4 Coverage Analysis
Produces a coverage matrix (Requirement | Existing test | Coverage status | Missing scenarios), with explanation for each status.

### 6.5 Missing-Test Recommendations
For each gap: missing behavior, why it matters, suggested test type/priority, related acceptance criterion, risk if not added.

### 6.6 Report Storage
Stores analysis in DynamoDB (structured data) and S3 (Markdown/JSON report). Includes analysis ID, repo, issue number, requirements, coverage results, missing tests, execution status, date, user feedback.

### 6.7 Optional GitHub Action
User may approve creating a GitHub issue with missing tests — never automatic.

## 7. System Boundaries (v1 will NOT)

Auto-write full test code, auto-open PRs, modify app code, merge branches, approve releases, execute production changes, analyze every file in huge repos, support many SCM platforms, replace human QA approval.

## 8. Agent Architecture (proposed, LangGraph)

Workflow: Receive request → Validate repo/issue → Retrieve GitHub issue → Extract requirements → Search relevant test files → Read/classify tests → Match tests to requirements → Generate missing scenarios → Validate analysis → Save report → Return result.

Proposed nodes: Request Validator, Requirement Retriever (GitHub MCP), Requirement Parser, Test Search Planner, Test File Retriever, Coverage Analyzer, Test Plan Generator, Quality Validator, Report Saver, Response Formatter.

## 9. MCP Integration

**GitHub MCP**: get repo info, get issue, get issue comments, search repo files, read repo files, list PRs, create issue (read-only ops required; issue creation optional + user-confirmed).

**Custom Test Analysis MCP Server** — proposed tools:
- `find_test_files(repository, keywords)` → list of test file paths
- `read_test_file` → file content/sections
- `extract_test_metadata` → test name, framework, tested behavior, expected result, tags, referenced endpoint/component
- `save_coverage_report` → stores to S3/DynamoDB
- `get_previous_analysis` → returns prior report for issue/repo

## 10. HTTP API (proposed, FastAPI)

- `POST /api/analyses` — start analysis (repository, issue_number)
- `GET /api/analyses/{id}` — status
- `GET /api/analyses/{id}/report` — completed report
- `GET /api/analyses` — list previous analyses
- `POST /api/analyses/{id}/github-issue` — create missing-tests issue
- `GET /health/live`, `GET /health/ready`

## 11. Web UI (proposed, React)

Main page: enter repo + issue number + optional notes → "Analyze test coverage".
Results page: requirement summary, acceptance criteria, coverage %, coverage matrix, existing tests, missing scenarios, priorities, agent warnings, tool-call history, create-issue button, download-report button.
History page: past analyses with repo, issue, date, status, coverage result, report link.

## 12. AWS Infrastructure (proposed)

- **EC2** — self-managed K8s cluster (1 control-plane + 1-2 worker nodes)
- **S3** — coverage reports, exported files, archives
- **DynamoDB** — analysis metadata, structured coverage results, status, feedback
- **SQS** (optional) — decouple API request from agent execution for longer jobs
- **IAM** — scoped access to S3/DynamoDB/SQS/CloudWatch
- **CloudWatch** — AWS-level logs and infra metrics

## 13. Kubernetes Design (proposed)

Namespaces: `dev`, `prod`, `monitoring`. Each env: frontend, FastAPI agent, custom MCP server, optional worker deployments, services, ConfigMaps, secrets, ingress. Liveness/readiness probes, resource requests/limits, HPA, ConfigMaps (env name, log level, bucket name, table name, MCP address), Secrets (GitHub token, LLM API credentials, app secrets).

## 14. Terraform (proposed)

```
terraform/
├── modules/ (networking, ec2, iam, s3, dynamodb, sqs, monitoring)
├── environments/ (dev, prod)
└── variables.tf
```
Provisions VPC, subnets, IGW, route tables, security groups, EC2 instances, IAM roles, S3 buckets, DynamoDB tables, SQS queues, CloudWatch resources. K8s manifests via YAML/Helm/Terraform K8s provider.

## 15. CI/CD Pipeline (proposed, GitHub Actions)

**PR pipeline**: install deps → format/lint checks → unit tests → MCP integration tests → build images → scan images → publish test summary → block merge on failure.

**Dev deploy** (on merge): build/push images → deploy to `dev` → smoke tests → report.

**Prod deploy** (on approval/release): full tests → versioned images → deploy to `prod` → readiness checks → smoke tests → report.

## 16. Testing Strategy

- **Unit tests**: requirement extraction, criteria parsing, search-query generation, test-file classification, coverage calculation, missing-test generation, report formatting, error handling, retries, termination conditions. Mock LLM and external systems.
- **MCP tool tests**: valid/invalid input, missing repo/file, empty results, large files, storage failure, timeout, unauthorized access — per custom tool.
- **MCP integration tests**: real MCP transport — start local MCP server, provide sample requirement, call `find_test_files`, read files, generate coverage result, verify tool calls, confirm report gaps.
- **API tests**: create analysis, invalid repo format, missing issue number, status/report retrieval, GitHub/LLM/MCP failures, storage failures, health endpoints.
- **E2E test**: full flow from UI request through displayed coverage matrix and saved report.

## 17. Error Handling

Must handle: repo/issue not found, private repo without permission, GitHub rate limit, no acceptance criteria found, no related tests found, unsupported framework, MCP server unavailable/timeout, LLM timeout/invalid response, S3/DynamoDB failure, partial analysis.

Retry strategy: limited retries with exponential backoff.

Fallbacks: analyze issue body only if comments fail; continue with remaining files if one fails to read; still return analysis if report save fails (report the storage failure); use "Unable to determine" instead of guessing when coverage is unclear.

## 18. Agent System Prompt (example)

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

## 19. Observability

**Metrics**: total/successful/failed analyses, avg analysis duration, API latency, LLM latency/failures, MCP tool-call count/latency/timeouts, GitHub error count, files analyzed, requirements extracted, missing tests found, S3/DynamoDB save failures.

**Logs**: request ID, analysis ID, repo, issue number, workflow step, tool name/duration, retry count, error type, final status. Never log secrets/tokens.

**Alerts**: high API error rate, repeated LLM failures, MCP server unavailable, high MCP latency, GitHub API failure spike, queue backlog, pod restarts, high CPU/memory, readiness-probe failures.

**Dashboard** (Grafana): service health, request volume, success/error rate, analysis latency, LLM performance, MCP performance, K8s pod health, resource usage, recent failures.

## 20. Measurable Business Value

Metrics to track: time saved preparing test plans, % acceptance criteria analyzed, missing scenarios identified, % recommendations accepted, reduction in manual search time, average analysis duration, user rating.

Example goal: reduce initial requirement/coverage analysis from ~30-60 minutes manual work to under 5 minutes agent-assisted.

## 21. Recommended MVP

GitHub issue retrieval → requirement extraction → repo test-file search → test-file reading → coverage classification → test-plan generation → missing-test recommendations → FastAPI HTTP API → basic React UI → custom MCP server → DynamoDB/S3 storage → K8s deployment (dev/prod) → Terraform infra → GitHub Actions CI/CD → unit + MCP integration tests → Prometheus/Grafana monitoring.

## 22. Optional Features (post-MVP)

Create missing-tests GitHub issue, compare two analyses, export PDF reports, PR-level analysis, multi-framework support, test-code skeleton generation, user feedback, changed-requirement detection, specialized sub-agent, reusable project skill.

## 23. Suggested Repository Structure

```
testscope-ai/
├── docs/
│   ├── spec.md
│   ├── plan.md
│   └── test-plan.md
├── backend/
│   ├── app/ (api, agent, models, services, storage, main.py)
│   ├── tests/
│   └── Dockerfile
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

## 24. Live Demo Scenario

Open a GitHub issue with a small feature + acceptance criteria → show existing repo tests → open TestScope AI UI → enter repo/issue → start analysis → show GitHub MCP call → show custom MCP server searching/reading tests → display coverage matrix → show a covered criterion and a missing test → save report → optionally create GitHub issue → open Grafana with real metrics → open GitHub Actions pipeline.

## 25. Estimated Difficulty

Medium overall. The AI workflow itself is manageable (one focused business process); complexity comes mainly from the mandatory infra (MCP, K8s, AWS EC2, Terraform, CI/CD, testing, observability). Estimate: ~45-65 focused development hours.

## 26. Summary

TestScope AI connects to GitHub via MCP, retrieves requirements, inspects existing tests, produces a structured test plan, and identifies missing coverage — reducing repetitive QA analysis and helping teams find testing gaps earlier, while remaining scoped to one focused workflow: Requirement → Existing tests → Coverage analysis → Missing test recommendations.