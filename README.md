# TestScope AI

An AI agent that analyzes a GitHub issue's acceptance criteria against a repository's
existing pytest tests, producing a coverage matrix, a full test plan, and missing-scenario
recommendations — with an optional user-approved step to file a GitHub issue for the gaps.

See:
- `docs/2026-07-30-testscope-ai-design.md` — architecture and design spec
- `docs/2026-07-30-testscope-ai-plan.md` — task-by-task implementation plan

## Repository Structure

- `backend/api` — FastAPI HTTP service
- `backend/worker` — LangGraph agent, consumes SQS jobs
- `backend/shared` — common models, AWS clients, config (used by `api` and `worker`)
- `mcp-server` — custom `mcp-test-analysis` MCP server
- `frontend` — React UI
- `terraform` — AWS infrastructure
- `kubernetes` — k8s manifests (base/dev/prod/monitoring)

## Local Development

**Required setup step:** create and activate a repo-root virtualenv before installing anything.
The OS Python is externally managed (PEP 668) and refuses direct `pip install`:

```bash
python3 -m venv .venv
source .venv/bin/activate   # run this in every new shell before pip/python commands below
which python                # confirm it resolves inside .venv before installing
```

Each Python service is an independently installable package, installed into that same `.venv`:

```bash
cd backend/api && pip install -e ".[dev]" && python -m pytest
cd backend/worker && pip install -e ".[dev]" && python -m pytest
cd backend/shared && pip install -e ".[dev]" && python -m pytest
cd mcp-server && pip install -e ".[dev]" && python -m pytest
```

```bash
cd frontend && npm install && npm test
```
