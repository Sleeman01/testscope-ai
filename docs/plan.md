# TestScope AI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build TestScope AI — an agent that reads a GitHub issue, extracts acceptance criteria, matches them against existing pytest tests, produces a coverage matrix and test plan, and stores/publishes the result — deployed on a self-managed k3s cluster on EC2 with full Terraform/CI/CD/observability, per `docs/spec.md`.

**Architecture:** Two backend services (`api`, `worker`) split around an SQS queue; the `worker` runs a LangGraph agent that calls a custom `mcp-test-analysis` MCP server (this repo) and the official `mcp-github` MCP server; results persist to DynamoDB + S3; a React `frontend` talks only to `api`. Everything ships as 4 Docker images to a single k3s cluster (dev/prod/monitoring namespaces) on one EC2 host, provisioned by Terraform.

**Tech Stack:** Python 3.11, FastAPI, LangGraph, Anthropic Claude API (`anthropic` SDK), MCP Python SDK (`mcp`, `FastMCP`), boto3 + moto (tests), pytest, React 18 + TypeScript + Vite + Vitest, Terraform ≥1.5, k3s, GitHub Actions.

## Global Constraints

Copied verbatim from `docs/spec.md` — every task's requirements implicitly include these:

- **LLM:** Anthropic Claude API only. Model id is a single named constant (`ANTHROPIC_MODEL` env var, default `claude-sonnet-4-5-20250929`) in `backend/worker/app/config.py` — never hardcoded elsewhere.
- **Test framework scope:** v1 analyzes Python/pytest tests only.
- **Repo clone:** shallow (`--depth 1 --single-branch`), 30s subprocess timeout, reject repos >500MB before cloning (checked via GitHub MCP `get_repository`, size field is KB → convert to bytes).
- **File reads:** `read_test_file` truncates at 50KB (`truncated=true`).
- **File search cap:** `find_test_files` returns at most 30 ranked files.
- **Workspace:** `/workspace/{analysis_id}` per job; explicit `cleanup_workspace` call in worker's `finally`; backstop sweeper deletes dirs older than 1 hour every 15 minutes.
- **Retries:** transient errors get 3 attempts, backoff 1s/2s/4s. Validation/not-found/access-denied errors fail fast, no retry.
- **Overall timeout:** entire LangGraph run wrapped in a 10-minute (600s) wall-clock timeout.
- **Idempotency:** Job Intake and Report Saver are upserts keyed by `analysis_id` — last-write-wins, no dedup logic needed.
- **No auth, no de-dup check on `POST /api/analyses`** — both are stated v1 decisions, not gaps to fill in.
- **Secrets isolation:** GitHub token only in `mcp-github`/`mcp-test-analysis` K8s Secrets; Anthropic API key only in `worker`'s Secret. Never logged.
- **DynamoDB:** table `testscope-analyses-{env}`, PK `analysis_id`; GSI1 (PK `repository#issue_number`, SK `created_at`); GSI2 (PK constant `"ANALYSIS"`, SK `created_at`).
- **S3:** bucket `testscope-reports-{env}`, key pattern `{repository}/{issue_number}/{analysis_id}.md` and `.json`.
- **SQS:** queue `testscope-jobs-{env}` + DLQ, redrive after 3 receives.
- **AWS mocking in tests:** `moto` for S3/DynamoDB/SQS — never hit real AWS from unit or MCP-integration tests.
- **LLM mocking in tests:** a stub Anthropic client returning canned JSON — never call the real Claude API from automated tests (cost/determinism/CI speed).
- **MCP integration tests:** real MCP transport against a local fixture repo (small bare git repo under `mcp-server/tests/fixtures/`, cloned from a local path — no network).
- **K8s:** single EC2 host, k3s, namespaces `dev`/`prod`/`monitoring`. Images built: `api`, `worker`, `mcp-test-analysis`, `frontend` (4 images, pushed to GHCR).
- **Coverage target:** ≥80% unit test coverage on core agent/MCP logic (tracked in the PR pipeline).

---

## Build Order

1. **Phase 0** — repo scaffolding
2. **Phase 1** — custom MCP server (`mcp-test-analysis`) — no AWS/LLM coupling beyond boto3, testable first
3. **Phase 2** — `backend/shared` (config, AWS clients, `AnalysisRecord` model)
4. **Phase 3** — `backend/worker` (LangGraph agent)
5. **Phase 4** — `backend/api` (FastAPI)
6. **Phase 5** — `frontend` (React)
7. **Phase 6** — Terraform
8. **Phase 7** — Kubernetes manifests
9. **Phase 8** — CI/CD
10. **Phase 9** — Observability
11. **Phase 10** — local full-stack integration

Each phase's tasks are ordered so every task lands with its own passing tests before the next depends on it.

---

## Phase 0 — Repo Scaffolding

### Task 1: Monorepo skeleton and per-service tooling

**Files:**
- Create: `backend/api/pyproject.toml`, `backend/worker/pyproject.toml`, `backend/shared/pyproject.toml`, `mcp-server/pyproject.toml`
- Create: `backend/api/app/__init__.py`, `backend/worker/app/__init__.py`, `backend/shared/__init__.py`, `mcp-server/__init__.py`
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`
- Create: `docker-compose.yml` (stub, services added incrementally in later phases)
- Create: `.gitignore`, `README.md`
- Create: `backend/api/tests/test_smoke.py`, `backend/worker/tests/test_smoke.py`, `backend/shared/tests/test_smoke.py`, `mcp-server/tests/test_smoke.py`, `frontend/src/smoke.test.ts`

**Interfaces:**
- Produces: importable empty packages `testscope_api`, `testscope_worker`, `testscope_shared`, `testscope_mcp` (via each `pyproject.toml`'s `[project]` name + `src`-less flat layout under `app`/root), and a Vite+Vitest-configured `frontend/`.

- [ ] **Step 1: Write failing smoke tests for each Python package**

```python
# backend/api/tests/test_smoke.py (same pattern in worker/shared/mcp-server, adjust import)
def test_package_importable():
    import app  # noqa: F401
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/api && python -m pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'` (no `pyproject.toml`/package yet)

- [ ] **Step 3: Create each `pyproject.toml`**

```toml
# backend/api/pyproject.toml
[project]
name = "testscope-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["fastapi>=0.115", "uvicorn[standard]>=0.32", "pydantic>=2.9", "boto3>=1.35"]

[project.optional-dependencies]
dev = ["pytest>=8.3", "pytest-asyncio>=0.24", "pytest-cov>=5.0", "moto[s3,dynamodb,sqs]>=5.0", "httpx>=0.27", "ruff>=0.7"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["app*"]
```

Repeat with names `testscope-worker` (deps: add `langgraph>=0.2`, `anthropic>=0.39`, `mcp>=1.1`), `testscope-shared` (deps: `boto3`, `pydantic`), `testscope-mcp` (deps: `mcp>=1.1`, `boto3`, `GitPython>=3.1`). Each gets its own `app/__init__.py` (or root `__init__.py` for `shared`/`mcp-server`) with `# TestScope AI service package`.

- [ ] **Step 4: Install each package in editable mode and re-run**

Run: `cd backend/api && pip install -e ".[dev]" && python -m pytest tests/test_smoke.py -v` (repeat per service)
Expected: PASS for all four Python packages

- [ ] **Step 5: Scaffold frontend with Vite + Vitest**

```json
// frontend/package.json
{
  "name": "testscope-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run"
  },
  "dependencies": { "react": "^18.3.1", "react-dom": "^18.3.1", "react-router-dom": "^6.27.0" },
  "devDependencies": {
    "@testing-library/react": "^16.0.1", "@testing-library/jest-dom": "^6.6.2",
    "@vitejs/plugin-react": "^4.3.3", "typescript": "^5.6.3", "vite": "^5.4.10",
    "vitest": "^2.1.4", "jsdom": "^25.0.1"
  }
}
```

```ts
// frontend/src/smoke.test.ts
import { describe, it, expect } from "vitest";
describe("smoke", () => { it("runs", () => { expect(1 + 1).toBe(2); }); });
```

Run: `cd frontend && npm install && npm test`
Expected: PASS

- [ ] **Step 6: Write root `.gitignore` and stub `docker-compose.yml`**

```yaml
# docker-compose.yml — services added in Phase 10; placeholder keeps `docker compose config` valid now
services: {}
```

- [ ] **Step 7: Commit**

```bash
git add backend frontend mcp-server docker-compose.yml .gitignore README.md
git commit -m "chore: scaffold monorepo packages for api, worker, shared, mcp-server, frontend"
```

---

## Phase 1 — Custom MCP Server (`mcp-test-analysis`)

### Task 2: `extract_test_metadata` tool (deterministic, no LLM)

**Files:**
- Create: `mcp-server/tools/extract_test_metadata.py`
- Test: `mcp-server/tests/test_extract_test_metadata.py`
- Test fixture: `mcp-server/tests/fixtures/sample_test_file.py`

**Interfaces:**
- Produces: `extract_test_metadata(file_content: str) -> dict` returning `{"tests": [{"name": str, "framework": str, "decorators": list[str], "docstring": str | None, "fixtures_used": list[str], "assert_count": int, "string_literals": list[str], "line_range": [int, int]}]}`. Takes raw file content (not a path) so it's pure/unit-testable without touching disk; the MCP tool wrapper (Task 8) reads the file via `WorkspaceManager` and passes content in.

- [ ] **Step 1: Write the failing test**

```python
# mcp-server/tests/test_extract_test_metadata.py
from pathlib import Path
from tools.extract_test_metadata import extract_test_metadata

FIXTURE = Path(__file__).parent / "fixtures" / "sample_test_file.py"

def test_extracts_pytest_function_with_fixture_and_markers():
    content = FIXTURE.read_text()
    result = extract_test_metadata(content)
    names = [t["name"] for t in result["tests"]]
    assert "test_login_rejects_invalid_password" in names
    entry = next(t for t in result["tests"] if t["name"] == "test_login_rejects_invalid_password")
    assert entry["framework"] == "pytest"
    assert "client" in entry["fixtures_used"]
    assert "pytest.mark.parametrize" in entry["decorators"]
    assert entry["assert_count"] >= 1
    assert "/api/login" in entry["string_literals"]

def test_ignores_non_test_functions():
    content = "def helper():\n    return 1\n"
    result = extract_test_metadata(content)
    assert result["tests"] == []
```

```python
# mcp-server/tests/fixtures/sample_test_file.py
import pytest

@pytest.mark.parametrize("password", ["wrong", ""])
def test_login_rejects_invalid_password(client, password):
    """Login must reject invalid passwords with 401."""
    response = client.post("/api/login", json={"password": password})
    assert response.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp-server && python -m pytest tests/test_extract_test_metadata.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.extract_test_metadata'`

- [ ] **Step 3: Implement using `ast`**

```python
# mcp-server/tools/extract_test_metadata.py
import ast

def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute):
        parts = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    if isinstance(node, ast.Name):
        return node.id
    return ast.dump(node)

def _string_literals(node: ast.AST) -> list[str]:
    out = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str) and child.value.strip():
            out.append(child.value)
    return out

def extract_test_metadata(file_content: str) -> dict:
    tree = ast.parse(file_content)
    tests = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue
        decorators = [_decorator_name(d) for d in node.decorator_list]
        fixtures_used = [
            arg.arg for arg in node.args.args
            if arg.arg not in ("self",) and not arg.arg.startswith("_")
        ]
        assert_count = sum(1 for child in ast.walk(node) if isinstance(child, ast.Assert))
        docstring = ast.get_docstring(node)
        tests.append({
            "name": node.name,
            "framework": "pytest",
            "decorators": decorators,
            "docstring": docstring,
            "fixtures_used": fixtures_used,
            "assert_count": assert_count,
            "string_literals": _string_literals(node),
            "line_range": [node.lineno, node.end_lineno or node.lineno],
        })
    return {"tests": tests}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp-server && python -m pytest tests/test_extract_test_metadata.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/extract_test_metadata.py mcp-server/tests/test_extract_test_metadata.py mcp-server/tests/fixtures/sample_test_file.py
git commit -m "feat(mcp-server): add deterministic extract_test_metadata tool"
```

### Task 3: `WorkspaceManager` (shallow clone, size guard) + `find_test_files` tool

**Files:**
- Create: `mcp-server/workspace.py`
- Create: `mcp-server/github_client.py`
- Create: `mcp-server/tools/find_test_files.py`
- Test: `mcp-server/tests/test_workspace.py`
- Test: `mcp-server/tests/test_find_test_files.py`
- Test fixture: `mcp-server/tests/fixtures/make_bare_repo.py` (helper that builds a local bare git repo with a couple of test files, used here and in Task 8)

**Interfaces:**
- Consumes: none from earlier tasks (Task 2's `extract_test_metadata` is independent).
- Produces: `class WorkspaceManager` with `get_or_clone(analysis_id: str, clone_url: str, ref: str, root: Path) -> Path` (raises `WorkspaceError(code: str, message: str)` on failure, `code` ∈ `{"CLONE_TIMEOUT", "CLONE_FAILED"}`), `cleanup(analysis_id: str, root: Path) -> bool`, `sweep_stale(root: Path, max_age_seconds: int) -> int` — `cleanup`/`sweep_stale` are consumed by Task 5. `get_repo_size_bytes(mcp_client, owner: str, repo: str) -> int` in `github_client.py`, raising `WorkspaceError("REPO_TOO_LARGE", ...)` when over the 500MB threshold — called by `find_test_files` before cloning.

- [ ] **Step 1: Write failing tests for `WorkspaceManager` against a local bare repo (no network)**

```python
# mcp-server/tests/fixtures/make_bare_repo.py
import subprocess
from pathlib import Path

def make_bare_repo(tmp_path: Path) -> str:
    """Creates a local bare git repo with one test file, returns its file:// clone URL."""
    work = tmp_path / "work"
    work.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=work, check=True)
    (work / "tests").mkdir()
    (work / "tests" / "test_login.py").write_text(
        "def test_login_rejects_invalid_password():\n    assert True\n"
    )
    subprocess.run(["git", "add", "."], cwd=work, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=work, check=True)
    bare = tmp_path / "bare.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(work), str(bare)], check=True)
    return f"file://{bare}"
```

```python
# mcp-server/tests/test_workspace.py
from pathlib import Path
from workspace import WorkspaceManager, WorkspaceError
from tests.fixtures.make_bare_repo import make_bare_repo

def test_get_or_clone_creates_workspace_and_reuses_it(tmp_path):
    clone_url = make_bare_repo(tmp_path)
    root = tmp_path / "workspace_root"
    mgr = WorkspaceManager()
    path1 = mgr.get_or_clone("analysis-1", clone_url, "main", root)
    assert (path1 / "tests" / "test_login.py").exists()
    path2 = mgr.get_or_clone("analysis-1", clone_url, "main", root)
    assert path1 == path2  # reused, not re-cloned

def test_get_or_clone_raises_on_bad_url(tmp_path):
    root = tmp_path / "workspace_root"
    mgr = WorkspaceManager()
    with pytest.raises(WorkspaceError) as exc:
        mgr.get_or_clone("analysis-2", "file:///no/such/repo.git", "main", root)
    assert exc.value.code == "CLONE_FAILED"
    assert not (root / "analysis-2").exists()  # partial dir removed on failure
```

Add `import pytest` to the top of that test file.

- [ ] **Step 2: Run to verify failure**

Run: `cd mcp-server && python -m pytest tests/test_workspace.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'workspace'`

- [ ] **Step 3: Implement `WorkspaceManager`**

```python
# mcp-server/workspace.py
import shutil
import subprocess
import time
from pathlib import Path

class WorkspaceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

class WorkspaceManager:
    def get_or_clone(self, analysis_id: str, clone_url: str, ref: str, root: Path) -> Path:
        target = root / analysis_id
        if target.exists():
            return target
        root.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--single-branch", "--branch", ref, clone_url, str(target)],
                check=True, capture_output=True, text=True, timeout=30,
            )
        except subprocess.TimeoutExpired:
            shutil.rmtree(target, ignore_errors=True)
            raise WorkspaceError("CLONE_TIMEOUT", f"Clone of {clone_url} exceeded 30s")
        except subprocess.CalledProcessError as e:
            shutil.rmtree(target, ignore_errors=True)
            stderr = (e.stderr or "")[:500]
            raise WorkspaceError("CLONE_FAILED", f"git clone failed: {stderr}")
        return target

    def cleanup(self, analysis_id: str, root: Path) -> bool:
        target = root / analysis_id
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            return True
        return False

    def sweep_stale(self, root: Path, max_age_seconds: int) -> int:
        if not root.exists():
            return 0
        now = time.time()
        removed = 0
        for entry in root.iterdir():
            if entry.is_dir() and (now - entry.stat().st_mtime) > max_age_seconds:
                shutil.rmtree(entry, ignore_errors=True)
                removed += 1
        return removed
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp-server && python -m pytest tests/test_workspace.py -v`
Expected: PASS

- [ ] **Step 5: Write failing test for `find_test_files` (mocks the GitHub size-check MCP call)**

```python
# mcp-server/tests/test_find_test_files.py
from unittest.mock import AsyncMock
from pathlib import Path
import pytest
from tools.find_test_files import find_test_files
from tests.fixtures.make_bare_repo import make_bare_repo

@pytest.mark.asyncio
async def test_finds_files_matching_keywords(tmp_path, monkeypatch):
    clone_url = make_bare_repo(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path / "workspace_root"))
    fake_mcp_client = AsyncMock()
    fake_mcp_client.get_repo_size_bytes = AsyncMock(return_value=1024)
    result = await find_test_files(
        analysis_id="a1", clone_url=clone_url, ref="main",
        keywords=["login"], github_client=fake_mcp_client,
    )
    paths = [f["path"] for f in result["files"]]
    assert any("test_login.py" in p for p in paths)

@pytest.mark.asyncio
async def test_rejects_oversized_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path / "workspace_root"))
    fake_mcp_client = AsyncMock()
    fake_mcp_client.get_repo_size_bytes = AsyncMock(return_value=600 * 1024 * 1024)
    from workspace import WorkspaceError
    with pytest.raises(WorkspaceError) as exc:
        await find_test_files(
            analysis_id="a2", clone_url="file:///irrelevant", ref="main",
            keywords=["login"], github_client=fake_mcp_client,
        )
    assert exc.value.code == "REPO_TOO_LARGE"
```

- [ ] **Step 6: Run to verify failure, then implement**

Run: `cd mcp-server && python -m pytest tests/test_find_test_files.py -v` → FAIL (`ModuleNotFoundError`)

```python
# mcp-server/tools/find_test_files.py
import os
from pathlib import Path
from workspace import WorkspaceManager, WorkspaceError

MAX_REPO_BYTES = 500 * 1024 * 1024
MAX_FILES = 30
_manager = WorkspaceManager()

async def find_test_files(analysis_id: str, clone_url: str, ref: str, keywords: list[str], github_client, owner: str = "", repo: str = "") -> dict:
    size_bytes = await github_client.get_repo_size_bytes(owner, repo)
    if size_bytes > MAX_REPO_BYTES:
        raise WorkspaceError("REPO_TOO_LARGE", f"Repo is {size_bytes} bytes, exceeds {MAX_REPO_BYTES}")

    root = Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
    workspace = _manager.get_or_clone(analysis_id, clone_url, ref, root)

    candidates = [
        p for p in workspace.rglob("test_*.py")
    ] + [p for p in workspace.rglob("*_test.py")]
    scored = []
    for path in set(candidates):
        text = path.read_text(errors="ignore").lower()
        matched = [kw for kw in keywords if kw.lower() in text or kw.lower() in path.name.lower()]
        if matched or not keywords:
            scored.append({
                "path": str(path.relative_to(workspace)),
                "size_bytes": path.stat().st_size,
                "matched_keywords": matched,
            })
    scored.sort(key=lambda f: len(f["matched_keywords"]), reverse=True)
    return {"files": scored[:MAX_FILES]}
```

`github_client.get_repo_size_bytes` (real implementation, calling `mcp-github`'s `get_repository` tool over MCP) is built in Task 8 alongside server wiring; this task only needs it as an injected duck-typed dependency, proven here with a mock.

- [ ] **Step 7: Run test to verify it passes**

Run: `cd mcp-server && python -m pytest tests/test_find_test_files.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add mcp-server/workspace.py mcp-server/tools/find_test_files.py mcp-server/tests/test_workspace.py mcp-server/tests/test_find_test_files.py mcp-server/tests/fixtures/make_bare_repo.py
git commit -m "feat(mcp-server): add WorkspaceManager and find_test_files tool"
```

### Task 4: `read_test_file` tool

**Files:**
- Create: `mcp-server/tools/read_test_file.py`
- Test: `mcp-server/tests/test_read_test_file.py`

**Interfaces:**
- Consumes: `WorkspaceManager` workspace layout from Task 3 (`WORKSPACE_ROOT/{analysis_id}/{path}`).
- Produces: `read_test_file(analysis_id: str, path: str, root: Path | None = None) -> dict` → `{"content": str, "truncated": bool}`.

- [ ] **Step 1: Write the failing test**

```python
# mcp-server/tests/test_read_test_file.py
from pathlib import Path
from tools.read_test_file import read_test_file

def test_reads_full_small_file(tmp_path):
    root = tmp_path / "workspace_root"
    (root / "a1").mkdir(parents=True)
    (root / "a1" / "test_x.py").write_text("def test_x():\n    assert True\n")
    result = read_test_file("a1", "test_x.py", root=root)
    assert "def test_x" in result["content"]
    assert result["truncated"] is False

def test_truncates_large_file(tmp_path):
    root = tmp_path / "workspace_root"
    (root / "a1").mkdir(parents=True)
    big = "x = 1\n" * 20000  # well over 50KB
    (root / "a1" / "test_big.py").write_text(big)
    result = read_test_file("a1", "test_big.py", root=root)
    assert result["truncated"] is True
    assert len(result["content"].encode()) <= 50 * 1024
```

- [ ] **Step 2: Run to verify failure**

Run: `cd mcp-server && python -m pytest tests/test_read_test_file.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# mcp-server/tools/read_test_file.py
import os
from pathlib import Path

MAX_BYTES = 50 * 1024

def read_test_file(analysis_id: str, path: str, root: Path | None = None) -> dict:
    root = root or Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
    full_path = (root / analysis_id / path).resolve()
    workspace_root = (root / analysis_id).resolve()
    if workspace_root not in full_path.parents and full_path != workspace_root:
        raise ValueError(f"Path {path} escapes workspace for {analysis_id}")
    raw = full_path.read_bytes()
    truncated = len(raw) > MAX_BYTES
    content = raw[:MAX_BYTES].decode(errors="ignore") if truncated else raw.decode(errors="ignore")
    return {"content": content, "truncated": truncated}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp-server && python -m pytest tests/test_read_test_file.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/read_test_file.py mcp-server/tests/test_read_test_file.py
git commit -m "feat(mcp-server): add read_test_file tool with 50KB truncation"
```

### Task 5: `cleanup_workspace` tool + background sweeper

**Files:**
- Create: `mcp-server/tools/cleanup_workspace.py`
- Create: `mcp-server/sweeper.py`
- Test: `mcp-server/tests/test_cleanup_workspace.py`
- Test: `mcp-server/tests/test_sweeper.py`

**Interfaces:**
- Consumes: `WorkspaceManager.cleanup` / `.sweep_stale` from Task 3.
- Produces: `cleanup_workspace(analysis_id: str, root: Path | None = None) -> dict` → `{"deleted": bool}`; `start_sweeper(root: Path, interval_seconds: int = 900, max_age_seconds: int = 3600) -> threading.Thread` (daemon thread, consumed by Task 8's server startup).

- [ ] **Step 1: Write failing tests**

```python
# mcp-server/tests/test_cleanup_workspace.py
from pathlib import Path
from tools.cleanup_workspace import cleanup_workspace

def test_deletes_existing_workspace(tmp_path):
    root = tmp_path / "workspace_root"
    (root / "a1").mkdir(parents=True)
    result = cleanup_workspace("a1", root=root)
    assert result == {"deleted": True}
    assert not (root / "a1").exists()

def test_reports_false_when_nothing_to_delete(tmp_path):
    root = tmp_path / "workspace_root"
    result = cleanup_workspace("does-not-exist", root=root)
    assert result == {"deleted": False}
```

```python
# mcp-server/tests/test_sweeper.py
import time
from pathlib import Path
from sweeper import start_sweeper

def test_sweeper_removes_stale_dirs(tmp_path):
    root = tmp_path / "workspace_root"
    stale = root / "old-analysis"
    stale.mkdir(parents=True)
    old_time = time.time() - 7200
    import os
    os.utime(stale, (old_time, old_time))

    thread = start_sweeper(root, interval_seconds=0.1, max_age_seconds=3600)
    time.sleep(0.3)
    assert not stale.exists()
    thread_stop_event_cleanup(thread)  # see implementation note in Step 3

def thread_stop_event_cleanup(thread):
    # start_sweeper returns a daemon thread; test process exit reaps it.
    # No explicit stop needed for this unit test's lifetime.
    pass
```

- [ ] **Step 2: Run to verify failure**

Run: `cd mcp-server && python -m pytest tests/test_cleanup_workspace.py tests/test_sweeper.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# mcp-server/tools/cleanup_workspace.py
import os
from pathlib import Path
from workspace import WorkspaceManager

_manager = WorkspaceManager()

def cleanup_workspace(analysis_id: str, root: Path | None = None) -> dict:
    root = root or Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
    deleted = _manager.cleanup(analysis_id, root)
    return {"deleted": deleted}
```

```python
# mcp-server/sweeper.py
import threading
from pathlib import Path
from workspace import WorkspaceManager

_manager = WorkspaceManager()

def start_sweeper(root: Path, interval_seconds: int = 900, max_age_seconds: int = 3600) -> threading.Thread:
    def _loop():
        while True:
            _manager.sweep_stale(root, max_age_seconds)
            threading.Event().wait(interval_seconds)

    thread = threading.Thread(target=_loop, daemon=True, name="workspace-sweeper")
    thread.start()
    return thread
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp-server && python -m pytest tests/test_cleanup_workspace.py tests/test_sweeper.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/cleanup_workspace.py mcp-server/sweeper.py mcp-server/tests/test_cleanup_workspace.py mcp-server/tests/test_sweeper.py
git commit -m "feat(mcp-server): add cleanup_workspace tool and stale-workspace sweeper"
```

### Task 6: `save_coverage_report` tool

**Files:**
- Create: `mcp-server/aws.py`
- Create: `mcp-server/tools/save_coverage_report.py`
- Test: `mcp-server/tests/test_save_coverage_report.py`

**Interfaces:**
- Produces: `get_dynamodb_table()`, `get_s3_client()`, `get_s3_bucket_name() -> str`, `get_table_name() -> str` in `aws.py` (env-driven: `DYNAMODB_TABLE`, `S3_BUCKET`, both required). `save_coverage_report(analysis_id, repository, issue_number, requirement, coverage_matrix, missing_tests, test_plan, status, tool_call_trace) -> dict` → `{"s3_report_key": str, "dynamodb_status": str}`. This defines the exact DynamoDB item shape and S3 key pattern that `backend/shared`'s `AnalysisRecord` (Task 9) and `AnalysisStore` (Task 9) independently agree on — both sides are tested against the same fixture JSON (`mcp-server/tests/fixtures/sample_analysis_record.json`, duplicated at `backend/shared/tests/fixtures/sample_analysis_record.json` in Task 9) so the two independently-deployed services stay in sync without a shared code dependency.

- [ ] **Step 1: Write the failing test using moto**

```python
# mcp-server/tests/test_save_coverage_report.py
import json
import os
import boto3
import pytest
from moto import mock_aws

@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DYNAMODB_TABLE", "testscope-analyses-test")
    monkeypatch.setenv("S3_BUCKET", "testscope-reports-test")
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="testscope-analyses-test",
            KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "analysis_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="testscope-reports-test")
        yield

def test_writes_dynamodb_item_and_s3_report(aws_env):
    from tools.save_coverage_report import save_coverage_report
    result = save_coverage_report(
        analysis_id="a1", repository="acme/widgets", issue_number=42,
        requirement={"feature_name": "Login"}, coverage_matrix=[{"criterion_id": "AC1", "status": "Covered"}],
        missing_tests=[], test_plan=[], status="completed", tool_call_trace=[],
    )
    assert result["s3_report_key"] == "acme/widgets/42/a1.json"
    assert result["dynamodb_status"] == "saved"

    import boto3
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    item = ddb.Table("testscope-analyses-test").get_item(Key={"analysis_id": "a1"})["Item"]
    assert item["status"] == "completed"
    assert item["repository"] == "acme/widgets"

    s3 = boto3.client("s3", region_name="us-east-1")
    body = s3.get_object(Bucket="testscope-reports-test", Key="acme/widgets/42/a1.json")["Body"].read()
    assert json.loads(body)["status"] == "completed"
    md = s3.get_object(Bucket="testscope-reports-test", Key="acme/widgets/42/a1.md")["Body"].read().decode()
    assert "Login" in md
```

- [ ] **Step 2: Run to verify failure**

Run: `cd mcp-server && python -m pytest tests/test_save_coverage_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'aws'`

- [ ] **Step 3: Implement `aws.py` and the tool**

```python
# mcp-server/aws.py
import os
import boto3

def get_dynamodb_table():
    return boto3.resource("dynamodb").Table(get_table_name())

def get_s3_client():
    return boto3.client("s3")

def get_table_name() -> str:
    return os.environ["DYNAMODB_TABLE"]

def get_s3_bucket_name() -> str:
    return os.environ["S3_BUCKET"]
```

```python
# mcp-server/tools/save_coverage_report.py
import json
from datetime import datetime, timezone
from aws import get_dynamodb_table, get_s3_client, get_s3_bucket_name

def _render_markdown(repository, issue_number, requirement, coverage_matrix, missing_tests, test_plan) -> str:
    lines = [f"# Coverage Report — {repository}#{issue_number}", "", f"## {requirement.get('feature_name', 'Untitled')}", ""]
    lines.append("## Coverage Matrix")
    for row in coverage_matrix:
        lines.append(f"- **{row['criterion_id']}**: {row['status']}")
    lines.append("")
    lines.append(f"## Missing Tests ({len(missing_tests)})")
    for m in missing_tests:
        lines.append(f"- {m.get('behavior', '')}")
    return "\n".join(lines)

def save_coverage_report(analysis_id, repository, issue_number, requirement, coverage_matrix,
                          missing_tests, test_plan, status, tool_call_trace) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    s3_key = f"{repository}/{issue_number}/{analysis_id}"
    payload = {
        "analysis_id": analysis_id, "repository": repository, "issue_number": issue_number,
        "requirement": requirement, "coverage_matrix": coverage_matrix,
        "missing_tests": missing_tests, "test_plan": test_plan, "status": status,
        "tool_call_trace": tool_call_trace, "created_at": now,
    }
    s3 = get_s3_client()
    bucket = get_s3_bucket_name()
    s3.put_object(Bucket=bucket, Key=f"{s3_key}.json", Body=json.dumps(payload).encode(), ContentType="application/json")
    md = _render_markdown(repository, issue_number, requirement, coverage_matrix, missing_tests, test_plan)
    s3.put_object(Bucket=bucket, Key=f"{s3_key}.md", Body=md.encode(), ContentType="text/markdown")

    covered = sum(1 for r in coverage_matrix if r["status"] == "Covered")
    total = len(coverage_matrix) or 1
    table = get_dynamodb_table()
    table.put_item(Item={
        "analysis_id": analysis_id, "repository": repository, "issue_number": issue_number,
        "repository_issue": f"{repository}#{issue_number}", "gsi2_pk": "ANALYSIS",
        "status": status, "created_at": now, "updated_at": now,
        "requirement_summary": requirement.get("feature_name", ""),
        "coverage_summary": {"percent_covered": round(100 * covered / total, 1)},
        "missing_tests_count": len(missing_tests),
        "s3_report_key": f"{s3_key}.json", "tool_call_trace": tool_call_trace,
    })
    return {"s3_report_key": f"{s3_key}.json", "dynamodb_status": "saved"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp-server && python -m pytest tests/test_save_coverage_report.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mcp-server/aws.py mcp-server/tools/save_coverage_report.py mcp-server/tests/test_save_coverage_report.py
git commit -m "feat(mcp-server): add save_coverage_report tool (DynamoDB + S3)"
```

### Task 7: `get_previous_analysis` tool

**Files:**
- Create: `mcp-server/tools/get_previous_analysis.py`
- Test: `mcp-server/tests/test_get_previous_analysis.py`

**Interfaces:**
- Consumes: `aws.get_dynamodb_table()` from Task 6. Assumes GSI1 (`repository_issue-index`, PK `repository_issue`, SK `created_at`) exists on the table — created in Terraform Task 28 and in each test's moto `create_table` call.
- Produces: `get_previous_analysis(repository: str, issue_number: int) -> dict` → `{"analyses": [{analysis_id, created_at, status, coverage_summary, s3_report_key}]}`, newest first.

- [ ] **Step 1: Write the failing test**

```python
# mcp-server/tests/test_get_previous_analysis.py
import boto3
import pytest
from moto import mock_aws

@pytest.fixture
def table_with_gsi(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DYNAMODB_TABLE", "testscope-analyses-test")
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="testscope-analyses-test",
            KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "analysis_id", "AttributeType": "S"},
                {"AttributeName": "repository_issue", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[{
                "IndexName": "repository_issue-index",
                "KeySchema": [
                    {"AttributeName": "repository_issue", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }],
        )
        table = boto3.resource("dynamodb", region_name="us-east-1").Table("testscope-analyses-test")
        table.put_item(Item={"analysis_id": "a1", "repository_issue": "acme/widgets#42", "created_at": "2026-01-01T00:00:00Z", "status": "completed", "coverage_summary": {"percent_covered": 80.0}, "s3_report_key": "acme/widgets/42/a1.json"})
        table.put_item(Item={"analysis_id": "a2", "repository_issue": "acme/widgets#42", "created_at": "2026-01-02T00:00:00Z", "status": "completed", "coverage_summary": {"percent_covered": 90.0}, "s3_report_key": "acme/widgets/42/a2.json"})
        yield

def test_returns_analyses_newest_first(table_with_gsi):
    from tools.get_previous_analysis import get_previous_analysis
    result = get_previous_analysis("acme/widgets", 42)
    ids = [a["analysis_id"] for a in result["analyses"]]
    assert ids == ["a2", "a1"]
```

- [ ] **Step 2: Run to verify failure**

Run: `cd mcp-server && python -m pytest tests/test_get_previous_analysis.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# mcp-server/tools/get_previous_analysis.py
from boto3.dynamodb.conditions import Key
from aws import get_dynamodb_table

def get_previous_analysis(repository: str, issue_number: int) -> dict:
    table = get_dynamodb_table()
    response = table.query(
        IndexName="repository_issue-index",
        KeyConditionExpression=Key("repository_issue").eq(f"{repository}#{issue_number}"),
        ScanIndexForward=False,
    )
    analyses = [{
        "analysis_id": item["analysis_id"], "created_at": item["created_at"],
        "status": item["status"], "coverage_summary": item.get("coverage_summary"),
        "s3_report_key": item.get("s3_report_key"),
    } for item in response["Items"]]
    return {"analyses": analyses}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp-server && python -m pytest tests/test_get_previous_analysis.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/get_previous_analysis.py mcp-server/tests/test_get_previous_analysis.py
git commit -m "feat(mcp-server): add get_previous_analysis tool"
```

### Task 8: Server wiring (`FastMCP`) + real GitHub size-check client + MCP integration test

**Files:**
- Modify: `mcp-server/github_client.py` (created in Task 3 as an interface stub; fill in the real implementation here)
- Create: `mcp-server/server.py`
- Test: `mcp-server/tests/test_mcp_integration.py`

**Interfaces:**
- Consumes: all six tool functions from Tasks 2–7; `WorkspaceManager`/`start_sweeper` from Tasks 3/5.
- Produces: `server.py` exposes an MCP server over streamable-HTTP (env `MCP_HOST`, `MCP_PORT`, default `0.0.0.0:8100`) registering `find_test_files`, `read_test_file`, `extract_test_metadata`, `save_coverage_report`, `get_previous_analysis`, `cleanup_workspace` as `@mcp.tool()`-decorated tools with MCP-visible names matching spec §5.1 exactly — this is the contract the worker's MCP client (Task 11) calls by name.

- [ ] **Step 1: Implement `github_client.py`'s real `get_repo_size_bytes`**

```python
# mcp-server/github_client.py
import os
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

class GithubClient:
    """Thin MCP client this server uses to call the separately-deployed mcp-github server.

    NOTE: verify `get_repository` is the exact tool name exposed by the installed
    github-mcp-server version (`mcp list-tools` against MCP_GITHUB_URL) and update
    the constant below if it differs — spec §5.2 assumes this name.
    """
    TOOL_NAME = "get_repository"

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.environ["MCP_GITHUB_URL"]

    async def get_repo_size_bytes(self, owner: str, repo: str) -> int:
        async with streamablehttp_client(self.base_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(self.TOOL_NAME, {"owner": owner, "repo": repo})
                size_kb = result.structuredContent["size"]
                return size_kb * 1024
```

- [ ] **Step 2: Implement `server.py` registering all six tools**

```python
# mcp-server/server.py
import asyncio
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from tools.find_test_files import find_test_files as _find_test_files
from tools.read_test_file import read_test_file as _read_test_file
from tools.extract_test_metadata import extract_test_metadata as _extract_test_metadata
from tools.save_coverage_report import save_coverage_report as _save_coverage_report
from tools.get_previous_analysis import get_previous_analysis as _get_previous_analysis
from tools.cleanup_workspace import cleanup_workspace as _cleanup_workspace
from github_client import GithubClient
from sweeper import start_sweeper

mcp = FastMCP("testscope-test-analysis")
_github_client = GithubClient()
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))

@mcp.tool()
async def find_test_files(analysis_id: str, repository: str, ref: str, keywords: list[str]) -> dict:
    owner, repo = repository.split("/", 1)
    clone_url = f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/{repository}.git"
    return await _find_test_files(analysis_id, clone_url, ref, keywords, _github_client, owner, repo)

@mcp.tool()
def read_test_file(analysis_id: str, path: str) -> dict:
    return _read_test_file(analysis_id, path, root=WORKSPACE_ROOT)

@mcp.tool()
def extract_test_metadata(analysis_id: str, path: str) -> dict:
    content = _read_test_file(analysis_id, path, root=WORKSPACE_ROOT)["content"]
    return _extract_test_metadata(content)

@mcp.tool()
def save_coverage_report(analysis_id: str, repository: str, issue_number: int, requirement: dict,
                          coverage_matrix: list, missing_tests: list, test_plan: list, status: str,
                          tool_call_trace: list) -> dict:
    return _save_coverage_report(analysis_id, repository, issue_number, requirement, coverage_matrix,
                                  missing_tests, test_plan, status, tool_call_trace)

@mcp.tool()
def get_previous_analysis(repository: str, issue_number: int) -> dict:
    return _get_previous_analysis(repository, issue_number)

@mcp.tool()
def cleanup_workspace(analysis_id: str) -> dict:
    return _cleanup_workspace(analysis_id, root=WORKSPACE_ROOT)

if __name__ == "__main__":
    start_sweeper(WORKSPACE_ROOT, interval_seconds=900, max_age_seconds=3600)
    mcp.run(transport="streamable-http")
```

- [ ] **Step 3: Write the failing MCP integration test (real transport, local fixture repo, no network)**

```python
# mcp-server/tests/test_mcp_integration.py
import subprocess
import sys
import time
from pathlib import Path
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from tests.fixtures.make_bare_repo import make_bare_repo

@pytest.mark.asyncio
async def test_find_and_extract_over_real_mcp_transport(tmp_path, monkeypatch):
    clone_url = make_bare_repo(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path / "workspace_root"))
    monkeypatch.setenv("DYNAMODB_TABLE", "unused-in-this-test")
    monkeypatch.setenv("S3_BUCKET", "unused-in-this-test")
    monkeypatch.setenv("GITHUB_TOKEN", "unused-in-this-test")
    monkeypatch.setenv("MCP_GITHUB_URL", "http://localhost:1")  # unused: find_test_files below skips the size check via a stub

    # This test exercises read_test_file + extract_test_metadata + cleanup_workspace directly
    # over real MCP transport, seeding the workspace ourselves to avoid needing a live mcp-github.
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        env={**__import__("os").environ, "MCP_PORT": "8199"},
        cwd=str(Path(__file__).parent.parent),
    )
    try:
        time.sleep(1.0)
        workspace = tmp_path / "workspace_root" / "int-test-1"
        workspace.mkdir(parents=True)
        (workspace / "test_login.py").write_text(
            "def test_login_rejects_invalid_password():\n    assert True\n"
        )
        async with streamablehttp_client("http://localhost:8199/mcp") as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                read_result = await session.call_tool("read_test_file", {"analysis_id": "int-test-1", "path": "test_login.py"})
                assert "test_login_rejects_invalid_password" in read_result.structuredContent["content"]

                meta_result = await session.call_tool("extract_test_metadata", {"analysis_id": "int-test-1", "path": "test_login.py"})
                names = [t["name"] for t in meta_result.structuredContent["tests"]]
                assert "test_login_rejects_invalid_password" in names

                cleanup_result = await session.call_tool("cleanup_workspace", {"analysis_id": "int-test-1"})
                assert cleanup_result.structuredContent["deleted"] is True
    finally:
        proc.terminate()
        proc.wait(timeout=5)
```

- [ ] **Step 4: Run to verify failure, then run for real**

Run: `cd mcp-server && python -m pytest tests/test_mcp_integration.py -v`
Expected: first FAIL (`server.py` doesn't exist yet if run before Step 2) — after Step 2's implementation, expected PASS.

- [ ] **Step 5: Run the full `mcp-server` test suite and check coverage**

Run: `cd mcp-server && python -m pytest --cov=. --cov-report=term-missing`
Expected: all tests PASS, coverage ≥80% on `tools/`, `workspace.py`, `aws.py`

- [ ] **Step 6: Commit**

```bash
git add mcp-server/github_client.py mcp-server/server.py mcp-server/tests/test_mcp_integration.py
git commit -m "feat(mcp-server): wire FastMCP server, register all tools, add MCP integration test"
```

- [ ] **Step 7: Add `mcp-server/Dockerfile`**

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml .
COPY . .
RUN pip install --no-cache-dir .
RUN mkdir -p /workspace
EXPOSE 8100
CMD ["python", "server.py"]
```

- [ ] **Step 8: Commit Dockerfile**

```bash
git add mcp-server/Dockerfile
git commit -m "build(mcp-server): add Dockerfile"
```

---

## Phase 2 — `backend/shared`

### Task 9: Config, AWS client wrappers, `AnalysisRecord` model

**Files:**
- Create: `backend/shared/config.py`
- Create: `backend/shared/models.py`
- Create: `backend/shared/dynamodb.py`
- Create: `backend/shared/s3.py`
- Create: `backend/shared/sqs.py`
- Test: `backend/shared/tests/test_models.py`, `test_dynamodb.py`, `test_s3.py`, `test_sqs.py`
- Fixture: `backend/shared/tests/fixtures/sample_analysis_record.json` (same shape as `mcp-server/tests/fixtures/` — see Task 6 note: independently maintained, contract-tested against the same JSON, not code-shared with `mcp-server`)

**Interfaces:**
- Produces: `class Settings(BaseSettings)` (fields: `env, dynamodb_table, s3_bucket, sqs_queue_url, mcp_github_url, mcp_test_analysis_url, anthropic_api_key, anthropic_model`), loaded via `get_settings() -> Settings` (env-driven, cached with `functools.lru_cache`).
- Produces: `class AnalysisRecord(BaseModel)` with fields `analysis_id: str, repository: str, issue_number: int, status: Literal["pending","running","completed","failed"], created_at: str, updated_at: str, requirement_summary: str | None, coverage_summary: dict | None, missing_tests_count: int, s3_report_key: str | None, error_message: str | None, storage_status: str | None, tool_call_trace: list[dict], github_issue_url: str | None, user_feedback: dict | None`.
- Produces: `class AnalysisStore` — `upsert(record: AnalysisRecord) -> None`, `get(analysis_id: str) -> AnalysisRecord | None`, `query_by_repo_issue(repository: str, issue_number: int) -> list[AnalysisRecord]`, `list_recent(limit: int, cursor: str | None = None) -> tuple[list[AnalysisRecord], str | None]`. Consumed by `backend/worker`'s Job Intake node (Task 10) and every `backend/api` route (Tasks 19–21).
- Produces: `class ReportStore` — `presigned_url(s3_key: str, expires_in: int = 300) -> str`, `read_json(s3_key: str) -> dict`. Consumed by Task 21.
- Produces: `class JobQueue` — `send_job(analysis_id: str, repository: str, issue_number: int, notes: str | None) -> None`, `receive_jobs(max_messages: int = 1, wait_seconds: int = 20) -> list[dict]` (each dict has `body: dict, receipt_handle: str`), `delete_message(receipt_handle: str) -> None`. Consumed by Task 19 (`send_job`) and Task 10 (`receive_jobs`/`delete_message`).

- [ ] **Step 1: Write failing test for `AnalysisRecord` round-trip against the shared fixture**

```python
# backend/shared/tests/test_models.py
import json
from pathlib import Path
from models import AnalysisRecord

FIXTURE = Path(__file__).parent / "fixtures" / "sample_analysis_record.json"

def test_analysis_record_parses_the_shared_fixture():
    data = json.loads(FIXTURE.read_text())
    record = AnalysisRecord.model_validate(data)
    assert record.analysis_id == data["analysis_id"]
    assert record.status == "completed"
```

```json
// backend/shared/tests/fixtures/sample_analysis_record.json
{
  "analysis_id": "a1", "repository": "acme/widgets", "issue_number": 42,
  "status": "completed", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:05:00Z",
  "requirement_summary": "Login", "coverage_summary": {"percent_covered": 80.0},
  "missing_tests_count": 1, "s3_report_key": "acme/widgets/42/a1.json",
  "error_message": null, "storage_status": "saved", "tool_call_trace": [],
  "github_issue_url": null, "user_feedback": null
}
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/shared && python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Implement `config.py` and `models.py`**

```python
# backend/shared/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    env: str = "dev"
    dynamodb_table: str
    s3_bucket: str
    sqs_queue_url: str
    mcp_github_url: str
    mcp_test_analysis_url: str
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# backend/shared/models.py
from typing import Literal
from pydantic import BaseModel

class AnalysisRecord(BaseModel):
    analysis_id: str
    repository: str
    issue_number: int
    status: Literal["pending", "running", "completed", "failed"]
    created_at: str
    updated_at: str
    requirement_summary: str | None = None
    coverage_summary: dict | None = None
    missing_tests_count: int = 0
    s3_report_key: str | None = None
    error_message: str | None = None
    storage_status: str | None = None
    tool_call_trace: list[dict] = []
    github_issue_url: str | None = None
    user_feedback: dict | None = None
```

Add `pydantic-settings>=2.6` to `backend/shared/pyproject.toml` dependencies.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend/shared && python -m pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Write failing tests for `AnalysisStore`, `ReportStore`, `JobQueue` (moto)**

```python
# backend/shared/tests/test_dynamodb.py
import boto3
import pytest
from moto import mock_aws
from models import AnalysisRecord
from dynamodb import AnalysisStore

@pytest.fixture
def store(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="t", KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "analysis_id", "AttributeType": "S"},
                {"AttributeName": "repository_issue", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "S"},
                {"AttributeName": "gsi2_pk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {"IndexName": "repository_issue-index", "KeySchema": [
                    {"AttributeName": "repository_issue", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}],
                 "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "recent-index", "KeySchema": [
                    {"AttributeName": "gsi2_pk", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}],
                 "Projection": {"ProjectionType": "ALL"}},
            ],
        )
        yield AnalysisStore(table_name="t")

def test_upsert_then_get_roundtrips(store):
    record = AnalysisRecord(analysis_id="a1", repository="acme/widgets", issue_number=42,
                             status="running", created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
    store.upsert(record)
    fetched = store.get("a1")
    assert fetched.status == "running"

def test_upsert_is_idempotent_last_write_wins(store):
    r1 = AnalysisRecord(analysis_id="a1", repository="acme/widgets", issue_number=42,
                         status="running", created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
    r2 = r1.model_copy(update={"status": "completed", "updated_at": "2026-01-01T00:05:00Z"})
    store.upsert(r1)
    store.upsert(r2)
    assert store.get("a1").status == "completed"

def test_query_by_repo_issue_orders_newest_first(store):
    for i, ts in enumerate(["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"]):
        store.upsert(AnalysisRecord(analysis_id=f"a{i}", repository="acme/widgets", issue_number=42,
                                     status="completed", created_at=ts, updated_at=ts))
    results = store.query_by_repo_issue("acme/widgets", 42)
    assert [r.analysis_id for r in results] == ["a1", "a0"]
```

- [ ] **Step 6: Run to verify failure, then implement**

Run: `cd backend/shared && python -m pytest tests/test_dynamodb.py -v` → FAIL (`ModuleNotFoundError`)

```python
# backend/shared/dynamodb.py
import boto3
from boto3.dynamodb.conditions import Key
from models import AnalysisRecord

class AnalysisStore:
    def __init__(self, table_name: str):
        self._table = boto3.resource("dynamodb").Table(table_name)

    def upsert(self, record: AnalysisRecord) -> None:
        item = record.model_dump()
        item["repository_issue"] = f"{record.repository}#{record.issue_number}"
        item["gsi2_pk"] = "ANALYSIS"
        self._table.put_item(Item=item)

    def get(self, analysis_id: str) -> AnalysisRecord | None:
        response = self._table.get_item(Key={"analysis_id": analysis_id})
        item = response.get("Item")
        return AnalysisRecord.model_validate(item) if item else None

    def query_by_repo_issue(self, repository: str, issue_number: int) -> list[AnalysisRecord]:
        response = self._table.query(
            IndexName="repository_issue-index",
            KeyConditionExpression=Key("repository_issue").eq(f"{repository}#{issue_number}"),
            ScanIndexForward=False,
        )
        return [AnalysisRecord.model_validate(item) for item in response["Items"]]

    def list_recent(self, limit: int, cursor: str | None = None) -> tuple[list[AnalysisRecord], str | None]:
        kwargs = {
            "IndexName": "recent-index",
            "KeyConditionExpression": Key("gsi2_pk").eq("ANALYSIS"),
            "ScanIndexForward": False, "Limit": limit,
        }
        if cursor:
            kwargs["ExclusiveStartKey"] = {"gsi2_pk": "ANALYSIS", "created_at": cursor, "analysis_id": cursor}
        response = self._table.query(**kwargs)
        records = [AnalysisRecord.model_validate(item) for item in response["Items"]]
        next_cursor = response.get("LastEvaluatedKey", {}).get("created_at")
        return records, next_cursor
```

```python
# backend/shared/s3.py
import json
import boto3

class ReportStore:
    def __init__(self, bucket: str):
        self._bucket = bucket
        self._client = boto3.client("s3")

    def presigned_url(self, s3_key: str, expires_in: int = 300) -> str:
        return self._client.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": s3_key}, ExpiresIn=expires_in,
        )

    def read_json(self, s3_key: str) -> dict:
        body = self._client.get_object(Bucket=self._bucket, Key=s3_key)["Body"].read()
        return json.loads(body)
```

```python
# backend/shared/sqs.py
import json
import boto3

class JobQueue:
    def __init__(self, queue_url: str):
        self._queue_url = queue_url
        self._client = boto3.client("sqs")

    def send_job(self, analysis_id: str, repository: str, issue_number: int, notes: str | None) -> None:
        body = {"analysis_id": analysis_id, "repository": repository, "issue_number": issue_number, "notes": notes}
        self._client.send_message(QueueUrl=self._queue_url, MessageBody=json.dumps(body))

    def receive_jobs(self, max_messages: int = 1, wait_seconds: int = 20) -> list[dict]:
        response = self._client.receive_message(
            QueueUrl=self._queue_url, MaxNumberOfMessages=max_messages, WaitTimeSeconds=wait_seconds,
        )
        return [{"body": json.loads(m["Body"]), "receipt_handle": m["ReceiptHandle"]} for m in response.get("Messages", [])]

    def delete_message(self, receipt_handle: str) -> None:
        self._client.delete_message(QueueUrl=self._queue_url, ReceiptHandle=receipt_handle)
```

Add analogous moto-based tests `test_s3.py` (presigned URL is generated, `read_json` round-trips a `put_object`'d payload) and `test_sqs.py` (`send_job` then `receive_jobs` returns the same body, `delete_message` empties the queue) following the same fixture pattern as `test_dynamodb.py`.

- [ ] **Step 7: Run full shared test suite**

Run: `cd backend/shared && python -m pytest --cov=. --cov-report=term-missing`
Expected: all PASS, ≥80% coverage

- [ ] **Step 8: Commit**

```bash
git add backend/shared
git commit -m "feat(shared): add config, AnalysisRecord model, DynamoDB/S3/SQS client wrappers"
```

---

## Phase 3 — `backend/worker` (LangGraph Agent)

`backend/worker` depends on `backend/shared` as a path dependency (`pip install -e ../shared`, added to `backend/worker/pyproject.toml`'s dev install step in Task 1's follow-up — add this now as part of Task 10 Step 0).

### Task 10: Worker skeleton — SQS consumer loop, health endpoint, Job Intake node

**Files:**
- Modify: `backend/worker/pyproject.toml` (add `-e ../shared` and `-e ../shared[dev]` install note; add `fastapi`, `uvicorn` for the health endpoint)
- Create: `backend/worker/app/state.py`
- Create: `backend/worker/app/nodes/__init__.py`
- Create: `backend/worker/app/nodes/job_intake.py`
- Create: `backend/worker/app/health.py`
- Create: `backend/worker/app/main.py`
- Test: `backend/worker/tests/test_job_intake.py`

**Interfaces:**
- Consumes: `AnalysisStore`, `JobQueue`, `AnalysisRecord`, `get_settings` from `backend/shared` (Task 9).
- Produces: `class AgentState(TypedDict)` with fields `analysis_id: str, repository: str, issue_number: int, notes: str | None, default_branch: str, issue_body: str, issue_comments: list[str], requirement: dict, search_keywords: list[str], candidate_files: list[dict], test_metadata: dict, coverage_matrix: list[dict], test_plan: list[dict], missing_tests: list[dict], warnings: list[str], tool_call_trace: list[dict], status: str, error_message: str | None` — every later node task reads/writes this exact shape.
- Produces: `job_intake(state: AgentState, store: AnalysisStore) -> AgentState` (upserts `status="running"`, idempotent by `analysis_id`).
- Produces: `main.py`'s poll loop, consumed by no other task (it's the process entrypoint) — but its shape (`while True: receive → run_analysis → delete_message`) is what Task 17's `run_analysis` plugs into.

- [ ] **Step 1: Write failing test for `job_intake`**

```python
# backend/worker/tests/test_job_intake.py
import boto3
import pytest
from moto import mock_aws
from dynamodb import AnalysisStore
from app.nodes.job_intake import job_intake

@pytest.fixture
def store(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="t", KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "analysis_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield AnalysisStore(table_name="t")

def test_job_intake_writes_running_status(store):
    state = {"analysis_id": "a1", "repository": "acme/widgets", "issue_number": 42, "notes": None,
             "tool_call_trace": [], "warnings": []}
    result = job_intake(state, store)
    assert result["status"] == "running"
    assert store.get("a1").status == "running"

def test_job_intake_is_idempotent_on_redelivery(store):
    state = {"analysis_id": "a1", "repository": "acme/widgets", "issue_number": 42, "notes": None,
              "tool_call_trace": [], "warnings": []}
    job_intake(state, store)
    result = job_intake(state, store)  # simulates SQS redelivery
    assert result["status"] == "running"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/worker && python -m pytest tests/test_job_intake.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `state.py` and `job_intake.py`**

```python
# backend/worker/app/state.py
from typing import TypedDict

class AgentState(TypedDict):
    analysis_id: str
    repository: str
    issue_number: int
    notes: str | None
    default_branch: str
    issue_body: str
    issue_comments: list[str]
    requirement: dict
    search_keywords: list[str]
    candidate_files: list[dict]
    test_metadata: dict
    coverage_matrix: list[dict]
    test_plan: list[dict]
    missing_tests: list[dict]
    warnings: list[str]
    tool_call_trace: list[dict]
    status: str
    error_message: str | None
```

```python
# backend/worker/app/nodes/job_intake.py
from datetime import datetime, timezone
from models import AnalysisRecord
from dynamodb import AnalysisStore

def job_intake(state: dict, store: AnalysisStore) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    store.upsert(AnalysisRecord(
        analysis_id=state["analysis_id"], repository=state["repository"],
        issue_number=state["issue_number"], status="running", created_at=now, updated_at=now,
        tool_call_trace=state.get("tool_call_trace", []),
    ))
    state["status"] = "running"
    return state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend/worker && python -m pytest tests/test_job_intake.py -v`
Expected: PASS

- [ ] **Step 5: Add health endpoint and poll-loop skeleton (not unit tested here — wired end-to-end in Task 17)**

```python
# backend/worker/app/health.py
import threading
from fastapi import FastAPI
import uvicorn

def start_health_server(port: int = 8080) -> threading.Thread:
    app = FastAPI()

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        return {"status": "ok"}  # extended in Task 17 to check SQS reachability

    thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning"),
        daemon=True, name="worker-health",
    )
    thread.start()
    return thread
```

```python
# backend/worker/app/main.py
import time
from config import get_settings
from sqs import JobQueue
from app.health import start_health_server

def poll_forever() -> None:
    settings = get_settings()
    queue = JobQueue(settings.sqs_queue_url)
    start_health_server()
    while True:
        jobs = queue.receive_jobs(max_messages=1, wait_seconds=20)
        for job in jobs:
            # run_analysis(**job["body"]) wired in Task 17
            queue.delete_message(job["receipt_handle"])
        if not jobs:
            time.sleep(1)

if __name__ == "__main__":
    poll_forever()
```

- [ ] **Step 6: Commit**

```bash
git add backend/worker/app backend/worker/tests backend/worker/pyproject.toml
git commit -m "feat(worker): add AgentState, job_intake node, health endpoint, poll-loop skeleton"
```

### Task 11: MCP client wrapper + Request Validator + Requirement Retriever nodes

**Files:**
- Create: `backend/worker/app/mcp_clients.py`
- Create: `backend/worker/app/nodes/request_validator.py`
- Create: `backend/worker/app/nodes/requirement_retriever.py`
- Test: `backend/worker/tests/test_request_validator.py`, `test_requirement_retriever.py`

**Interfaces:**
- Consumes: `AgentState` from Task 10.
- Produces: `async def call_github_tool(tool_name: str, **kwargs) -> dict` and `async def call_test_mcp_tool(tool_name: str, **kwargs) -> dict` in `mcp_clients.py` (both open a `streamablehttp_client` session per call against `settings.mcp_github_url` / `settings.mcp_test_analysis_url`, matching the tool contracts from spec §5). Consumed by every remaining node task (13, 14, 15) and by Task 17's Report Saver/Cleanup.
- Produces: `async def request_validator(state: AgentState) -> AgentState` (sets `state["default_branch"]`; sets `state["status"]="failed"` + `state["error_message"]` and short-circuits on not-found/access-denied — later graph wiring in Task 17 routes on `status`).
- Produces: `async def requirement_retriever(state: AgentState) -> AgentState` (sets `state["issue_body"]`, `state["issue_comments"]`; on comment-fetch failure, sets `issue_comments=[]` and appends a warning instead of failing).

- [ ] **Step 1: Write failing tests using a fake MCP client**

```python
# backend/worker/tests/test_request_validator.py
import pytest
from unittest.mock import AsyncMock, patch
from app.nodes.request_validator import request_validator

@pytest.mark.asyncio
async def test_sets_default_branch_on_success():
    state = {"repository": "acme/widgets", "tool_call_trace": [], "warnings": []}
    with patch("app.nodes.request_validator.call_github_tool", new=AsyncMock(return_value={"default_branch": "main"})):
        result = await request_validator(state)
    assert result["default_branch"] == "main"
    assert result.get("status") != "failed"

@pytest.mark.asyncio
async def test_fails_gracefully_on_repo_not_found():
    state = {"repository": "acme/does-not-exist", "tool_call_trace": [], "warnings": []}
    with patch("app.nodes.request_validator.call_github_tool", new=AsyncMock(side_effect=Exception("404 Not Found"))):
        result = await request_validator(state)
    assert result["status"] == "failed"
    assert "not found" in result["error_message"].lower() or "404" in result["error_message"]
```

```python
# backend/worker/tests/test_requirement_retriever.py
import pytest
from unittest.mock import AsyncMock, patch
from app.nodes.requirement_retriever import requirement_retriever

@pytest.mark.asyncio
async def test_retrieves_issue_body_and_comments():
    state = {"repository": "acme/widgets", "issue_number": 42, "tool_call_trace": [], "warnings": []}
    calls = {"get_issue": {"body": "Add login"}, "get_issue_comments": {"comments": ["clarification"]}}
    async def fake_call(tool_name, **kwargs):
        return calls[tool_name]
    with patch("app.nodes.requirement_retriever.call_github_tool", new=AsyncMock(side_effect=fake_call)):
        result = await requirement_retriever(state)
    assert result["issue_body"] == "Add login"
    assert result["issue_comments"] == ["clarification"]

@pytest.mark.asyncio
async def test_falls_back_to_body_only_when_comments_fail():
    state = {"repository": "acme/widgets", "issue_number": 42, "tool_call_trace": [], "warnings": []}
    async def fake_call(tool_name, **kwargs):
        if tool_name == "get_issue":
            return {"body": "Add login"}
        raise Exception("comments API failed")
    with patch("app.nodes.requirement_retriever.call_github_tool", new=AsyncMock(side_effect=fake_call)):
        result = await requirement_retriever(state)
    assert result["issue_body"] == "Add login"
    assert result["issue_comments"] == []
    assert any("comment" in w.lower() for w in result["warnings"])
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/worker && python -m pytest tests/test_request_validator.py tests/test_requirement_retriever.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `mcp_clients.py` and both nodes**

```python
# backend/worker/app/mcp_clients.py
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from config import get_settings

async def _call(base_url: str, tool_name: str, **kwargs) -> dict:
    async with streamablehttp_client(base_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, kwargs)
            return result.structuredContent

async def call_github_tool(tool_name: str, **kwargs) -> dict:
    return await _call(get_settings().mcp_github_url, tool_name, **kwargs)

async def call_test_mcp_tool(tool_name: str, **kwargs) -> dict:
    return await _call(get_settings().mcp_test_analysis_url, tool_name, **kwargs)
```

```python
# backend/worker/app/nodes/request_validator.py
from app.mcp_clients import call_github_tool

async def request_validator(state: dict) -> dict:
    owner, repo = state["repository"].split("/", 1)
    try:
        result = await call_github_tool("get_repository", owner=owner, repo=repo)
    except Exception as exc:
        state["status"] = "failed"
        state["error_message"] = f"Repository validation failed: {exc}"
        return state
    state["default_branch"] = result.get("default_branch", "main")
    return state
```

```python
# backend/worker/app/nodes/requirement_retriever.py
from app.mcp_clients import call_github_tool

async def requirement_retriever(state: dict) -> dict:
    owner, repo = state["repository"].split("/", 1)
    issue = await call_github_tool("get_issue", owner=owner, repo=repo, issue_number=state["issue_number"])
    state["issue_body"] = issue.get("body", "")
    try:
        comments = await call_github_tool("get_issue_comments", owner=owner, repo=repo, issue_number=state["issue_number"])
        state["issue_comments"] = comments.get("comments", [])
    except Exception:
        state["issue_comments"] = []
        state.setdefault("warnings", []).append("Could not fetch issue comments; analyzing issue body only.")
    return state
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend/worker && python -m pytest tests/test_request_validator.py tests/test_requirement_retriever.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/worker/app/mcp_clients.py backend/worker/app/nodes/request_validator.py backend/worker/app/nodes/requirement_retriever.py backend/worker/tests/test_request_validator.py backend/worker/tests/test_requirement_retriever.py
git commit -m "feat(worker): add MCP client wrapper, Request Validator and Requirement Retriever nodes"
```

### Task 12: LLM client wrapper + Requirement Parser node

**Files:**
- Create: `backend/worker/app/llm_client.py`
- Create: `backend/worker/app/retry.py`
- Create: `backend/worker/app/nodes/requirement_parser.py`
- Test: `backend/worker/tests/test_llm_client.py`, `test_requirement_parser.py`

**Interfaces:**
- Consumes: `AgentState` (`issue_body`, `issue_comments`) from Task 11.
- Produces: `async def call_llm(system_prompt: str, user_prompt: str, response_model: type[BaseModel], tool_name: str) -> BaseModel` in `llm_client.py` — uses Claude's forced tool-use for structured output; wraps calls in `with_retry`. Consumed by every remaining LLM node (13, 14, 15).
- Produces: `async def with_retry(fn, *args, max_attempts: int = 3, backoff_base: float = 1.0, **kwargs) -> Any` in `retry.py` — generic exponential-backoff wrapper (1s/2s/4s), re-raises after exhausting attempts. Consumed by `llm_client.call_llm` and by MCP tool calls in later tasks that need retry (Task 13's `find_test_files` call).
- Produces: `class AcceptanceCriterion(BaseModel)` (`id: str, text: str`), `class Requirement(BaseModel)` (`feature_name: str, business_objective: str, functional_requirements: list[str], acceptance_criteria: list[AcceptanceCriterion], validation_rules: list[str], user_roles: list[str], constraints: list[str], gaps: list[str]`) in `requirement_parser.py`.
- Produces: `async def requirement_parser(state: AgentState) -> AgentState` — populates `state["requirement"]` (as a dict via `.model_dump()`); if `acceptance_criteria` is empty, sets `status="failed"`, `error_message="No acceptance criteria found in issue"`.

- [ ] **Step 1: Write failing test for `with_retry`**

```python
# backend/worker/tests/test_llm_client.py
import pytest
from retry import with_retry

@pytest.mark.asyncio
async def test_with_retry_succeeds_after_transient_failures():
    calls = {"count": 0}
    async def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("transient")
        return "ok"
    result = await with_retry(flaky, max_attempts=3, backoff_base=0.01)
    assert result == "ok"
    assert calls["count"] == 3

@pytest.mark.asyncio
async def test_with_retry_reraises_after_exhausting_attempts():
    async def always_fails():
        raise TimeoutError("still failing")
    with pytest.raises(TimeoutError):
        await with_retry(always_fails, max_attempts=2, backoff_base=0.01)
```

- [ ] **Step 2: Run to verify failure, then implement `retry.py`**

Run: `cd backend/worker && python -m pytest tests/test_llm_client.py -v` → FAIL (`ModuleNotFoundError`)

```python
# backend/worker/app/retry.py — note: imported as top-level `retry` per test above (package root on sys.path)
import asyncio

async def with_retry(fn, *args, max_attempts: int = 3, backoff_base: float = 1.0, **kwargs):
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                await asyncio.sleep(backoff_base * (2 ** attempt))
    raise last_exc
```

Place `retry.py` at `backend/worker/retry.py` (package root, alongside `config.py`/`models.py`/`dynamodb.py` re-exports — see Step 6 note) so it's importable the same way in both tests and `app/` modules.

- [ ] **Step 3: Run to verify `with_retry` tests pass**

Run: `cd backend/worker && python -m pytest tests/test_llm_client.py -v`
Expected: PASS

- [ ] **Step 4: Write failing test for `requirement_parser` with a stub LLM**

```python
# backend/worker/tests/test_requirement_parser.py
import pytest
from unittest.mock import AsyncMock, patch
from app.nodes.requirement_parser import requirement_parser, Requirement, AcceptanceCriterion

@pytest.mark.asyncio
async def test_extracts_structured_requirement():
    state = {"issue_body": "Users must be able to log in with email and password.",
             "issue_comments": [], "tool_call_trace": [], "warnings": []}
    stub_result = Requirement(
        feature_name="Login", business_objective="Let users authenticate",
        functional_requirements=["Email/password login"],
        acceptance_criteria=[AcceptanceCriterion(id="AC1", text="Invalid password returns 401")],
        validation_rules=[], user_roles=["user"], constraints=[], gaps=[],
    )
    with patch("app.nodes.requirement_parser.call_llm", new=AsyncMock(return_value=stub_result)):
        result = await requirement_parser(state)
    assert result["requirement"]["feature_name"] == "Login"
    assert len(result["requirement"]["acceptance_criteria"]) == 1
    assert result.get("status") != "failed"

@pytest.mark.asyncio
async def test_terminates_gracefully_when_no_criteria_found():
    state = {"issue_body": "not much here", "issue_comments": [], "tool_call_trace": [], "warnings": []}
    stub_result = Requirement(
        feature_name="Unknown", business_objective="", functional_requirements=[],
        acceptance_criteria=[], validation_rules=[], user_roles=[], constraints=[],
        gaps=["No acceptance criteria stated in the issue"],
    )
    with patch("app.nodes.requirement_parser.call_llm", new=AsyncMock(return_value=stub_result)):
        result = await requirement_parser(state)
    assert result["status"] == "failed"
    assert "acceptance criteria" in result["error_message"].lower()
```

- [ ] **Step 5: Run to verify failure**

Run: `cd backend/worker && python -m pytest tests/test_requirement_parser.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 6: Implement `llm_client.py` and `requirement_parser.py`**

```python
# backend/worker/app/llm_client.py
from anthropic import AsyncAnthropic
from pydantic import BaseModel
from config import get_settings
from retry import with_retry

async def call_llm(system_prompt: str, user_prompt: str, response_model: type[BaseModel], tool_name: str) -> BaseModel:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def _do_call():
        return await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[{"name": tool_name, "input_schema": response_model.model_json_schema()}],
            tool_choice={"type": "tool", "name": tool_name},
        )

    response = await with_retry(_do_call, max_attempts=3, backoff_base=1.0)
    tool_use = next(block for block in response.content if block.type == "tool_use")
    return response_model.model_validate(tool_use.input)
```

```python
# backend/worker/app/nodes/requirement_parser.py
from pydantic import BaseModel
from app.llm_client import call_llm

class AcceptanceCriterion(BaseModel):
    id: str
    text: str

class Requirement(BaseModel):
    feature_name: str
    business_objective: str
    functional_requirements: list[str]
    acceptance_criteria: list[AcceptanceCriterion]
    validation_rules: list[str]
    user_roles: list[str]
    constraints: list[str]
    gaps: list[str]

SYSTEM_PROMPT = """You are a software quality analysis agent. Extract structured requirements
from a GitHub issue. Base your output only on the issue text provided — never invent acceptance
criteria, constraints, or roles that are not stated or clearly implied. If information is
missing, list it in `gaps` instead of guessing."""

async def requirement_parser(state: dict) -> dict:
    user_prompt = f"Issue body:\n{state['issue_body']}\n\nComments:\n" + "\n---\n".join(state.get("issue_comments", []))
    requirement: Requirement = await call_llm(SYSTEM_PROMPT, user_prompt, Requirement, tool_name="extract_requirement")
    state["requirement"] = requirement.model_dump()
    if not requirement.acceptance_criteria:
        state["status"] = "failed"
        state["error_message"] = "No acceptance criteria found in issue body or comments"
    return state
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend/worker && python -m pytest tests/test_requirement_parser.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/worker/retry.py backend/worker/app/llm_client.py backend/worker/app/nodes/requirement_parser.py backend/worker/tests/test_llm_client.py backend/worker/tests/test_requirement_parser.py
git commit -m "feat(worker): add LLM client wrapper, retry utility, Requirement Parser node"
```

### Task 13: Test Search Planner + Test File Retriever + Test File Classifier nodes

**Files:**
- Create: `backend/worker/app/nodes/test_search_planner.py`
- Create: `backend/worker/app/nodes/test_file_retriever.py`
- Create: `backend/worker/app/nodes/test_file_classifier.py`
- Test: one test file per node, same names with `test_` prefix

**Interfaces:**
- Consumes: `state["requirement"]["acceptance_criteria"]` (Task 12), `call_llm` (Task 12), `call_test_mcp_tool` (Task 11).
- Produces: `async def test_search_planner(state: AgentState) -> AgentState` — sets `state["search_keywords"]: list[str]`.
- Produces: `async def test_file_retriever(state: AgentState) -> AgentState` — calls MCP `find_test_files`, sets `state["candidate_files"]: list[dict]` (empty list on no matches — not a failure).
- Produces: `async def test_file_classifier(state: AgentState) -> AgentState` — calls MCP `extract_test_metadata` per candidate file, sets `state["test_metadata"]: dict[str, list[dict]]` keyed by file path; a single file's parse failure is caught, appended to `state["warnings"]`, and skipped (not fatal).

- [ ] **Step 1: Write failing tests**

```python
# backend/worker/tests/test_test_search_planner.py
import pytest
from unittest.mock import AsyncMock, patch
from app.nodes.test_search_planner import test_search_planner, SearchKeywords

@pytest.mark.asyncio
async def test_generates_keywords_from_criteria():
    state = {"requirement": {"acceptance_criteria": [{"id": "AC1", "text": "Invalid password returns 401"}]},
             "tool_call_trace": [], "warnings": []}
    stub = SearchKeywords(keywords=["login", "password", "401"])
    with patch("app.nodes.test_search_planner.call_llm", new=AsyncMock(return_value=stub)):
        result = await test_search_planner(state)
    assert result["search_keywords"] == ["login", "password", "401"]
```

```python
# backend/worker/tests/test_test_file_retriever.py
import pytest
from unittest.mock import AsyncMock, patch
from app.nodes.test_file_retriever import test_file_retriever

@pytest.mark.asyncio
async def test_populates_candidate_files():
    state = {"repository": "acme/widgets", "default_branch": "main", "analysis_id": "a1",
             "search_keywords": ["login"], "tool_call_trace": [], "warnings": []}
    fake_response = {"files": [{"path": "tests/test_login.py", "size_bytes": 100, "matched_keywords": ["login"]}]}
    with patch("app.nodes.test_file_retriever.call_test_mcp_tool", new=AsyncMock(return_value=fake_response)):
        result = await test_file_retriever(state)
    assert result["candidate_files"] == fake_response["files"]

@pytest.mark.asyncio
async def test_no_matches_is_not_a_failure():
    state = {"repository": "acme/widgets", "default_branch": "main", "analysis_id": "a1",
             "search_keywords": ["nonexistent"], "tool_call_trace": [], "warnings": []}
    with patch("app.nodes.test_file_retriever.call_test_mcp_tool", new=AsyncMock(return_value={"files": []})):
        result = await test_file_retriever(state)
    assert result["candidate_files"] == []
    assert result.get("status") != "failed"
```

```python
# backend/worker/tests/test_test_file_classifier.py
import pytest
from unittest.mock import AsyncMock, patch
from app.nodes.test_file_classifier import test_file_classifier

@pytest.mark.asyncio
async def test_extracts_metadata_per_candidate_file():
    state = {"analysis_id": "a1", "candidate_files": [{"path": "tests/test_login.py"}],
             "tool_call_trace": [], "warnings": []}
    fake_meta = {"tests": [{"name": "test_login_rejects_invalid_password"}]}
    with patch("app.nodes.test_file_classifier.call_test_mcp_tool", new=AsyncMock(return_value=fake_meta)):
        result = await test_file_classifier(state)
    assert result["test_metadata"]["tests/test_login.py"] == fake_meta["tests"]

@pytest.mark.asyncio
async def test_skips_unparseable_file_without_failing():
    state = {"analysis_id": "a1", "candidate_files": [{"path": "tests/broken.py"}],
              "tool_call_trace": [], "warnings": []}
    with patch("app.nodes.test_file_classifier.call_test_mcp_tool", new=AsyncMock(side_effect=Exception("SyntaxError"))):
        result = await test_file_classifier(state)
    assert result["test_metadata"] == {}
    assert any("broken.py" in w for w in result["warnings"])
```

- [ ] **Step 2: Run to verify all three fail**

Run: `cd backend/worker && python -m pytest tests/test_test_search_planner.py tests/test_test_file_retriever.py tests/test_test_file_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError` for each

- [ ] **Step 3: Implement all three nodes**

```python
# backend/worker/app/nodes/test_search_planner.py
from pydantic import BaseModel
from app.llm_client import call_llm

class SearchKeywords(BaseModel):
    keywords: list[str]

SYSTEM_PROMPT = """You generate repository search keywords for finding pytest test files
relevant to given acceptance criteria. Prefer concrete function names, endpoint paths,
component names, and domain terms over generic words."""

async def test_search_planner(state: dict) -> dict:
    criteria_text = "\n".join(f"- {c['text']}" for c in state["requirement"]["acceptance_criteria"])
    result: SearchKeywords = await call_llm(SYSTEM_PROMPT, criteria_text, SearchKeywords, tool_name="generate_keywords")
    state["search_keywords"] = result.keywords
    return state
```

```python
# backend/worker/app/nodes/test_file_retriever.py
from app.mcp_clients import call_test_mcp_tool

async def test_file_retriever(state: dict) -> dict:
    result = await call_test_mcp_tool(
        "find_test_files", analysis_id=state["analysis_id"], repository=state["repository"],
        ref=state["default_branch"], keywords=state["search_keywords"],
    )
    state["candidate_files"] = result["files"]
    return state
```

```python
# backend/worker/app/nodes/test_file_classifier.py
from app.mcp_clients import call_test_mcp_tool

async def test_file_classifier(state: dict) -> dict:
    metadata = {}
    for candidate in state["candidate_files"]:
        path = candidate["path"]
        try:
            result = await call_test_mcp_tool("extract_test_metadata", analysis_id=state["analysis_id"], path=path)
            metadata[path] = result["tests"]
        except Exception:
            state.setdefault("warnings", []).append(f"Could not parse {path}; skipped.")
    state["test_metadata"] = metadata
    return state
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend/worker && python -m pytest tests/test_test_search_planner.py tests/test_test_file_retriever.py tests/test_test_file_classifier.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/worker/app/nodes/test_search_planner.py backend/worker/app/nodes/test_file_retriever.py backend/worker/app/nodes/test_file_classifier.py backend/worker/tests/test_test_search_planner.py backend/worker/tests/test_test_file_retriever.py backend/worker/tests/test_test_file_classifier.py
git commit -m "feat(worker): add Test Search Planner, Test File Retriever, Test File Classifier nodes"
```

### Task 14: Coverage Analyzer node (with `read_test_file` fallback)

**Files:**
- Create: `backend/worker/app/nodes/coverage_analyzer.py`
- Test: `backend/worker/tests/test_coverage_analyzer.py`

**Interfaces:**
- Consumes: `state["requirement"]["acceptance_criteria"]`, `state["test_metadata"]` (Task 13), `call_llm` (Task 12), `call_test_mcp_tool` (Task 11).
- Produces: `class CoverageEntry(BaseModel)` (`criterion_id: str, status: Literal["Covered","Partially covered","Not covered","Unable to determine"], evidence: list[str], explanation: str`). `async def coverage_analyzer(state: AgentState) -> AgentState` — sets `state["coverage_matrix"]: list[dict]` (one entry per criterion); if the "no supported framework" condition is hit (`state["test_metadata"]` is empty AND `state["candidate_files"]` is non-empty — i.e., files were found but none parsed as pytest), appends the framework warning from spec §13.

- [ ] **Step 1: Write the failing test**

```python
# backend/worker/tests/test_coverage_analyzer.py
import pytest
from unittest.mock import AsyncMock, patch
from app.nodes.coverage_analyzer import coverage_analyzer, CoverageEntry

@pytest.mark.asyncio
async def test_classifies_each_criterion():
    state = {
        "requirement": {"acceptance_criteria": [{"id": "AC1", "text": "Invalid password returns 401"}]},
        "test_metadata": {"tests/test_login.py": [{"name": "test_login_rejects_invalid_password", "assert_count": 1}]},
        "candidate_files": [{"path": "tests/test_login.py"}],
        "analysis_id": "a1", "tool_call_trace": [], "warnings": [],
    }
    stub = [CoverageEntry(criterion_id="AC1", status="Covered",
                           evidence=["tests/test_login.py::test_login_rejects_invalid_password"],
                           explanation="Test asserts 401 on invalid password.")]
    with patch("app.nodes.coverage_analyzer.call_llm", new=AsyncMock(return_value=stub)):
        result = await coverage_analyzer(state)
    assert result["coverage_matrix"][0]["status"] == "Covered"

@pytest.mark.asyncio
async def test_flags_unsupported_framework_when_files_found_but_none_parsed():
    state = {
        "requirement": {"acceptance_criteria": [{"id": "AC1", "text": "x"}]},
        "test_metadata": {}, "candidate_files": [{"path": "tests/login.test.js"}],
        "analysis_id": "a1", "tool_call_trace": [], "warnings": [],
    }
    stub = [CoverageEntry(criterion_id="AC1", status="Unable to determine", evidence=[], explanation="No pytest tests found.")]
    with patch("app.nodes.coverage_analyzer.call_llm", new=AsyncMock(return_value=stub)):
        result = await coverage_analyzer(state)
    assert any("no supported test framework" in w.lower() for w in result["warnings"])
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/worker && python -m pytest tests/test_coverage_analyzer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# backend/worker/app/nodes/coverage_analyzer.py
from typing import Literal
from pydantic import BaseModel, RootModel
from app.llm_client import call_llm

class CoverageEntry(BaseModel):
    criterion_id: str
    status: Literal["Covered", "Partially covered", "Not covered", "Unable to determine"]
    evidence: list[str]
    explanation: str

class CoverageMatrix(RootModel[list[CoverageEntry]]):
    pass

SYSTEM_PROMPT = """You are a software quality analysis agent. For each acceptance criterion,
decide whether the provided test metadata demonstrates it is Covered, Partially covered,
Not covered, or Unable to determine. Only cite evidence (file path + test name) that appears
in the provided metadata — never invent file paths or test names. If genuinely ambiguous,
use "Unable to determine" rather than guessing."""

async def coverage_analyzer(state: dict) -> dict:
    criteria = state["requirement"]["acceptance_criteria"]
    metadata_text = "\n".join(f"{path}: {tests}" for path, tests in state["test_metadata"].items()) or "(no test metadata extracted)"
    user_prompt = f"Acceptance criteria:\n{criteria}\n\nTest metadata:\n{metadata_text}"
    result: CoverageMatrix = await call_llm(SYSTEM_PROMPT, user_prompt, CoverageMatrix, tool_name="classify_coverage")
    state["coverage_matrix"] = [entry.model_dump() for entry in result.root]

    if not state["test_metadata"] and state["candidate_files"]:
        state.setdefault("warnings", []).append(
            "No supported test framework detected; results may be incomplete."
        )
    return state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend/worker && python -m pytest tests/test_coverage_analyzer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/worker/app/nodes/coverage_analyzer.py backend/worker/tests/test_coverage_analyzer.py
git commit -m "feat(worker): add Coverage Analyzer node"
```

### Task 15: Test Plan Generator + Missing-Test Recommender nodes

**Files:**
- Create: `backend/worker/app/nodes/test_plan_generator.py`
- Create: `backend/worker/app/nodes/missing_test_recommender.py`
- Test: `backend/worker/tests/test_test_plan_generator.py`, `test_missing_test_recommender.py`

**Interfaces:**
- Consumes: `state["requirement"]`, `state["coverage_matrix"]` (Task 14), `call_llm` (Task 12).
- Produces: `class TestCase(BaseModel)` (`id, title, requirement_id, preconditions: list[str], steps: list[str], test_data: str, expected_result: str, type: Literal[...9 categories from spec §4...], priority: Literal["low","medium","high"], automation_recommendation: str`). `async def test_plan_generator(state: AgentState) -> AgentState` sets `state["test_plan"]: list[dict]`.
- Produces: `class MissingTest(BaseModel)` (`behavior: str, why_it_matters: str, suggested_type: str, suggested_priority: Literal["low","medium","high"], related_criterion_id: str, risk: str`). `async def missing_test_recommender(state: AgentState) -> AgentState` sets `state["missing_tests"]: list[dict]`.

- [ ] **Step 1: Write failing tests**

```python
# backend/worker/tests/test_test_plan_generator.py
import pytest
from unittest.mock import AsyncMock, patch
from app.nodes.test_plan_generator import test_plan_generator, TestCase, TestPlan

@pytest.mark.asyncio
async def test_generates_scenarios_across_categories():
    state = {"requirement": {"acceptance_criteria": [{"id": "AC1", "text": "Invalid password returns 401"}]},
              "coverage_matrix": [], "tool_call_trace": [], "warnings": []}
    stub = TestPlan(root=[TestCase(id="TC1", title="Reject invalid password", requirement_id="AC1",
                                    preconditions=["user exists"], steps=["POST /api/login with wrong password"],
                                    test_data="password=wrong", expected_result="401 response",
                                    type="negative", priority="high", automation_recommendation="automate via pytest")])
    with patch("app.nodes.test_plan_generator.call_llm", new=AsyncMock(return_value=stub)):
        result = await test_plan_generator(state)
    assert result["test_plan"][0]["type"] == "negative"
```

```python
# backend/worker/tests/test_missing_test_recommender.py
import pytest
from unittest.mock import AsyncMock, patch
from app.nodes.missing_test_recommender import missing_test_recommender, MissingTest, MissingTests

@pytest.mark.asyncio
async def test_recommends_missing_scenarios_for_gaps():
    state = {"requirement": {"acceptance_criteria": [{"id": "AC1", "text": "x"}]},
              "coverage_matrix": [{"criterion_id": "AC1", "status": "Not covered"}],
              "tool_call_trace": [], "warnings": []}
    stub = MissingTests(root=[MissingTest(behavior="401 on invalid password", why_it_matters="security boundary",
                                           suggested_type="negative", suggested_priority="high",
                                           related_criterion_id="AC1", risk="unauthorized access if unverified")])
    with patch("app.nodes.missing_test_recommender.call_llm", new=AsyncMock(return_value=stub)):
        result = await missing_test_recommender(state)
    assert result["missing_tests"][0]["related_criterion_id"] == "AC1"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/worker && python -m pytest tests/test_test_plan_generator.py tests/test_missing_test_recommender.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# backend/worker/app/nodes/test_plan_generator.py
from typing import Literal
from pydantic import BaseModel, RootModel
from app.llm_client import call_llm

TEST_TYPES = Literal["positive", "negative", "validation", "boundary-value", "permission",
                      "api", "ui", "integration", "error-handling", "regression"]

class TestCase(BaseModel):
    id: str
    title: str
    requirement_id: str
    preconditions: list[str]
    steps: list[str]
    test_data: str
    expected_result: str
    type: TEST_TYPES
    priority: Literal["low", "medium", "high"]
    automation_recommendation: str

class TestPlan(RootModel[list[TestCase]]):
    pass

SYSTEM_PROMPT = """You are a software quality analysis agent. Generate a full test plan covering
positive, negative, validation, boundary-value, permission, API, UI, integration, error-handling,
and regression scenarios for the given requirement. Every test case must reference a real
acceptance criterion id."""

async def test_plan_generator(state: dict) -> dict:
    user_prompt = f"Requirement:\n{state['requirement']}\n\nCurrent coverage:\n{state['coverage_matrix']}"
    result: TestPlan = await call_llm(SYSTEM_PROMPT, user_prompt, TestPlan, tool_name="generate_test_plan")
    state["test_plan"] = [tc.model_dump() for tc in result.root]
    return state
```

```python
# backend/worker/app/nodes/missing_test_recommender.py
from typing import Literal
from pydantic import BaseModel, RootModel
from app.llm_client import call_llm

class MissingTest(BaseModel):
    behavior: str
    why_it_matters: str
    suggested_type: str
    suggested_priority: Literal["low", "medium", "high"]
    related_criterion_id: str
    risk: str

class MissingTests(RootModel[list[MissingTest]]):
    pass

SYSTEM_PROMPT = """You are a software quality analysis agent. For every criterion marked
Not covered or Partially covered, recommend the missing test(s): what behavior is untested,
why it matters, suggested type/priority, the related criterion id, and the risk of leaving it
untested. Do not recommend tests for criteria already marked Covered."""

async def missing_test_recommender(state: dict) -> dict:
    gaps = [c for c in state["coverage_matrix"] if c["status"] in ("Not covered", "Partially covered")]
    result: MissingTests = await call_llm(SYSTEM_PROMPT, f"Gaps:\n{gaps}", MissingTests, tool_name="recommend_missing_tests")
    state["missing_tests"] = [m.model_dump() for m in result.root]
    return state
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend/worker && python -m pytest tests/test_test_plan_generator.py tests/test_missing_test_recommender.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/worker/app/nodes/test_plan_generator.py backend/worker/app/nodes/missing_test_recommender.py backend/worker/tests/test_test_plan_generator.py backend/worker/tests/test_missing_test_recommender.py
git commit -m "feat(worker): add Test Plan Generator and Missing-Test Recommender nodes"
```

### Task 16: Quality Validator node

**Files:**
- Create: `backend/worker/app/nodes/quality_validator.py`
- Test: `backend/worker/tests/test_quality_validator.py`

**Interfaces:**
- Consumes: `state["coverage_matrix"]`, `state["requirement"]["acceptance_criteria"]`, `state["candidate_files"]` (Tasks 12–14). Pure/deterministic — no LLM call.
- Produces: `def quality_validator(state: AgentState) -> AgentState` — for each `coverage_matrix` entry, strips any `evidence` string whose file path isn't in `state["candidate_files"]`'s paths, appending a warning per stripped item; does not call the network or an LLM (cheap, synchronous, always runs).

- [ ] **Step 1: Write the failing test**

```python
# backend/worker/tests/test_quality_validator.py
from app.nodes.quality_validator import quality_validator

def test_strips_fabricated_evidence_not_in_candidate_files():
    state = {
        "candidate_files": [{"path": "tests/test_login.py"}],
        "coverage_matrix": [
            {"criterion_id": "AC1", "status": "Covered",
             "evidence": ["tests/test_login.py::test_x", "tests/nonexistent.py::test_fake"],
             "explanation": "..."},
        ],
        "warnings": [],
    }
    result = quality_validator(state)
    evidence = result["coverage_matrix"][0]["evidence"]
    assert "tests/nonexistent.py::test_fake" not in evidence
    assert "tests/test_login.py::test_x" in evidence
    assert any("fabricated" in w.lower() or "nonexistent.py" in w for w in result["warnings"])

def test_leaves_valid_evidence_untouched():
    state = {
        "candidate_files": [{"path": "tests/test_login.py"}],
        "coverage_matrix": [{"criterion_id": "AC1", "status": "Covered",
                              "evidence": ["tests/test_login.py::test_x"], "explanation": "..."}],
        "warnings": [],
    }
    result = quality_validator(state)
    assert result["coverage_matrix"][0]["evidence"] == ["tests/test_login.py::test_x"]
    assert result["warnings"] == []
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/worker && python -m pytest tests/test_quality_validator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# backend/worker/app/nodes/quality_validator.py
def quality_validator(state: dict) -> dict:
    known_paths = {f["path"] for f in state.get("candidate_files", [])}
    for entry in state.get("coverage_matrix", []):
        kept, dropped = [], []
        for item in entry.get("evidence", []):
            path = item.split("::")[0]
            (kept if path in known_paths else dropped).append(item)
        entry["evidence"] = kept
        for item in dropped:
            state.setdefault("warnings", []).append(f"Dropped fabricated evidence reference: {item}")
    return state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend/worker && python -m pytest tests/test_quality_validator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/worker/app/nodes/quality_validator.py backend/worker/tests/test_quality_validator.py
git commit -m "feat(worker): add Quality Validator node (strips fabricated evidence)"
```

### Task 17: Report Saver + Cleanup, overall timeout, full graph wiring, worker E2E test

**Files:**
- Create: `backend/worker/app/nodes/report_saver.py`
- Create: `backend/worker/app/graph.py`
- Create: `backend/worker/app/runner.py`
- Modify: `backend/worker/app/main.py` (wire `run_analysis` into the poll loop from Task 10)
- Modify: `backend/worker/app/health.py` (extend `/health/ready` to check SQS reachability)
- Test: `backend/worker/tests/test_report_saver.py`, `test_runner_e2e.py`

**Interfaces:**
- Consumes: all node functions from Tasks 10–16; `call_test_mcp_tool` (Task 11); `AgentState` shape (Task 10).
- Produces: `async def report_saver(state: AgentState) -> AgentState` — calls MCP `save_coverage_report`, sets `state["status"]="completed"` on success or leaves `status` as-is and appends a warning + sets `storage_status="failed"` if the save call raises (non-fatal, per spec §13).
- Produces: `def build_graph() -> CompiledStateGraph` in `graph.py` — LangGraph `StateGraph(AgentState)` wiring nodes 1–12 in the exact order from spec §4 table, with conditional edges: after `request_validator` and `requirement_parser`, route to `END` if `state["status"] == "failed"`, else continue.
- Produces: `async def run_analysis(analysis_id: str, repository: str, issue_number: int, notes: str | None) -> None` in `runner.py` — builds the initial `AgentState`, calls `job_intake` first (outside the graph, since it must run even before the graph is invoked), then `asyncio.wait_for(graph.ainvoke(state), timeout=600)`, and in a `finally` block calls MCP `cleanup_workspace` and does a final `AnalysisStore.upsert` reflecting terminal `status` (this is the "Cleanup" node from spec §4, implemented as a wrapper rather than a graph node so it still runs on timeout/exception). Consumed by `main.py`'s poll loop.

- [ ] **Step 1: Write the failing test for `report_saver`**

```python
# backend/worker/tests/test_report_saver.py
import pytest
from unittest.mock import AsyncMock, patch
from app.nodes.report_saver import report_saver

@pytest.mark.asyncio
async def test_marks_completed_on_successful_save():
    state = {"analysis_id": "a1", "repository": "acme/widgets", "issue_number": 42,
              "requirement": {"feature_name": "Login"}, "coverage_matrix": [], "missing_tests": [],
              "test_plan": [], "tool_call_trace": [], "warnings": [], "status": "running"}
    with patch("app.nodes.report_saver.call_test_mcp_tool", new=AsyncMock(return_value={"s3_report_key": "k", "dynamodb_status": "saved"})):
        result = await report_saver(state)
    assert result["status"] == "completed"

@pytest.mark.asyncio
async def test_save_failure_is_non_fatal():
    state = {"analysis_id": "a1", "repository": "acme/widgets", "issue_number": 42,
              "requirement": {"feature_name": "Login"}, "coverage_matrix": [], "missing_tests": [],
              "test_plan": [], "tool_call_trace": [], "warnings": [], "status": "running"}
    with patch("app.nodes.report_saver.call_test_mcp_tool", new=AsyncMock(side_effect=Exception("S3 down"))):
        result = await report_saver(state)
    assert result["status"] == "completed"  # analysis itself still succeeded
    assert result.get("storage_status") == "failed"
    assert any("s3" in w.lower() or "save" in w.lower() for w in result["warnings"])
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/worker && python -m pytest tests/test_report_saver.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `report_saver.py`**

```python
# backend/worker/app/nodes/report_saver.py
from app.mcp_clients import call_test_mcp_tool

async def report_saver(state: dict) -> dict:
    state["status"] = "completed"
    try:
        await call_test_mcp_tool(
            "save_coverage_report", analysis_id=state["analysis_id"], repository=state["repository"],
            issue_number=state["issue_number"], requirement=state["requirement"],
            coverage_matrix=state["coverage_matrix"], missing_tests=state["missing_tests"],
            test_plan=state["test_plan"], status=state["status"], tool_call_trace=state.get("tool_call_trace", []),
        )
        state["storage_status"] = "saved"
    except Exception as exc:
        state["storage_status"] = "failed"
        state.setdefault("warnings", []).append(f"Report save failed: {exc}")
    return state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend/worker && python -m pytest tests/test_report_saver.py -v`
Expected: PASS

- [ ] **Step 5: Implement `graph.py`, `runner.py`, and wire `main.py`/`health.py`**

```python
# backend/worker/app/graph.py
from langgraph.graph import StateGraph, END
from app.state import AgentState
from app.nodes.job_intake import job_intake  # not added as a graph node — see runner.py
from app.nodes.request_validator import request_validator
from app.nodes.requirement_retriever import requirement_retriever
from app.nodes.requirement_parser import requirement_parser
from app.nodes.test_search_planner import test_search_planner
from app.nodes.test_file_retriever import test_file_retriever
from app.nodes.test_file_classifier import test_file_classifier
from app.nodes.coverage_analyzer import coverage_analyzer
from app.nodes.test_plan_generator import test_plan_generator
from app.nodes.missing_test_recommender import missing_test_recommender
from app.nodes.quality_validator import quality_validator
from app.nodes.report_saver import report_saver

def _failed_or_continue(state: AgentState) -> str:
    return "end" if state.get("status") == "failed" else "continue"

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("request_validator", request_validator)
    graph.add_node("requirement_retriever", requirement_retriever)
    graph.add_node("requirement_parser", requirement_parser)
    graph.add_node("test_search_planner", test_search_planner)
    graph.add_node("test_file_retriever", test_file_retriever)
    graph.add_node("test_file_classifier", test_file_classifier)
    graph.add_node("coverage_analyzer", coverage_analyzer)
    graph.add_node("test_plan_generator", test_plan_generator)
    graph.add_node("missing_test_recommender", missing_test_recommender)
    graph.add_node("quality_validator", quality_validator)
    graph.add_node("report_saver", report_saver)

    graph.set_entry_point("request_validator")
    graph.add_conditional_edges("request_validator", _failed_or_continue, {"end": END, "continue": "requirement_retriever"})
    graph.add_edge("requirement_retriever", "requirement_parser")
    graph.add_conditional_edges("requirement_parser", _failed_or_continue, {"end": END, "continue": "test_search_planner"})
    graph.add_edge("test_search_planner", "test_file_retriever")
    graph.add_edge("test_file_retriever", "test_file_classifier")
    graph.add_edge("test_file_classifier", "coverage_analyzer")
    graph.add_edge("coverage_analyzer", "test_plan_generator")
    graph.add_edge("test_plan_generator", "missing_test_recommender")
    graph.add_edge("missing_test_recommender", "quality_validator")
    graph.add_edge("quality_validator", "report_saver")
    graph.add_edge("report_saver", END)
    return graph.compile()
```

```python
# backend/worker/app/runner.py
import asyncio
from datetime import datetime, timezone
from config import get_settings
from dynamodb import AnalysisStore
from models import AnalysisRecord
from app.nodes.job_intake import job_intake
from app.graph import build_graph
from app.mcp_clients import call_test_mcp_tool

_graph = build_graph()

async def run_analysis(analysis_id: str, repository: str, issue_number: int, notes: str | None) -> None:
    store = AnalysisStore(table_name=get_settings().dynamodb_table)
    state = {
        "analysis_id": analysis_id, "repository": repository, "issue_number": issue_number,
        "notes": notes, "tool_call_trace": [], "warnings": [], "status": "pending",
    }
    state = job_intake(state, store)
    try:
        state = await asyncio.wait_for(_graph.ainvoke(state), timeout=600)
    except asyncio.TimeoutError:
        state["status"] = "failed"
        state["error_message"] = "analysis timed out"
    except Exception as exc:
        state["status"] = "failed"
        state["error_message"] = str(exc)
    finally:
        try:
            await call_test_mcp_tool("cleanup_workspace", analysis_id=analysis_id)
        except Exception:
            pass
        now = datetime.now(timezone.utc).isoformat()
        store.upsert(AnalysisRecord(
            analysis_id=analysis_id, repository=repository, issue_number=issue_number,
            status=state.get("status", "failed"), created_at=now, updated_at=now,
            requirement_summary=state.get("requirement", {}).get("feature_name"),
            error_message=state.get("error_message"), storage_status=state.get("storage_status"),
            missing_tests_count=len(state.get("missing_tests", [])),
            tool_call_trace=state.get("tool_call_trace", []),
        ))
```

```python
# backend/worker/app/main.py (replace the placeholder loop from Task 10)
import asyncio
import time
from config import get_settings
from sqs import JobQueue
from app.health import start_health_server
from app.runner import run_analysis

def poll_forever() -> None:
    settings = get_settings()
    queue = JobQueue(settings.sqs_queue_url)
    start_health_server()
    while True:
        jobs = queue.receive_jobs(max_messages=1, wait_seconds=20)
        for job in jobs:
            asyncio.run(run_analysis(**job["body"]))
            queue.delete_message(job["receipt_handle"])
        if not jobs:
            time.sleep(1)

if __name__ == "__main__":
    poll_forever()
```

Update `/health/ready` in `health.py` to attempt `JobQueue(get_settings().sqs_queue_url)._client.get_queue_attributes(...)` and return `503` on failure — same pattern as Task 19's API readiness check (kept in sync during Task 19).

- [ ] **Step 6: Write the failing worker end-to-end test — stub LLM, real local MCP transport, fixture repo**

```python
# backend/worker/tests/test_runner_e2e.py
import subprocess
import sys
import time
from pathlib import Path
import boto3
import pytest
from moto import mock_aws
from unittest.mock import AsyncMock, patch
from app.runner import run_analysis
from dynamodb import AnalysisStore

@pytest.fixture
def full_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DYNAMODB_TABLE", "testscope-analyses-test")
    monkeypatch.setenv("S3_BUCKET", "testscope-reports-test")
    monkeypatch.setenv("SQS_QUEUE_URL", "unused-in-this-test")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "http://localhost:8198/mcp")
    monkeypatch.setenv("MCP_GITHUB_URL", "http://localhost:8197/mcp")  # stub, see step 7 note
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path / "workspace_root"))
    monkeypatch.setenv("GITHUB_TOKEN", "unused")
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="testscope-analyses-test", KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "analysis_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="testscope-reports-test")
        yield

@pytest.mark.asyncio
async def test_full_pipeline_reaches_completed_status(full_env):
    # LLM calls are stubbed end-to-end (no real Claude call); MCP calls hit the real
    # mcp-server subprocess started in Step 7, which itself hits moto-mocked AWS.
    stub_llm_by_tool = {
        "extract_requirement": {"feature_name": "Login", "business_objective": "auth", "functional_requirements": [],
                                 "acceptance_criteria": [{"id": "AC1", "text": "Invalid password returns 401"}],
                                 "validation_rules": [], "user_roles": [], "constraints": [], "gaps": []},
        "generate_keywords": {"keywords": ["login"]},
        "classify_coverage": [{"criterion_id": "AC1", "status": "Not covered", "evidence": [], "explanation": "no matching test"}],
        "generate_test_plan": [],
        "recommend_missing_tests": [{"behavior": "401 on bad password", "why_it_matters": "security",
                                       "suggested_type": "negative", "suggested_priority": "high",
                                       "related_criterion_id": "AC1", "risk": "unauthorized access"}],
    }
    async def fake_call_llm(system_prompt, user_prompt, response_model, tool_name):
        return response_model.model_validate(stub_llm_by_tool[tool_name])

    async def fake_call_github_tool(tool_name, **kwargs):
        if tool_name == "get_repository":
            return {"default_branch": "main"}
        if tool_name == "get_issue":
            return {"body": "Users must be rejected with 401 on invalid password."}
        if tool_name == "get_issue_comments":
            return {"comments": []}
        raise ValueError(tool_name)

    with patch("app.llm_client.call_llm", new=AsyncMock(side_effect=fake_call_llm)), \
         patch("app.mcp_clients.call_github_tool", new=AsyncMock(side_effect=fake_call_github_tool)):
        await run_analysis(analysis_id="e2e-1", repository="acme/widgets", issue_number=42, notes=None)

    store = AnalysisStore(table_name="testscope-analyses-test")
    record = store.get("e2e-1")
    assert record.status == "completed"
    assert record.missing_tests_count == 1
```

- [ ] **Step 7: Add a `conftest.py` that starts a real `mcp-test-analysis` subprocess for this test session**

```python
# backend/worker/tests/conftest.py
import subprocess
import sys
import time
from pathlib import Path
import pytest

@pytest.fixture(scope="session", autouse=True)
def mcp_test_analysis_server():
    mcp_server_dir = Path(__file__).parent.parent.parent.parent / "mcp-server"
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=str(mcp_server_dir),
        env={**__import__("os").environ, "MCP_PORT": "8198", "DYNAMODB_TABLE": "testscope-analyses-test",
             "S3_BUCKET": "testscope-reports-test", "GITHUB_TOKEN": "unused",
             "MCP_GITHUB_URL": "http://localhost:8197/mcp", "WORKSPACE_ROOT": "/tmp/testscope-e2e-workspace"},
    )
    time.sleep(1.0)
    yield
    proc.terminate()
    proc.wait(timeout=5)
```

Because `find_test_files` calls out to `mcp-github` for the pre-clone size check, and this end-to-end test doesn't stand up a real `mcp-github`, the search step will raise — which is acceptable here since the assertions only need `test_file_retriever` to fail gracefully into an empty `candidate_files` list, not succeed. Adjust `test_file_retriever` (Task 13) to catch exceptions from `call_test_mcp_tool("find_test_files", ...)`, append a warning, and continue with `candidate_files=[]` rather than propagating — add this as a regression test in `test_test_file_retriever.py` (`test_search_failure_is_non_fatal`) before proceeding.

- [ ] **Step 8: Run to verify failure, then run for real**

Run: `cd backend/worker && python -m pytest tests/test_runner_e2e.py -v`
Expected: after Steps 5–7's implementation, PASS

- [ ] **Step 9: Run the full worker test suite and check coverage**

Run: `cd backend/worker && python -m pytest --cov=app --cov-report=term-missing`
Expected: all PASS, ≥80% coverage on `app/`

- [ ] **Step 10: Commit**

```bash
git add backend/worker/app backend/worker/tests
git commit -m "feat(worker): wire full LangGraph agent (Report Saver, Cleanup, 10-min timeout, graph assembly) and add worker E2E test"
```

- [ ] **Step 11: Add `backend/worker/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY ../shared /shared
RUN pip install --no-cache-dir -e /shared && pip install --no-cache-dir .
COPY . .
EXPOSE 8080
CMD ["python", "app/main.py"]
```

- [ ] **Step 12: Commit Dockerfile**

```bash
git add backend/worker/Dockerfile
git commit -m "build(worker): add Dockerfile"
```

---

## Phase 4 — `backend/api` (FastAPI)

`backend/api` also depends on `backend/shared` as a path dependency (`pip install -e ../shared`, added to `backend/api/pyproject.toml`).

### Task 18: API skeleton — app factory, schemas, health endpoints

**Files:**
- Create: `backend/api/app/schemas.py`
- Create: `backend/api/app/routes/__init__.py`
- Create: `backend/api/app/routes/health.py`
- Create: `backend/api/app/main.py`
- Test: `backend/api/tests/test_health.py`

**Interfaces:**
- Produces: `class CreateAnalysisRequest(BaseModel)` (`repository: str, issue_number: int, notes: str | None = None`), `class CreateAnalysisResponse(BaseModel)` (`analysis_id: str, status: str`), `class AnalysisStatusResponse(BaseModel)` (mirrors `AnalysisRecord` minus `tool_call_trace`), `class AnalysisListResponse(BaseModel)` (`analyses: list[AnalysisStatusResponse], next_cursor: str | None`), `class ReportResponse(BaseModel)` (`analysis_id: str, requirement: dict, coverage_matrix: list[dict], test_plan: list[dict], missing_tests: list[dict], tool_call_trace: list[dict], download_url: str`), `class GithubIssueResponse(BaseModel)` (`github_issue_url: str`) — all in `schemas.py`, consumed by Tasks 19–22.
- Produces: `def create_app() -> FastAPI` in `main.py`, registering routers; consumed by `uvicorn app.main:app` and by every route task's `TestClient(create_app())` tests.

- [ ] **Step 1: Write the failing test**

```python
# backend/api/tests/test_health.py
from fastapi.testclient import TestClient
from app.main import create_app

def test_health_live_returns_ok():
    client = TestClient(create_app())
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_health_ready_returns_ok(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "t")
    monkeypatch.setenv("S3_BUCKET", "b")
    monkeypatch.setenv("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/000/q")
    monkeypatch.setenv("MCP_GITHUB_URL", "http://mcp-github")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "http://mcp-test-analysis")
    client = TestClient(create_app())
    response = client.get("/health/ready")
    assert response.status_code == 200
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/api && python -m pytest tests/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# backend/api/app/schemas.py
from pydantic import BaseModel

class CreateAnalysisRequest(BaseModel):
    repository: str
    issue_number: int
    notes: str | None = None

class CreateAnalysisResponse(BaseModel):
    analysis_id: str
    status: str

class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    repository: str
    issue_number: int
    status: str
    created_at: str
    updated_at: str
    requirement_summary: str | None = None
    coverage_summary: dict | None = None
    missing_tests_count: int = 0
    error_message: str | None = None
    storage_status: str | None = None
    github_issue_url: str | None = None

class AnalysisListResponse(BaseModel):
    analyses: list[AnalysisStatusResponse]
    next_cursor: str | None = None

class ReportResponse(BaseModel):
    analysis_id: str
    requirement: dict
    coverage_matrix: list[dict]
    test_plan: list[dict]
    missing_tests: list[dict]
    tool_call_trace: list[dict]
    download_url: str

class GithubIssueResponse(BaseModel):
    github_issue_url: str
```

```python
# backend/api/app/routes/health.py
from fastapi import APIRouter
from config import get_settings

router = APIRouter()

@router.get("/health/live")
def live():
    return {"status": "ok"}

@router.get("/health/ready")
def ready():
    get_settings()  # raises if required env vars are missing
    return {"status": "ok"}
```

```python
# backend/api/app/main.py
from fastapi import FastAPI
from app.routes import health

def create_app() -> FastAPI:
    app = FastAPI(title="TestScope AI API")
    app.include_router(health.router)
    return app

app = create_app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend/api && python -m pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/app backend/api/tests/test_health.py
git commit -m "feat(api): add app factory, schemas, health endpoints"
```

### Task 19: `POST /api/analyses`

**Files:**
- Create: `backend/api/app/routes/analyses.py`
- Modify: `backend/api/app/main.py` (register `analyses.router`)
- Test: `backend/api/tests/test_create_analysis.py`

**Interfaces:**
- Consumes: `AnalysisStore`, `JobQueue`, `AnalysisRecord` (Task 9), `CreateAnalysisRequest`/`CreateAnalysisResponse` (Task 18).
- Produces: `router = APIRouter(prefix="/api/analyses")` with `POST ""` handler, consumed (extended) by Tasks 20–22 in the same file.

- [ ] **Step 1: Write the failing test**

```python
# backend/api/tests/test_create_analysis.py
import boto3
import pytest
from moto import mock_aws
from fastapi.testclient import TestClient

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DYNAMODB_TABLE", "testscope-analyses-test")
    monkeypatch.setenv("S3_BUCKET", "testscope-reports-test")
    monkeypatch.setenv("SQS_QUEUE_URL", "https://queue.amazonaws.com/123/q")
    monkeypatch.setenv("MCP_GITHUB_URL", "http://mcp-github")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "http://mcp-test-analysis")
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="testscope-analyses-test", KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "analysis_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        sqs = boto3.client("sqs", region_name="us-east-1")
        sqs.create_queue(QueueName="q")
        from app.main import create_app
        yield TestClient(create_app())

def test_create_analysis_returns_202_and_enqueues(client):
    response = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert "analysis_id" in body

def test_create_analysis_does_not_dedupe_concurrent_requests(client):
    r1 = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42})
    r2 = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42})
    assert r1.json()["analysis_id"] != r2.json()["analysis_id"]  # stated v1 limitation, spec §7
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/api && python -m pytest tests/test_create_analysis.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# backend/api/app/routes/analyses.py
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, status
from config import get_settings
from dynamodb import AnalysisStore
from sqs import JobQueue
from models import AnalysisRecord
from app.schemas import CreateAnalysisRequest, CreateAnalysisResponse

router = APIRouter(prefix="/api/analyses")

def _store() -> AnalysisStore:
    return AnalysisStore(table_name=get_settings().dynamodb_table)

def _queue() -> JobQueue:
    return JobQueue(get_settings().sqs_queue_url)

@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=CreateAnalysisResponse)
def create_analysis(payload: CreateAnalysisRequest):
    analysis_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    _store().upsert(AnalysisRecord(
        analysis_id=analysis_id, repository=payload.repository, issue_number=payload.issue_number,
        status="pending", created_at=now, updated_at=now,
    ))
    _queue().send_job(analysis_id, payload.repository, payload.issue_number, payload.notes)
    return CreateAnalysisResponse(analysis_id=analysis_id, status="pending")
```

```python
# backend/api/app/main.py (add analyses router)
from fastapi import FastAPI
from app.routes import health, analyses

def create_app() -> FastAPI:
    app = FastAPI(title="TestScope AI API")
    app.include_router(health.router)
    app.include_router(analyses.router)
    return app

app = create_app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend/api && python -m pytest tests/test_create_analysis.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/app/routes/analyses.py backend/api/app/main.py backend/api/tests/test_create_analysis.py
git commit -m "feat(api): add POST /api/analyses (enqueue, no dedup per v1 scope)"
```

### Task 20: `GET /api/analyses/{id}` and `GET /api/analyses`

**Files:**
- Modify: `backend/api/app/routes/analyses.py` (add two handlers to the existing `router`)
- Test: `backend/api/tests/test_get_and_list_analyses.py`

**Interfaces:**
- Consumes: `AnalysisStore.get`/`query_by_repo_issue`/`list_recent` (Task 9), `_store()` helper (Task 19).
- Produces: `GET /api/analyses/{analysis_id} -> AnalysisStatusResponse` (404 if missing); `GET /api/analyses?repository=&issue_number=&limit=&cursor= -> AnalysisListResponse`.

- [ ] **Step 1: Write the failing test**

```python
# backend/api/tests/test_get_and_list_analyses.py
# Reuses the `client` fixture pattern from test_create_analysis.py — copy the fixture verbatim into this file.
def test_get_returns_404_for_unknown_id(client):
    response = client.get("/api/analyses/does-not-exist")
    assert response.status_code == 404

def test_get_returns_created_analysis(client):
    created = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42}).json()
    response = client.get(f"/api/analyses/{created['analysis_id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

def test_list_returns_recent_analyses(client):
    client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 1})
    client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 2})
    response = client.get("/api/analyses?limit=10")
    assert response.status_code == 200
    assert len(response.json()["analyses"]) == 2
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/api && python -m pytest tests/test_get_and_list_analyses.py -v`
Expected: FAIL — `404` route not found (endpoints don't exist yet)

- [ ] **Step 3: Implement (append to `analyses.py`)**

```python
# backend/api/app/routes/analyses.py — append below create_analysis
from fastapi import HTTPException
from app.schemas import AnalysisStatusResponse, AnalysisListResponse

def _to_status_response(record) -> AnalysisStatusResponse:
    return AnalysisStatusResponse(**record.model_dump(exclude={"tool_call_trace", "user_feedback"}))

@router.get("/{analysis_id}", response_model=AnalysisStatusResponse)
def get_analysis(analysis_id: str):
    record = _store().get(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _to_status_response(record)

@router.get("", response_model=AnalysisListResponse)
def list_analyses(repository: str | None = None, issue_number: int | None = None,
                   limit: int = 20, cursor: str | None = None):
    if repository and issue_number is not None:
        records = _store().query_by_repo_issue(repository, issue_number)
        return AnalysisListResponse(analyses=[_to_status_response(r) for r in records], next_cursor=None)
    records, next_cursor = _store().list_recent(limit=limit, cursor=cursor)
    return AnalysisListResponse(analyses=[_to_status_response(r) for r in records], next_cursor=next_cursor)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend/api && python -m pytest tests/test_get_and_list_analyses.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/app/routes/analyses.py backend/api/tests/test_get_and_list_analyses.py
git commit -m "feat(api): add GET /api/analyses/{id} and GET /api/analyses"
```

### Task 21: `GET /api/analyses/{id}/report`

**Files:**
- Modify: `backend/api/app/routes/analyses.py`
- Test: `backend/api/tests/test_get_report.py`

**Interfaces:**
- Consumes: `ReportStore.presigned_url`/`.read_json` (Task 9), `ReportResponse` (Task 18).
- Produces: `GET /api/analyses/{analysis_id}/report -> ReportResponse` (409 if `status != "completed"`, 404 if the analysis itself doesn't exist).

- [ ] **Step 1: Write the failing test**

```python
# backend/api/tests/test_get_report.py
import json
import boto3
# Reuses the `client` fixture — copy verbatim from test_create_analysis.py, and additionally
# create the S3 bucket inside the fixture (`s3.create_bucket(Bucket="testscope-reports-test")`).

def test_returns_409_when_not_completed(client):
    created = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42}).json()
    response = client.get(f"/api/analyses/{created['analysis_id']}/report")
    assert response.status_code == 409

def test_returns_report_when_completed(client):
    created = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42}).json()
    analysis_id = created["analysis_id"]
    s3_key = f"acme/widgets/42/{analysis_id}.json"
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(Bucket="testscope-reports-test", Key=s3_key, Body=json.dumps({
        "requirement": {"feature_name": "Login"}, "coverage_matrix": [], "test_plan": [],
        "missing_tests": [], "tool_call_trace": [],
    }).encode())
    ddb = boto3.resource("dynamodb", region_name="us-east-1").Table("testscope-analyses-test")
    ddb.update_item(Key={"analysis_id": analysis_id},
                     UpdateExpression="SET #s = :s, s3_report_key = :k",
                     ExpressionAttributeNames={"#s": "status"},
                     ExpressionAttributeValues={":s": "completed", ":k": s3_key})
    response = client.get(f"/api/analyses/{analysis_id}/report")
    assert response.status_code == 200
    body = response.json()
    assert body["requirement"]["feature_name"] == "Login"
    assert body["download_url"].startswith("https://")
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/api && python -m pytest tests/test_get_report.py -v`
Expected: FAIL — `404` route not found

- [ ] **Step 3: Implement (append to `analyses.py`)**

```python
# backend/api/app/routes/analyses.py — append
from s3 import ReportStore
from app.schemas import ReportResponse

def _report_store() -> ReportStore:
    return ReportStore(bucket=get_settings().s3_bucket)

@router.get("/{analysis_id}/report", response_model=ReportResponse)
def get_report(analysis_id: str):
    record = _store().get(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if record.status != "completed":
        raise HTTPException(status_code=409, detail=f"Analysis is {record.status}, report not ready")
    report_store = _report_store()
    data = report_store.read_json(record.s3_report_key)
    return ReportResponse(
        analysis_id=analysis_id, requirement=data["requirement"], coverage_matrix=data["coverage_matrix"],
        test_plan=data["test_plan"], missing_tests=data["missing_tests"], tool_call_trace=data["tool_call_trace"],
        download_url=report_store.presigned_url(record.s3_report_key.replace(".json", ".md")),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend/api && python -m pytest tests/test_get_report.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/app/routes/analyses.py backend/api/tests/test_get_report.py
git commit -m "feat(api): add GET /api/analyses/{id}/report"
```

### Task 22: `POST /api/analyses/{id}/github-issue`

**Files:**
- Modify: `backend/api/app/routes/analyses.py`
- Create: `backend/api/app/mcp_client.py`
- Test: `backend/api/tests/test_create_github_issue.py`

**Interfaces:**
- Consumes: `AnalysisStore.get` (Task 9), `GithubIssueResponse` (Task 18).
- Produces: `async def call_github_tool(tool_name: str, **kwargs) -> dict` in `backend/api/app/mcp_client.py` — same shape/behavior as the worker's version (Task 11), independently implemented since `api` and `worker` are separate deployables with separate Dockerfiles; both call the same `mcp-github` MCP server contract. `POST /api/analyses/{analysis_id}/github-issue -> GithubIssueResponse` (409 if `status != "completed"`; requires the caller to have already reviewed the report — this endpoint is the only place `create_issue` is ever called, matching spec §5.2's "never from the automated workflow").

- [ ] **Step 1: Write the failing test**

```python
# backend/api/tests/test_create_github_issue.py
from unittest.mock import AsyncMock, patch
# Reuses the `client` fixture from test_create_analysis.py (with S3 bucket added, per test_get_report.py)

def test_returns_409_when_not_completed(client):
    created = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42}).json()
    response = client.post(f"/api/analyses/{created['analysis_id']}/github-issue")
    assert response.status_code == 409

def test_creates_issue_when_completed(client):
    import boto3, json
    created = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42}).json()
    analysis_id = created["analysis_id"]
    s3_key = f"acme/widgets/42/{analysis_id}.json"
    boto3.client("s3", region_name="us-east-1").put_object(
        Bucket="testscope-reports-test", Key=s3_key,
        Body=json.dumps({"missing_tests": [{"behavior": "401 on bad password"}]}).encode(),
    )
    ddb = boto3.resource("dynamodb", region_name="us-east-1").Table("testscope-analyses-test")
    ddb.update_item(Key={"analysis_id": analysis_id}, UpdateExpression="SET #s = :s, s3_report_key = :k",
                     ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":s": "completed", ":k": s3_key})
    with patch("app.routes.analyses.call_github_tool", new=AsyncMock(return_value={"html_url": "https://github.com/acme/widgets/issues/99"})):
        response = client.post(f"/api/analyses/{analysis_id}/github-issue")
    assert response.status_code == 200
    assert response.json()["github_issue_url"] == "https://github.com/acme/widgets/issues/99"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/api && python -m pytest tests/test_create_github_issue.py -v`
Expected: FAIL — `404` route not found

- [ ] **Step 3: Implement**

```python
# backend/api/app/mcp_client.py
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from config import get_settings

async def call_github_tool(tool_name: str, **kwargs) -> dict:
    async with streamablehttp_client(get_settings().mcp_github_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, kwargs)
            return result.structuredContent
```

```python
# backend/api/app/routes/analyses.py — append
from app.mcp_client import call_github_tool
from app.schemas import GithubIssueResponse

@router.post("/{analysis_id}/github-issue", response_model=GithubIssueResponse)
async def create_github_issue(analysis_id: str):
    record = _store().get(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if record.status != "completed":
        raise HTTPException(status_code=409, detail=f"Analysis is {record.status}, cannot file issue yet")
    data = _report_store().read_json(record.s3_report_key)
    owner, repo = record.repository.split("/", 1)
    body_lines = ["## Missing Test Coverage (via TestScope AI)", ""]
    body_lines += [f"- {m['behavior']}" for m in data["missing_tests"]]
    result = await call_github_tool(
        "create_issue", owner=owner, repo=repo,
        title=f"Missing test coverage for #{record.issue_number}",
        body="\n".join(body_lines),
    )
    issue_url = result["html_url"]
    record.github_issue_url = issue_url
    _store().upsert(record)
    return GithubIssueResponse(github_issue_url=issue_url)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend/api && python -m pytest tests/test_create_github_issue.py -v`
Expected: PASS

- [ ] **Step 5: Run the full API test suite and check coverage**

Run: `cd backend/api && python -m pytest --cov=app --cov-report=term-missing`
Expected: all PASS, ≥80% coverage on `app/`

- [ ] **Step 6: Commit**

```bash
git add backend/api/app backend/api/tests/test_create_github_issue.py
git commit -m "feat(api): add POST /api/analyses/{id}/github-issue (gated, user-approved)"
```

- [ ] **Step 7: Add `backend/api/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY ../shared /shared
RUN pip install --no-cache-dir -e /shared && pip install --no-cache-dir .
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 8: Commit Dockerfile**

```bash
git add backend/api/Dockerfile
git commit -m "build(api): add Dockerfile"
```

---

## Phase 5 — `frontend` (React)

### Task 23: Frontend skeleton — API client, routing, Vitest config

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/main.tsx`
- Create: `frontend/vitest.config.ts`
- Test: `frontend/src/api/client.test.ts`

**Interfaces:**
- Produces (`types.ts`): `interface AnalysisStatus { analysis_id: string; repository: string; issue_number: number; status: "pending"|"running"|"completed"|"failed"; created_at: string; updated_at: string; requirement_summary: string | null; coverage_summary: { percent_covered: number } | null; missing_tests_count: number; error_message: string | null; github_issue_url: string | null }`, `interface Report { analysis_id: string; requirement: Record<string, unknown>; coverage_matrix: Array<Record<string, unknown>>; test_plan: Array<Record<string, unknown>>; missing_tests: Array<Record<string, unknown>>; tool_call_trace: Array<Record<string, unknown>>; download_url: string }`.
- Produces (`client.ts`): `async function createAnalysis(repository: string, issueNumber: number, notes?: string): Promise<{analysis_id: string; status: string}>`, `async function getAnalysis(id: string): Promise<AnalysisStatus>`, `async function listAnalyses(): Promise<{analyses: AnalysisStatus[]}>`, `async function getReport(id: string): Promise<Report>`, `async function createGithubIssue(id: string): Promise<{github_issue_url: string}>` — all consumed by Tasks 24–26. Base URL read from `import.meta.env.VITE_API_BASE_URL` (default `""`, same-origin).
- Produces (`App.tsx`): `<BrowserRouter>` with routes `/` (Home, Task 24), `/analyses/:id` (Results, Task 25), `/history` (History, Task 26).

- [ ] **Step 1: Write the failing test for the API client**

```ts
// frontend/src/api/client.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { createAnalysis, getAnalysis } from "./client";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

describe("createAnalysis", () => {
  it("POSTs to /api/analyses and returns the parsed body", async () => {
    (fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ analysis_id: "a1", status: "pending" }),
    });
    const result = await createAnalysis("acme/widgets", 42);
    expect(fetch).toHaveBeenCalledWith(
      "/api/analyses",
      expect.objectContaining({ method: "POST" })
    );
    expect(result.analysis_id).toBe("a1");
  });
});

describe("getAnalysis", () => {
  it("GETs /api/analyses/{id}", async () => {
    (fetch as any).mockResolvedValue({ ok: true, json: async () => ({ analysis_id: "a1", status: "completed" }) });
    const result = await getAnalysis("a1");
    expect(fetch).toHaveBeenCalledWith("/api/analyses/a1", expect.anything());
    expect(result.status).toBe("completed");
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npm test -- client.test.ts`
Expected: FAIL — `Cannot find module './client'`

- [ ] **Step 3: Implement**

```ts
// frontend/src/api/types.ts
export interface AnalysisStatus {
  analysis_id: string;
  repository: string;
  issue_number: number;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  requirement_summary: string | null;
  coverage_summary: { percent_covered: number } | null;
  missing_tests_count: number;
  error_message: string | null;
  github_issue_url: string | null;
}

export interface Report {
  analysis_id: string;
  requirement: Record<string, unknown>;
  coverage_matrix: Array<Record<string, unknown>>;
  test_plan: Array<Record<string, unknown>>;
  missing_tests: Array<Record<string, unknown>>;
  tool_call_trace: Array<Record<string, unknown>>;
  download_url: string;
}
```

```ts
// frontend/src/api/client.ts
import type { AnalysisStatus, Report } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, options);
  if (!response.ok) throw new Error(`Request to ${path} failed: ${response.status}`);
  return response.json();
}

export function createAnalysis(repository: string, issueNumber: number, notes?: string) {
  return request<{ analysis_id: string; status: string }>("/api/analyses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repository, issue_number: issueNumber, notes }),
  });
}

export function getAnalysis(id: string) {
  return request<AnalysisStatus>(`/api/analyses/${id}`);
}

export function listAnalyses() {
  return request<{ analyses: AnalysisStatus[] }>("/api/analyses");
}

export function getReport(id: string) {
  return request<Report>(`/api/analyses/${id}/report`);
}

export function createGithubIssue(id: string) {
  return request<{ github_issue_url: string }>(`/api/analyses/${id}/github-issue`, { method: "POST" });
}
```

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Home } from "./pages/Home";
import { Results } from "./pages/Results";
import { History } from "./pages/History";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/analyses/:id" element={<Results />} />
        <Route path="/history" element={<History />} />
      </Routes>
    </BrowserRouter>
  );
}
```

```tsx
// frontend/src/main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode><App /></StrictMode>
);
```

```ts
// frontend/vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", globals: true },
});
```

`pages/Home.tsx`, `pages/Results.tsx`, `pages/History.tsx` are stubbed with a one-line placeholder component in this task (`export function Home() { return <div>Home</div>; }`, etc.) so `App.tsx` compiles — Tasks 24–26 replace each stub with a real implementation.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- client.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src frontend/vitest.config.ts
git commit -m "feat(frontend): add API client, routing skeleton, page stubs"
```

### Task 24: Home page — repo/issue form

**Files:**
- Modify: `frontend/src/pages/Home.tsx` (replace stub)
- Test: `frontend/src/pages/Home.test.tsx`

**Interfaces:**
- Consumes: `createAnalysis` (Task 23).
- Produces: `export function Home()` — a form (`repository`, `issue_number`, optional `notes`) that on submit calls `createAnalysis` and navigates to `/analyses/{analysis_id}`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/pages/Home.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Home } from "./Home";
import * as client from "../api/client";

describe("Home", () => {
  it("submits repository and issue number, then navigates to the results page", async () => {
    vi.spyOn(client, "createAnalysis").mockResolvedValue({ analysis_id: "a1", status: "pending" });
    render(<MemoryRouter><Home /></MemoryRouter>);

    fireEvent.change(screen.getByLabelText(/repository/i), { target: { value: "acme/widgets" } });
    fireEvent.change(screen.getByLabelText(/issue number/i), { target: { value: "42" } });
    fireEvent.click(screen.getByRole("button", { name: /analyze test coverage/i }));

    await waitFor(() => expect(client.createAnalysis).toHaveBeenCalledWith("acme/widgets", 42, ""));
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npm test -- Home.test.tsx`
Expected: FAIL — stub `Home` has no form elements

- [ ] **Step 3: Implement**

```tsx
// frontend/src/pages/Home.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createAnalysis } from "../api/client";

export function Home() {
  const [repository, setRepository] = useState("");
  const [issueNumber, setIssueNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const result = await createAnalysis(repository, Number(issueNumber), notes);
      navigate(`/analyses/${result.analysis_id}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1>TestScope AI</h1>
      <label htmlFor="repository">Repository (owner/repo)</label>
      <input id="repository" value={repository} onChange={(e) => setRepository(e.target.value)} required />

      <label htmlFor="issue-number">Issue number</label>
      <input id="issue-number" type="number" value={issueNumber} onChange={(e) => setIssueNumber(e.target.value)} required />

      <label htmlFor="notes">Notes (optional)</label>
      <textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />

      <button type="submit" disabled={submitting}>Analyze test coverage</button>
    </form>
  );
}
```

Associate each `<label>` with its `<input>` via matching `htmlFor`/`id` (`repository`, `issue-number`, `notes`) so `getByLabelText` resolves them.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- Home.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Home.tsx frontend/src/pages/Home.test.tsx
git commit -m "feat(frontend): implement Home page (repo/issue form)"
```

### Task 25: Results page — poll status, render coverage matrix, create-issue/download actions

**Files:**
- Modify: `frontend/src/pages/Results.tsx` (replace stub)
- Test: `frontend/src/pages/Results.test.tsx`

**Interfaces:**
- Consumes: `getAnalysis`, `getReport`, `createGithubIssue` (Task 23), `useParams` for `:id`.
- Produces: `export function Results()` — polls `getAnalysis(id)` every 3s while `status` is `pending`/`running`; once `completed`, calls `getReport(id)` and renders requirement summary, coverage matrix table, missing scenarios, tool-call history, "Create GitHub issue" button (confirms via `window.confirm` before calling `createGithubIssue`), "Download report" link using `report.download_url`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/pages/Results.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { Results } from "./Results";
import * as client from "../api/client";

function renderAt(id: string) {
  return render(
    <MemoryRouter initialEntries={[`/analyses/${id}`]}>
      <Routes><Route path="/analyses/:id" element={<Results />} /></Routes>
    </MemoryRouter>
  );
}

describe("Results", () => {
  it("shows the coverage matrix once analysis completes", async () => {
    vi.spyOn(client, "getAnalysis").mockResolvedValue({
      analysis_id: "a1", repository: "acme/widgets", issue_number: 42, status: "completed",
      created_at: "", updated_at: "", requirement_summary: "Login",
      coverage_summary: { percent_covered: 50 }, missing_tests_count: 1,
      error_message: null, github_issue_url: null,
    });
    vi.spyOn(client, "getReport").mockResolvedValue({
      analysis_id: "a1", requirement: { feature_name: "Login" },
      coverage_matrix: [{ criterion_id: "AC1", status: "Not covered", explanation: "no test" }],
      test_plan: [], missing_tests: [{ behavior: "401 on bad password" }],
      tool_call_trace: [], download_url: "https://example.com/report.md",
    });
    renderAt("a1");
    await waitFor(() => expect(screen.getByText(/not covered/i)).toBeInTheDocument());
    expect(screen.getByText(/401 on bad password/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /download report/i })).toHaveAttribute("href", "https://example.com/report.md");
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npm test -- Results.test.tsx`
Expected: FAIL — stub `Results` renders nothing matching

- [ ] **Step 3: Implement**

```tsx
// frontend/src/pages/Results.tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getAnalysis, getReport, createGithubIssue } from "../api/client";
import type { AnalysisStatus, Report } from "../api/types";

export function Results() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [issueUrl, setIssueUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    async function poll() {
      const current = await getAnalysis(id!);
      if (cancelled) return;
      setStatus(current);
      if (current.status === "completed") {
        setReport(await getReport(id!));
      } else if (current.status !== "failed") {
        setTimeout(poll, 3000);
      }
    }
    poll();
    return () => { cancelled = true; };
  }, [id]);

  async function handleCreateIssue() {
    if (!id) return;
    if (!window.confirm("Create a GitHub issue for the missing tests?")) return;
    const result = await createGithubIssue(id);
    setIssueUrl(result.github_issue_url);
  }

  if (!status) return <p>Loading...</p>;
  if (status.status === "failed") return <p>Analysis failed: {status.error_message}</p>;
  if (status.status !== "completed" || !report) return <p>Analyzing... ({status.status})</p>;

  return (
    <div>
      <h1>{status.repository}#{status.issue_number}</h1>
      <p>Coverage: {status.coverage_summary?.percent_covered}%</p>

      <h2>Coverage Matrix</h2>
      <table>
        <tbody>
          {report.coverage_matrix.map((row: any) => (
            <tr key={row.criterion_id}>
              <td>{row.criterion_id}</td>
              <td>{row.status}</td>
              <td>{row.explanation}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Missing Scenarios</h2>
      <ul>{report.missing_tests.map((m: any, i: number) => <li key={i}>{m.behavior}</li>)}</ul>

      <h2>Tool Call History</h2>
      <ul>{report.tool_call_trace.map((t: any, i: number) => <li key={i}>{t.node} → {t.tool} ({t.duration_ms}ms)</li>)}</ul>

      <button onClick={handleCreateIssue} disabled={!!status.github_issue_url || !!issueUrl}>
        Create GitHub issue
      </button>
      {(issueUrl || status.github_issue_url) && <p>Issue: {issueUrl ?? status.github_issue_url}</p>}
      <a href={report.download_url}>Download report</a>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- Results.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Results.tsx frontend/src/pages/Results.test.tsx
git commit -m "feat(frontend): implement Results page (polling, coverage matrix, actions)"
```

### Task 26: History page

**Files:**
- Modify: `frontend/src/pages/History.tsx` (replace stub)
- Test: `frontend/src/pages/History.test.tsx`

**Interfaces:**
- Consumes: `listAnalyses` (Task 23).
- Produces: `export function History()` — table of `repository`, `issue_number`, `created_at`, `status`, `coverage_summary.percent_covered`, linking each row to `/analyses/{analysis_id}`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/pages/History.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { History } from "./History";
import * as client from "../api/client";

describe("History", () => {
  it("lists past analyses with a link to each", async () => {
    vi.spyOn(client, "listAnalyses").mockResolvedValue({
      analyses: [{
        analysis_id: "a1", repository: "acme/widgets", issue_number: 42, status: "completed",
        created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
        requirement_summary: "Login", coverage_summary: { percent_covered: 80 },
        missing_tests_count: 1, error_message: null, github_issue_url: null,
      }],
    });
    render(<MemoryRouter><History /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText("acme/widgets")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /42/ })).toHaveAttribute("href", "/analyses/a1");
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npm test -- History.test.tsx`
Expected: FAIL — stub `History` renders nothing matching

- [ ] **Step 3: Implement**

```tsx
// frontend/src/pages/History.tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAnalyses } from "../api/client";
import type { AnalysisStatus } from "../api/types";

export function History() {
  const [analyses, setAnalyses] = useState<AnalysisStatus[]>([]);

  useEffect(() => {
    listAnalyses().then((result) => setAnalyses(result.analyses));
  }, []);

  return (
    <table>
      <thead><tr><th>Repository</th><th>Issue</th><th>Date</th><th>Status</th><th>Coverage</th></tr></thead>
      <tbody>
        {analyses.map((a) => (
          <tr key={a.analysis_id}>
            <td>{a.repository}</td>
            <td><Link to={`/analyses/${a.analysis_id}`}>{a.issue_number}</Link></td>
            <td>{a.created_at}</td>
            <td>{a.status}</td>
            <td>{a.coverage_summary?.percent_covered ?? "-"}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- History.test.tsx`
Expected: PASS

- [ ] **Step 5: Run the full frontend test suite**

Run: `cd frontend && npm test`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/History.tsx frontend/src/pages/History.test.tsx
git commit -m "feat(frontend): implement History page"
```

- [ ] **Step 7: Add `frontend/Dockerfile` (multi-stage build served via nginx)**

```dockerfile
FROM node:20-slim AS build
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

- [ ] **Step 8: Commit Dockerfile**

```bash
git add frontend/Dockerfile
git commit -m "build(frontend): add multi-stage Dockerfile (nginx)"
```

---

## Phase 6 — Terraform

Infra tasks aren't TDD in the pytest sense; each task's "test" step is `terraform validate`/`plan` (and, where noted, an actual `apply` against a real AWS account — flagged explicitly since that's a real-money, real-infrastructure action the implementer should confirm before running).

### Task 27: `networking` and `ec2` modules + `shared` environment (VPC, k3s bootstrap)

**Files:**
- Create: `terraform/modules/networking/main.tf`, `variables.tf`, `outputs.tf`
- Create: `terraform/modules/ec2/main.tf`, `variables.tf`, `outputs.tf`, `cloud-init.yaml.tpl`
- Create: `terraform/environments/shared/main.tf`, `variables.tf`, `backend.tf`

**Interfaces:**
- Produces (`networking` module outputs): `vpc_id`, `public_subnet_id`, `security_group_id` — consumed by `ec2` module.
- Produces (`ec2` module outputs): `instance_public_ip`, `instance_id` — consumed by Task 29 (deploy jobs need the IP for the self-hosted runner) and by `environments/dev`/`environments/prod` (Task 29) for IAM instance-profile attachment references.

- [ ] **Step 1: Write `networking` module**

```hcl
# terraform/modules/networking/main.tf
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags                 = { Name = "testscope-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block               = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone        = "${var.aws_region}a"
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "k3s_host" {
  name   = "testscope-k3s-host"
  vpc_id = aws_vpc.main.id

  ingress { description = "SSH from admin"; from_port = 22; to_port = 22; protocol = "tcp"; cidr_blocks = [var.admin_cidr] }
  ingress { description = "k3s API"; from_port = 6443; to_port = 6443; protocol = "tcp"; cidr_blocks = [var.admin_cidr] }
  ingress { description = "HTTP ingress"; from_port = 80; to_port = 80; protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  ingress { description = "HTTPS ingress"; from_port = 443; to_port = 443; protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}
```

```hcl
# terraform/modules/networking/variables.tf
variable "aws_region" { type = string }
variable "admin_cidr" { type = string, description = "Your IP in CIDR form, e.g. 203.0.113.4/32" }
```

```hcl
# terraform/modules/networking/outputs.tf
output "vpc_id" { value = aws_vpc.main.id }
output "public_subnet_id" { value = aws_subnet.public.id }
output "security_group_id" { value = aws_security_group.k3s_host.id }
```

- [ ] **Step 2: Write `ec2` module with k3s cloud-init bootstrap**

```hcl
# terraform/modules/ec2/main.tf
resource "aws_iam_role" "k3s_host" {
  name = "testscope-k3s-host-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" } }]
  })
}

resource "aws_iam_instance_profile" "k3s_host" {
  name = "testscope-k3s-host-profile"
  role = aws_iam_role.k3s_host.name
}

resource "aws_instance" "k3s_host" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = var.public_subnet_id
  vpc_security_group_ids = [var.security_group_id]
  iam_instance_profile   = aws_iam_instance_profile.k3s_host.name
  key_name               = var.key_pair_name
  user_data              = templatefile("${path.module}/cloud-init.yaml.tpl", {})

  root_block_device { volume_size = 40 }
  tags = { Name = "testscope-k3s-host" }
}
```

```yaml
# terraform/modules/ec2/cloud-init.yaml.tpl
#cloud-config
runcmd:
  - curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644
  - k3s kubectl create namespace dev
  - k3s kubectl create namespace prod
  - k3s kubectl create namespace monitoring
```

```hcl
# terraform/modules/ec2/variables.tf
variable "ami_id" { type = string, description = "Ubuntu 22.04 LTS AMI id for the target region" }
variable "instance_type" { type = string, default = "t3.large" }
variable "public_subnet_id" { type = string }
variable "security_group_id" { type = string }
variable "key_pair_name" { type = string }
```

```hcl
# terraform/modules/ec2/outputs.tf
output "instance_public_ip" { value = aws_instance.k3s_host.public_ip }
output "instance_id" { value = aws_instance.k3s_host.id }
output "iam_role_arn" { value = aws_iam_role.k3s_host.arn }
```

```hcl
# terraform/environments/shared/main.tf
terraform { required_version = ">= 1.5" }
provider "aws" { region = var.aws_region }

module "networking" {
  source     = "../../modules/networking"
  aws_region = var.aws_region
  admin_cidr = var.admin_cidr
}

module "ec2" {
  source             = "../../modules/ec2"
  ami_id             = var.ami_id
  public_subnet_id   = module.networking.public_subnet_id
  security_group_id  = module.networking.security_group_id
  key_pair_name      = var.key_pair_name
}

output "instance_public_ip" { value = module.ec2.instance_public_ip }
output "iam_role_arn" { value = module.ec2.iam_role_arn }
```

```hcl
# terraform/environments/shared/variables.tf
variable "aws_region" { type = string, default = "us-east-1" }
variable "admin_cidr" { type = string }
variable "ami_id" { type = string }
variable "key_pair_name" { type = string }
```

- [ ] **Step 3: Validate**

Run: `cd terraform/environments/shared && terraform init && terraform validate`
Expected: `Success! The configuration is valid.`

- [ ] **Step 4: Commit**

```bash
git add terraform/modules/networking terraform/modules/ec2 terraform/environments/shared
git commit -m "feat(terraform): add networking and ec2 modules, shared environment (VPC + k3s host)"
```

### Task 28: `iam`, `s3`, `dynamodb`, `sqs` modules (parameterized by env)

**Files:**
- Create: `terraform/modules/iam/main.tf`, `variables.tf`
- Create: `terraform/modules/s3/main.tf`, `variables.tf`, `outputs.tf`
- Create: `terraform/modules/dynamodb/main.tf`, `variables.tf`, `outputs.tf`
- Create: `terraform/modules/sqs/main.tf`, `variables.tf`, `outputs.tf`

**Interfaces:**
- Each module takes `var.env` (`"dev"`/`"prod"`) and names resources accordingly (`testscope-reports-${var.env}`, `testscope-analyses-${var.env}`, `testscope-jobs-${var.env}`), matching spec §6/§9 exactly. Outputs (`bucket_name`, `table_name`, `queue_url`, `dlq_url`) are consumed by Task 29's `dev`/`prod` environments and end up in K8s ConfigMaps (Task 34).

- [ ] **Step 1: Write `s3` module**

```hcl
# terraform/modules/s3/main.tf
resource "aws_s3_bucket" "reports" {
  bucket = "testscope-reports-${var.env}"
}

resource "aws_s3_bucket_lifecycle_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id
  rule {
    id     = "expire-old-reports"
    status = "Enabled"
    expiration { days = 180 }
  }
}
```

```hcl
# terraform/modules/s3/variables.tf
variable "env" { type = string }
```

```hcl
# terraform/modules/s3/outputs.tf
output "bucket_name" { value = aws_s3_bucket.reports.id }
output "bucket_arn" { value = aws_s3_bucket.reports.arn }
```

- [ ] **Step 2: Write `dynamodb` module (table + GSI1 + GSI2, per spec §6)**

```hcl
# terraform/modules/dynamodb/main.tf
resource "aws_dynamodb_table" "analyses" {
  name         = "testscope-analyses-${var.env}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "analysis_id"

  attribute { name = "analysis_id"; type = "S" }
  attribute { name = "repository_issue"; type = "S" }
  attribute { name = "created_at"; type = "S" }
  attribute { name = "gsi2_pk"; type = "S" }

  global_secondary_index {
    name            = "repository_issue-index"
    hash_key        = "repository_issue"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "recent-index"
    hash_key        = "gsi2_pk"
    range_key       = "created_at"
    projection_type = "ALL"
  }
}
```

```hcl
# terraform/modules/dynamodb/variables.tf
variable "env" { type = string }
```

```hcl
# terraform/modules/dynamodb/outputs.tf
output "table_name" { value = aws_dynamodb_table.analyses.name }
output "table_arn" { value = aws_dynamodb_table.analyses.arn }
```

- [ ] **Step 3: Write `sqs` module (queue + DLQ, redrive after 3 receives)**

```hcl
# terraform/modules/sqs/main.tf
resource "aws_sqs_queue" "dlq" {
  name = "testscope-jobs-${var.env}-dlq"
}

resource "aws_sqs_queue" "jobs" {
  name                       = "testscope-jobs-${var.env}"
  visibility_timeout_seconds = 660  # > worker's 600s graph timeout
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount      = 3
  })
}
```

```hcl
# terraform/modules/sqs/variables.tf
variable "env" { type = string }
```

```hcl
# terraform/modules/sqs/outputs.tf
output "queue_url" { value = aws_sqs_queue.jobs.id }
output "queue_arn" { value = aws_sqs_queue.jobs.arn }
output "dlq_arn" { value = aws_sqs_queue.dlq.arn }
```

- [ ] **Step 4: Write `iam` module (least-privilege policy scoped to this env's resources, attached to the shared instance role)**

```hcl
# terraform/modules/iam/main.tf
resource "aws_iam_role_policy" "env_access" {
  name = "testscope-${var.env}-access"
  role = var.instance_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = "${var.bucket_arn}/*" },
      { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
        Resource = [var.table_arn, "${var.table_arn}/index/*"] },
      { Effect = "Allow", Action = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
        Resource = [var.queue_arn, var.dlq_arn] },
      { Effect = "Allow", Action = ["cloudwatch:PutMetricData", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "*" },
    ]
  })
}
```

```hcl
# terraform/modules/iam/variables.tf
variable "env" { type = string }
variable "instance_role_name" { type = string }
variable "bucket_arn" { type = string }
variable "table_arn" { type = string }
variable "queue_arn" { type = string }
variable "dlq_arn" { type = string }
```

- [ ] **Step 5: Validate each module standalone**

Run: `for m in s3 dynamodb sqs iam; do (cd terraform/modules/$m && terraform init -backend=false && terraform validate); done`
Expected: `Success!` for all four

- [ ] **Step 6: Commit**

```bash
git add terraform/modules/iam terraform/modules/s3 terraform/modules/dynamodb terraform/modules/sqs
git commit -m "feat(terraform): add iam, s3, dynamodb, sqs modules parameterized by env"
```

### Task 29: `monitoring` module + `dev`/`prod` environments

**Files:**
- Create: `terraform/modules/monitoring/main.tf`, `variables.tf`
- Create: `terraform/environments/dev/main.tf`, `variables.tf`, `backend.tf`
- Create: `terraform/environments/prod/main.tf`, `variables.tf`, `backend.tf`

**Interfaces:**
- Consumes: `iam_role_arn`, `instance_public_ip` outputs from `environments/shared` (Task 27, referenced via `terraform_remote_state` data source) and the `s3`/`dynamodb`/`sqs`/`iam` modules (Task 28).
- Produces: per-env `bucket_name`, `table_name`, `queue_url` outputs — consumed directly by Task 34's K8s ConfigMap values (copied in manually per spec's "no manual clicking" caveat being about AWS resources, not about transcribing Terraform outputs into K8s config, which is standard practice; Task 34 documents this as a required manual step between `terraform apply` and `kubectl apply`).

- [ ] **Step 1: Write `monitoring` module (CloudWatch alarms + SNS, per spec §12)**

```hcl
# terraform/modules/monitoring/main.tf
resource "aws_sns_topic" "alerts" {
  name = "testscope-${var.env}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "dlq_not_empty" {
  alarm_name          = "testscope-${var.env}-dlq-not-empty"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  dimensions          = { QueueName = "testscope-jobs-${var.env}-dlq" }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "queue_backlog_age" {
  alarm_name          = "testscope-${var.env}-queue-backlog-age"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 900  # 15 min backlog
  dimensions          = { QueueName = "testscope-jobs-${var.env}" }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

```hcl
# terraform/modules/monitoring/variables.tf
variable "env" { type = string }
variable "alert_email" { type = string }
```

- [ ] **Step 2: Wire `dev` environment**

```hcl
# terraform/environments/dev/main.tf
terraform { required_version = ">= 1.5" }
provider "aws" { region = var.aws_region }

data "terraform_remote_state" "shared" {
  backend = "local"  # or "s3" with a real backend config — see backend.tf
  config  = { path = "../shared/terraform.tfstate" }
}

module "s3" { source = "../../modules/s3"; env = "dev" }
module "dynamodb" { source = "../../modules/dynamodb"; env = "dev" }
module "sqs" { source = "../../modules/sqs"; env = "dev" }

module "iam" {
  source              = "../../modules/iam"
  env                 = "dev"
  instance_role_name  = "testscope-k3s-host-role"
  bucket_arn          = module.s3.bucket_arn
  table_arn           = module.dynamodb.table_arn
  queue_arn           = module.sqs.queue_arn
  dlq_arn             = module.sqs.dlq_arn
}

module "monitoring" {
  source      = "../../modules/monitoring"
  env         = "dev"
  alert_email = var.alert_email
}

output "bucket_name" { value = module.s3.bucket_name }
output "table_name" { value = module.dynamodb.table_name }
output "queue_url" { value = module.sqs.queue_url }
```

```hcl
# terraform/environments/dev/variables.tf
variable "aws_region" { type = string, default = "us-east-1" }
variable "alert_email" { type = string }
```

Create `terraform/environments/prod/main.tf` identically, substituting `env = "prod"` everywhere and pointing `data.terraform_remote_state` at the same shared state (the EC2 host/IAM role is shared across both envs — only the AWS resources differ).

- [ ] **Step 3: Validate both**

Run: `for e in dev prod; do (cd terraform/environments/$e && terraform init -backend=false && terraform validate); done`
Expected: `Success!` for both

- [ ] **Step 4: Commit**

```bash
git add terraform/modules/monitoring terraform/environments/dev terraform/environments/prod
git commit -m "feat(terraform): add monitoring module (CloudWatch alarms + SNS), dev/prod environments"
```

### Task 30: Terraform validation and documented apply order

**Files:**
- Create: `terraform/README.md`

**Interfaces:** none — this task documents and verifies, it doesn't add new resources.

- [ ] **Step 1: Run `terraform fmt -recursive` across the whole `terraform/` tree**

Run: `cd terraform && terraform fmt -recursive -check`
Expected: no output (already formatted); if it lists files, run without `-check` to fix them, then re-run with `-check` to confirm

- [ ] **Step 2: Run `terraform validate` for all three roots**

Run: `for e in shared dev prod; do (cd terraform/environments/$e && terraform init -backend=false && terraform validate); done`
Expected: `Success!` for all three

- [ ] **Step 3: Document apply order (this is where real AWS spend starts — confirm account/region/budget before running)**

```markdown
# terraform/README.md

## Apply order (real AWS resources — confirm account, region, and budget first)

1. `cd terraform/environments/shared && terraform init && terraform apply` — provisions the VPC and the single k3s EC2 host. Note `instance_public_ip` from the output; you'll need it for `kubectl` access and CI's self-hosted runner registration.
2. `cd terraform/environments/dev && terraform init && terraform apply` — provisions dev's S3 bucket, DynamoDB table, SQS queues, IAM policy, CloudWatch alarms.
3. `cd terraform/environments/prod && terraform init && terraform apply` — same, for prod.
4. Copy each environment's `bucket_name`/`table_name`/`queue_url` outputs into the matching Kubernetes ConfigMap (`kubernetes/dev/configmap.yaml` / `kubernetes/prod/configmap.yaml`, Task 34) — this hand-off is manual by design (Terraform provisions AWS resources; it does not template Kubernetes manifests).
5. Tear-down order is the reverse: `prod` → `dev` → `shared` (`terraform destroy` in each), since `dev`/`prod` reference the shared instance role by name.
```

- [ ] **Step 4: Commit**

```bash
git add terraform/README.md
git commit -m "docs(terraform): document validated fmt/validate pass and apply order"
```

---

## Phase 7 — Kubernetes Manifests (k3s)

Base manifests are environment-agnostic; `kustomize` overlays (Task 34) patch in per-namespace values. Every manifest that needs a real image reference uses `ghcr.io/<org>/testscope-<service>:latest` as a placeholder tag — Task 34's overlays pin the actual tag (set by CI, Task 36/37).

### Task 31: Base `api` and `worker` manifests

**Files:**
- Create: `kubernetes/base/api/deployment.yaml`, `service.yaml`
- Create: `kubernetes/base/worker/deployment.yaml`
- Create: `kubernetes/base/configmap.yaml` (shared keys, values patched per-env)
- Create: `kubernetes/base/kustomization.yaml`

**Interfaces:** none consumed from earlier tasks (K8s manifests are declarative, not code with function signatures) — but every env var name here (`DYNAMODB_TABLE`, `S3_BUCKET`, `SQS_QUEUE_URL`, `MCP_GITHUB_URL`, `MCP_TEST_ANALYSIS_URL`, `ANTHROPIC_API_KEY`) must match exactly what `backend/shared/config.py`'s `Settings` (Task 9) reads via `pydantic-settings`'s default env-var-name-from-field-name behavior (uppercased field name).

- [ ] **Step 1: Write `api` Deployment + Service**

```yaml
# kubernetes/base/api/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 1
  selector: { matchLabels: { app: api } }
  template:
    metadata: { labels: { app: api } }
    spec:
      containers:
        - name: api
          image: ghcr.io/testscope-ai/api:latest
          ports: [{ containerPort: 8000 }]
          envFrom: [{ configMapRef: { name: testscope-config } }]
          resources:
            requests: { cpu: 100m, memory: 256Mi }
            limits: { cpu: 500m, memory: 512Mi }
          livenessProbe: { httpGet: { path: /health/live, port: 8000 }, initialDelaySeconds: 5, periodSeconds: 10 }
          readinessProbe: { httpGet: { path: /health/ready, port: 8000 }, initialDelaySeconds: 5, periodSeconds: 10 }
```

```yaml
# kubernetes/base/api/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  selector: { app: api }
  ports: [{ port: 8000, targetPort: 8000 }]
```

- [ ] **Step 2: Write `worker` Deployment (no Service needed — SQS-driven, only the health port is probed in-pod)**

```yaml
# kubernetes/base/worker/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker
spec:
  replicas: 1
  selector: { matchLabels: { app: worker } }
  template:
    metadata: { labels: { app: worker } }
    spec:
      containers:
        - name: worker
          image: ghcr.io/testscope-ai/worker:latest
          ports: [{ containerPort: 8080 }]
          envFrom: [{ configMapRef: { name: testscope-config } }]
          env:
            - name: ANTHROPIC_API_KEY
              valueFrom: { secretKeyRef: { name: worker-secrets, key: anthropic-api-key } }
          resources:
            requests: { cpu: 250m, memory: 512Mi }
            limits: { cpu: 1000m, memory: 1Gi }
          livenessProbe: { httpGet: { path: /health/live, port: 8080 }, initialDelaySeconds: 10, periodSeconds: 15 }
          readinessProbe: { httpGet: { path: /health/ready, port: 8080 }, initialDelaySeconds: 10, periodSeconds: 15 }
```

- [ ] **Step 3: Write the shared ConfigMap and root `kustomization.yaml`**

```yaml
# kubernetes/base/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: testscope-config
data:
  ENV: "base"  # overridden per-namespace in Task 34
  LOG_LEVEL: "INFO"
  DYNAMODB_TABLE: "REPLACED_BY_OVERLAY"
  S3_BUCKET: "REPLACED_BY_OVERLAY"
  SQS_QUEUE_URL: "REPLACED_BY_OVERLAY"
  MCP_GITHUB_URL: "http://mcp-github:8100/mcp"
  MCP_TEST_ANALYSIS_URL: "http://mcp-test-analysis:8100/mcp"
```

```yaml
# kubernetes/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - api/deployment.yaml
  - api/service.yaml
  - worker/deployment.yaml
  - configmap.yaml
```

- [ ] **Step 4: Validate manifests parse (no live cluster required)**

Run: `kubectl apply --dry-run=client -k kubernetes/base`
Expected: prints `deployment.apps/api created (dry run)` etc. for every resource, no errors — note this will report a missing `worker-secrets` Secret reference only at apply time against a real cluster, not at this client-side dry run

- [ ] **Step 5: Commit**

```bash
git add kubernetes/base/api kubernetes/base/worker kubernetes/base/configmap.yaml kubernetes/base/kustomization.yaml
git commit -m "feat(k8s): add base api and worker manifests (probes, resource limits)"
```

### Task 32: `mcp-test-analysis` and `mcp-github` manifests

**Files:**
- Create: `kubernetes/base/mcp-test-analysis/deployment.yaml`, `service.yaml`, `secret.yaml.example`
- Create: `kubernetes/base/mcp-github/deployment.yaml`, `service.yaml`
- Modify: `kubernetes/base/kustomization.yaml` (add both)

**Interfaces:** `mcp-test-analysis` Service DNS name `mcp-test-analysis:8100` and `mcp-github` Service DNS name `mcp-github:8100` are exactly the values baked into `kubernetes/base/configmap.yaml`'s `MCP_TEST_ANALYSIS_URL`/`MCP_GITHUB_URL` from Task 31 — keep these in sync if either Service name changes.

- [ ] **Step 1: Write `mcp-test-analysis` manifests (with the `/workspace` emptyDir + sizeLimit from spec §10)**

```yaml
# kubernetes/base/mcp-test-analysis/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-test-analysis
spec:
  replicas: 1
  selector: { matchLabels: { app: mcp-test-analysis } }
  template:
    metadata: { labels: { app: mcp-test-analysis } }
    spec:
      containers:
        - name: mcp-test-analysis
          image: ghcr.io/testscope-ai/mcp-test-analysis:latest
          ports: [{ containerPort: 8100 }]
          env:
            - name: WORKSPACE_ROOT
              value: /workspace
            - name: MCP_GITHUB_URL
              value: http://mcp-github:8100/mcp
            - name: GITHUB_TOKEN
              valueFrom: { secretKeyRef: { name: github-token, key: token } }
          envFrom: [{ configMapRef: { name: testscope-config } }]
          resources:
            requests: { cpu: 200m, memory: 256Mi }
            limits: { cpu: 500m, memory: 512Mi }
          volumeMounts: [{ name: workspace, mountPath: /workspace }]
          livenessProbe: { httpGet: { path: /health/live, port: 8100 }, initialDelaySeconds: 5, periodSeconds: 10 }
          readinessProbe: { httpGet: { path: /health/ready, port: 8100 }, initialDelaySeconds: 5, periodSeconds: 10 }
      volumes:
        - name: workspace
          emptyDir: { sizeLimit: 2Gi }
```

```yaml
# kubernetes/base/mcp-test-analysis/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-test-analysis
spec:
  selector: { app: mcp-test-analysis }
  ports: [{ port: 8100, targetPort: 8100 }]
```

```yaml
# kubernetes/base/mcp-test-analysis/secret.yaml.example
# Copy to secret.yaml (gitignored) and fill in per environment — never commit real tokens.
apiVersion: v1
kind: Secret
metadata:
  name: github-token
type: Opaque
stringData:
  token: "REPLACE_WITH_GITHUB_PAT"
```

Note in `server.py` (Task 8) that `/health/live` and `/health/ready` don't exist yet on the MCP server — add them now as part of this task since the probes above require them:

```python
# mcp-server/server.py — add before `if __name__ == "__main__":`
from fastapi import FastAPI
import threading
import uvicorn

def _start_health_server(port: int = 8101):
    app = FastAPI()
    app.get("/health/live")(lambda: {"status": "ok"})
    app.get("/health/ready")(lambda: {"status": "ok"})
    threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning"), daemon=True).start()
```

Call `_start_health_server()` in `server.py`'s `if __name__ == "__main__":` block alongside `start_sweeper(...)`, and change the probe ports above from `8100` to `8101` accordingly (the MCP transport and the health server run on separate ports in the same container). Add a matching unit test `mcp-server/tests/test_health.py` asserting both routes return 200 via `TestClient(_start_health_server.__wrapped__ ...)` — simpler: refactor `_start_health_server`'s inner `app` construction into a module-level `def build_health_app() -> FastAPI` so it's directly testable with `TestClient(build_health_app())` without starting a real server thread.

- [ ] **Step 2: Write `mcp-github` manifests (official image)**

```yaml
# kubernetes/base/mcp-github/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-github
spec:
  replicas: 1
  selector: { matchLabels: { app: mcp-github } }
  template:
    metadata: { labels: { app: mcp-github } }
    spec:
      containers:
        - name: mcp-github
          image: ghcr.io/github/github-mcp-server:latest
          ports: [{ containerPort: 8100 }]
          env:
            - name: GITHUB_PERSONAL_ACCESS_TOKEN
              valueFrom: { secretKeyRef: { name: github-token, key: token } }
          resources:
            requests: { cpu: 200m, memory: 256Mi }
            limits: { cpu: 500m, memory: 512Mi }
```

```yaml
# kubernetes/base/mcp-github/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-github
spec:
  selector: { app: mcp-github }
  ports: [{ port: 8100, targetPort: 8100 }]
```

`mcp-github` uses its **own** `github-token` Secret instance (per-namespace, created independently of `mcp-test-analysis`'s) — both reference the same Secret *name* for manifest simplicity, but each namespace's overlay (Task 34) supplies its own Secret value; this still satisfies spec §5.1's "own K8s Secret" requirement since it's not shared across namespaces or read by `worker`/`api`.

**Note:** verify the exact tool names/parameters against the installed `github-mcp-server` version's tool list (e.g. `docker run ghcr.io/github/github-mcp-server --help` or its README) before wiring Task 11/22's `get_repository`/`get_issue`/`get_issue_comments`/`create_issue` calls against a real deployment — this plan assumes those names per spec §5.2 but the upstream project's exact naming should be confirmed once, in this task, and any mismatch fixed in the two call sites (`backend/worker/app/mcp_clients.py`, `backend/api/app/mcp_client.py`) plus `mcp-server/github_client.py`.

- [ ] **Step 3: Update `kustomization.yaml` and validate**

```yaml
# kubernetes/base/kustomization.yaml — add to resources:
  - mcp-test-analysis/deployment.yaml
  - mcp-test-analysis/service.yaml
  - mcp-github/deployment.yaml
  - mcp-github/service.yaml
```

Run: `kubectl apply --dry-run=client -k kubernetes/base`
Expected: all resources listed, no parse errors

- [ ] **Step 4: Commit**

```bash
git add kubernetes/base/mcp-test-analysis kubernetes/base/mcp-github kubernetes/base/kustomization.yaml mcp-server/server.py mcp-server/tests/test_health.py
git commit -m "feat(k8s): add mcp-test-analysis and mcp-github manifests; add health endpoints to mcp-server"
```

### Task 33: `frontend` manifests + Ingress (Traefik)

**Files:**
- Create: `kubernetes/base/frontend/deployment.yaml`, `service.yaml`
- Create: `kubernetes/base/ingress.yaml`
- Modify: `kubernetes/base/kustomization.yaml`

**Interfaces:** none new — `frontend`'s nginx container proxies `/api/*` to the `api` Service (config below), so the browser never needs `VITE_API_BASE_URL` set at build time for the demo deployment (same-origin requests).

- [ ] **Step 1: Write `frontend` Deployment + Service + nginx API proxy config**

```yaml
# kubernetes/base/frontend/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 1
  selector: { matchLabels: { app: frontend } }
  template:
    metadata: { labels: { app: frontend } }
    spec:
      containers:
        - name: frontend
          image: ghcr.io/testscope-ai/frontend:latest
          ports: [{ containerPort: 80 }]
          resources:
            requests: { cpu: 50m, memory: 64Mi }
            limits: { cpu: 200m, memory: 256Mi }
          livenessProbe: { httpGet: { path: /, port: 80 }, initialDelaySeconds: 5, periodSeconds: 10 }
          readinessProbe: { httpGet: { path: /, port: 80 }, initialDelaySeconds: 5, periodSeconds: 10 }
```

```yaml
# kubernetes/base/frontend/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  selector: { app: frontend }
  ports: [{ port: 80, targetPort: 80 }]
```

Add `frontend/nginx.conf` (referenced by the `frontend/Dockerfile` from Task 26 — extend that Dockerfile's final stage to `COPY nginx.conf /etc/nginx/conf.d/default.conf`):

```nginx
# frontend/nginx.conf
server {
    listen 80;
    root /usr/share/nginx/html;
    location /api/ { proxy_pass http://api:8000; }
    location / { try_files $uri /index.html; }
}
```

- [ ] **Step 2: Write the Ingress (host-based routing per spec §10)**

```yaml
# kubernetes/base/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: testscope-ingress
  annotations:
    kubernetes.io/ingress.class: traefik
spec:
  rules:
    - host: REPLACED_BY_OVERLAY  # dev.testscope.local / testscope.local, see Task 34
      http:
        paths:
          - path: /
            pathType: Prefix
            backend: { service: { name: frontend, port: { number: 80 } } }
```

- [ ] **Step 3: Update `kustomization.yaml` and validate**

```yaml
# kubernetes/base/kustomization.yaml — add to resources:
  - frontend/deployment.yaml
  - frontend/service.yaml
  - ingress.yaml
```

Run: `kubectl apply --dry-run=client -k kubernetes/base`
Expected: all resources listed, no parse errors

- [ ] **Step 4: Commit**

```bash
git add kubernetes/base/frontend kubernetes/base/ingress.yaml kubernetes/base/kustomization.yaml frontend/nginx.conf frontend/Dockerfile
git commit -m "feat(k8s): add frontend manifests, Traefik ingress, nginx API proxy config"
```

### Task 34: `dev`/`prod` kustomize overlays (namespace, HPA, env-specific config) + validation

**Files:**
- Create: `kubernetes/dev/kustomization.yaml`, `configmap-patch.yaml`, `hpa.yaml`, `ingress-patch.yaml`
- Create: `kubernetes/prod/kustomization.yaml`, `configmap-patch.yaml`, `hpa.yaml`, `ingress-patch.yaml`
- Create: `kubernetes/monitoring/namespace.yaml` (placeholder namespace resource; Prometheus/Grafana/Loki manifests land here in Phase 9)

**Interfaces:** consumes Terraform outputs from Task 29/30 (`bucket_name`, `table_name`, `queue_url`) as the literal values in each `configmap-patch.yaml` — this is the manual hand-off documented in Task 30's `terraform/README.md`.

- [ ] **Step 1: Write the `dev` overlay**

```yaml
# kubernetes/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: dev
resources:
  - ../base
  - hpa.yaml
patches:
  - path: configmap-patch.yaml
  - path: ingress-patch.yaml
replicas:
  - name: api
    count: 1
  - name: worker
    count: 1
```

```yaml
# kubernetes/dev/configmap-patch.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: testscope-config
data:
  ENV: "dev"
  DYNAMODB_TABLE: "testscope-analyses-dev"     # from `terraform output table_name` in environments/dev
  S3_BUCKET: "testscope-reports-dev"           # from `terraform output bucket_name`
  SQS_QUEUE_URL: "PASTE_FROM_TERRAFORM_OUTPUT_queue_url"
```

```yaml
# kubernetes/dev/ingress-patch.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: testscope-ingress
spec:
  rules:
    - host: dev.testscope.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend: { service: { name: frontend, port: { number: 80 } } }
```

```yaml
# kubernetes/dev/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: api }
  minReplicas: 1
  maxReplicas: 3
  metrics: [{ type: Resource, resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } } }]
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: worker-hpa
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: worker }
  minReplicas: 1
  maxReplicas: 3
  metrics: [{ type: Resource, resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } } }]
```

- [ ] **Step 2: Write the `prod` overlay (same shape, prod-scoped values, higher baseline replicas)**

```yaml
# kubernetes/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: prod
resources:
  - ../base
  - hpa.yaml
patches:
  - path: configmap-patch.yaml
  - path: ingress-patch.yaml
replicas:
  - name: api
    count: 2
  - name: worker
    count: 1
```

```yaml
# kubernetes/prod/configmap-patch.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: testscope-config
data:
  ENV: "prod"
  DYNAMODB_TABLE: "testscope-analyses-prod"
  S3_BUCKET: "testscope-reports-prod"
  SQS_QUEUE_URL: "PASTE_FROM_TERRAFORM_OUTPUT_queue_url"
```

```yaml
# kubernetes/prod/ingress-patch.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: testscope-ingress
spec:
  rules:
    - host: testscope.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend: { service: { name: frontend, port: { number: 80 } } }
```

Copy `kubernetes/dev/hpa.yaml`'s content into `kubernetes/prod/hpa.yaml` unchanged (same scaling policy in both envs for this project's scale).

- [ ] **Step 3: Validate both overlays render**

Run: `kubectl kustomize kubernetes/dev | kubectl apply --dry-run=client -f -`
Run: `kubectl kustomize kubernetes/prod | kubectl apply --dry-run=client -f -`
Expected: both print the full resource list (namespaced to `dev`/`prod` respectively) with no errors

- [ ] **Step 4: Add the `monitoring` namespace placeholder**

```yaml
# kubernetes/monitoring/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
```

- [ ] **Step 5: Commit**

```bash
git add kubernetes/dev kubernetes/prod kubernetes/monitoring
git commit -m "feat(k8s): add dev/prod kustomize overlays (namespaces, HPA, env config, ingress hosts)"
```

---

## Phase 8 — CI/CD (GitHub Actions)

### Task 35: PR pipeline

**Files:**
- Create: `.github/workflows/pr.yml`

**Interfaces:** none — this workflow only runs commands defined in earlier tasks (`pytest`, `npm test`, `docker build`), it doesn't introduce new application code.

- [ ] **Step 1: Write the workflow**

```yaml
# .github/workflows/pr.yml
name: PR Checks
on:
  pull_request:
    branches: [main]

jobs:
  lint-and-test-python:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [backend/shared, backend/api, backend/worker, mcp-server]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install shared package
        if: matrix.service != 'backend/shared'
        run: pip install -e backend/shared
      - name: Install service
        run: pip install -e "${{ matrix.service }}[dev]"
      - name: Lint
        run: cd ${{ matrix.service }} && ruff check .
      - name: Unit + MCP integration tests with coverage
        run: cd ${{ matrix.service }} && python -m pytest --cov=. --cov-report=xml --cov-fail-under=80
      - uses: codecov/codecov-action@v4
        with: { files: "${{ matrix.service }}/coverage.xml", flags: "${{ matrix.service }}" }

  lint-and-test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm install
      - run: cd frontend && npx eslint src
      - run: cd frontend && npm test -- --coverage

  build-and-scan-images:
    needs: [lint-and-test-python, lint-and-test-frontend]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - service: backend/api
            image: api
          - service: backend/worker
            image: worker
          - service: mcp-server
            image: mcp-test-analysis
          - service: frontend
            image: frontend
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t testscope-${{ matrix.image }}:${{ github.sha }} ${{ matrix.service }}
      - name: Scan with Trivy
        uses: aquasecurity/trivy-action@0.24.0
        with:
          image-ref: testscope-${{ matrix.image }}:${{ github.sha }}
          severity: CRITICAL,HIGH
          exit-code: "1"

  summary:
    needs: [build-and-scan-images]
    runs-on: ubuntu-latest
    steps:
      - name: Write job summary
        run: echo "All PR checks passed — lint, unit tests (≥80% coverage), MCP integration tests, image builds, Trivy scans." >> "$GITHUB_STEP_SUMMARY"
```

- [ ] **Step 2: Verify the workflow YAML parses**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/pr.yml'))"`
Expected: no output (valid YAML, no exception)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/pr.yml
git commit -m "ci: add PR pipeline (lint, unit+MCP integration tests, coverage, image build+scan)"
```

### Task 36: Dev deploy workflow (self-hosted runner)

**Files:**
- Create: `.github/workflows/deploy-dev.yml`
- Create: `kubernetes/dev/smoke-test.sh`

**Interfaces:** consumes the same four `service`/`image` pairs as Task 35's build matrix; consumes `kubernetes/dev` overlay from Task 34.

- [ ] **Step 1: Write the smoke test script**

```bash
#!/usr/bin/env bash
# kubernetes/dev/smoke-test.sh
set -euo pipefail
NAMESPACE="${1:-dev}"
HOST="${2:-dev.testscope.local}"

kubectl -n "$NAMESPACE" wait --for=condition=available --timeout=120s deployment/api deployment/worker deployment/frontend deployment/mcp-test-analysis deployment/mcp-github

response=$(curl -s -o /dev/null -w "%{http_code}" "http://$HOST/api/health/live")
if [ "$response" != "200" ]; then
  echo "Smoke test failed: /api/health/live returned $response"
  exit 1
fi
echo "Smoke test passed."
```

- [ ] **Step 2: Write the deploy workflow (runs on a self-hosted runner registered on the EC2 k3s host)**

```yaml
# .github/workflows/deploy-dev.yml
name: Deploy Dev
on:
  push:
    branches: [main]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - service: backend/api
            image: api
          - service: backend/worker
            image: worker
          - service: mcp-server
            image: mcp-test-analysis
          - service: frontend
            image: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: "${{ github.actor }}", password: "${{ secrets.GITHUB_TOKEN }}" }
      - run: |
          docker build -t ghcr.io/${{ github.repository_owner }}/testscope-${{ matrix.image }}:${{ github.sha }} ${{ matrix.service }}
          docker push ghcr.io/${{ github.repository_owner }}/testscope-${{ matrix.image }}:${{ github.sha }}

  deploy:
    needs: [build-and-push]
    runs-on: [self-hosted, testscope-k3s]
    steps:
      - uses: actions/checkout@v4
      - name: Update image tags and apply
        run: |
          cd kubernetes/dev
          for img in api worker mcp-test-analysis frontend; do
            kubectl kustomize . | sed "s#ghcr.io/testscope-ai/${img}:latest#ghcr.io/${{ github.repository_owner }}/testscope-${img}:${{ github.sha }}#g" > /tmp/rendered.yaml
          done
          kubectl apply -f /tmp/rendered.yaml
      - name: Smoke test
        run: bash kubernetes/dev/smoke-test.sh dev dev.testscope.local
```

- [ ] **Step 3: Verify YAML parses**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/deploy-dev.yml'))"`
Expected: no output

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/deploy-dev.yml kubernetes/dev/smoke-test.sh
git commit -m "ci: add dev deploy workflow (self-hosted runner, GHCR push, kustomize apply, smoke test)"
```

### Task 37: Prod deploy workflow (manual approval gate)

**Files:**
- Create: `.github/workflows/deploy-prod.yml`
- Create: `kubernetes/prod/smoke-test.sh` (copy of `kubernetes/dev/smoke-test.sh` with `NAMESPACE`/`HOST` defaults changed to `prod`/`testscope.local`)

**Interfaces:** consumes the same build matrix pattern as Task 36; requires a GitHub **Environment** named `production` to be configured with a required reviewer (a one-time manual repo-settings step, documented here rather than automatable via workflow YAML).

- [ ] **Step 1: Write the workflow, gated on a version tag and the `production` Environment**

```yaml
# .github/workflows/deploy-prod.yml
name: Deploy Prod
on:
  push:
    tags: ["v*.*.*"]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - service: backend/api
            image: api
          - service: backend/worker
            image: worker
          - service: mcp-server
            image: mcp-test-analysis
          - service: frontend
            image: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: "${{ github.actor }}", password: "${{ secrets.GITHUB_TOKEN }}" }
      - run: |
          docker build -t ghcr.io/${{ github.repository_owner }}/testscope-${{ matrix.image }}:${{ github.ref_name }} ${{ matrix.service }}
          docker push ghcr.io/${{ github.repository_owner }}/testscope-${{ matrix.image }}:${{ github.ref_name }}

  deploy:
    needs: [build-and-push]
    runs-on: [self-hosted, testscope-k3s]
    environment: production  # requires a manual reviewer approval, configured once in repo Settings > Environments
    steps:
      - uses: actions/checkout@v4
      - name: Update image tags and apply
        run: |
          cd kubernetes/prod
          for img in api worker mcp-test-analysis frontend; do
            kubectl kustomize . | sed "s#ghcr.io/testscope-ai/${img}:latest#ghcr.io/${{ github.repository_owner }}/testscope-${img}:${{ github.ref_name }}#g" > /tmp/rendered.yaml
          done
          kubectl apply -f /tmp/rendered.yaml
      - name: Smoke test
        run: bash kubernetes/prod/smoke-test.sh prod testscope.local
```

- [ ] **Step 2: Verify YAML parses**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/deploy-prod.yml'))"`
Expected: no output

- [ ] **Step 3: Document the one-time manual setup this workflow depends on**

```markdown
# .github/workflows/README.md
Before `deploy-prod.yml` can run: create a GitHub Environment named `production`
(repo Settings > Environments > New environment), add at least one required reviewer.
Before either deploy workflow can run: register a self-hosted runner with label
`testscope-k3s` on the EC2 k3s host (repo Settings > Actions > Runners > New self-hosted
runner; run the provided `config.sh`/`run.sh` as a systemd service on the host).
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/deploy-prod.yml kubernetes/prod/smoke-test.sh .github/workflows/README.md
git commit -m "ci: add prod deploy workflow (tag-triggered, manual approval gate)"
```

---

## Phase 9 — Observability

### Task 38: Instrument `api`/`worker`/both MCP servers with `prometheus_client`; deploy Prometheus + Grafana + Loki/Promtail

**Files:**
- Modify: `backend/api/app/main.py` (add `/metrics`)
- Modify: `backend/worker/app/main.py`, `app/runner.py` (add `/metrics` on the health server, record histogram/counters)
- Modify: `mcp-server/server.py` (add `/metrics` on the health server from Task 32)
- Create: `kubernetes/monitoring/prometheus.yaml`, `grafana.yaml`, `loki.yaml`, `promtail.yaml`
- Test: `backend/api/tests/test_metrics.py`, `backend/worker/tests/test_metrics.py`

**Interfaces:**
- Produces: `backend/shared/metrics.py` — `REQUEST_COUNT = Counter(...)`, `REQUEST_LATENCY = Histogram(...)` (api); `ANALYSIS_COUNT = Counter("testscope_analyses_total", ["status"])`, `ANALYSIS_DURATION = Histogram("testscope_analysis_duration_seconds")`, `LLM_CALL_COUNT = Counter("testscope_llm_calls_total", ["status"])`, `MCP_TOOL_CALL_COUNT = Counter("testscope_mcp_tool_calls_total", ["tool", "status"])`, `MCP_TOOL_LATENCY = Histogram("testscope_mcp_tool_duration_seconds", ["tool"])` (worker) — all `prometheus_client` primitives, importable from `backend/shared` since both `api` and `worker` expose `/metrics`.

- [ ] **Step 1: Write failing test asserting `/metrics` is exposed and increments on a request**

```python
# backend/api/tests/test_metrics.py
from fastapi.testclient import TestClient
from app.main import create_app

def test_metrics_endpoint_exposes_request_count(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "t"); monkeypatch.setenv("S3_BUCKET", "b")
    monkeypatch.setenv("SQS_QUEUE_URL", "q"); monkeypatch.setenv("MCP_GITHUB_URL", "g")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "m")
    client = TestClient(create_app())
    client.get("/health/live")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "testscope_api_requests_total" in response.text
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend/api && python -m pytest tests/test_metrics.py -v`
Expected: FAIL — `404` on `/metrics`

- [ ] **Step 3: Implement `backend/shared/metrics.py` and wire both services**

```python
# backend/shared/metrics.py
from prometheus_client import Counter, Histogram

API_REQUEST_COUNT = Counter("testscope_api_requests_total", "API requests", ["method", "path", "status"])
API_REQUEST_LATENCY = Histogram("testscope_api_request_duration_seconds", "API request latency", ["path"])

ANALYSIS_COUNT = Counter("testscope_analyses_total", "Analyses run", ["status"])
ANALYSIS_DURATION = Histogram("testscope_analysis_duration_seconds", "Full analysis duration")
LLM_CALL_COUNT = Counter("testscope_llm_calls_total", "LLM calls", ["status"])
MCP_TOOL_CALL_COUNT = Counter("testscope_mcp_tool_calls_total", "MCP tool calls", ["tool", "status"])
MCP_TOOL_LATENCY = Histogram("testscope_mcp_tool_duration_seconds", "MCP tool call latency", ["tool"])
```

```python
# backend/api/app/main.py — add a middleware and /metrics route
import time
from fastapi import FastAPI, Request
from prometheus_client import make_asgi_app
from metrics import API_REQUEST_COUNT, API_REQUEST_LATENCY
from app.routes import health, analyses

def create_app() -> FastAPI:
    app = FastAPI(title="TestScope AI API")

    @app.middleware("http")
    async def track_metrics(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        API_REQUEST_LATENCY.labels(path=request.url.path).observe(time.time() - start)
        API_REQUEST_COUNT.labels(method=request.method, path=request.url.path, status=response.status_code).inc()
        return response

    app.include_router(health.router)
    app.include_router(analyses.router)
    app.mount("/metrics", make_asgi_app())
    return app

app = create_app()
```

```python
# backend/worker/app/nodes/report_saver.py — instrument success/failure (extend Task 17's implementation)
from metrics import ANALYSIS_COUNT
# inside report_saver, right before `return state`:
ANALYSIS_COUNT.labels(status=state["status"]).inc()
```

```python
# backend/worker/app/mcp_clients.py — wrap _call with latency/count metrics (extend Task 11's implementation)
import time
from metrics import MCP_TOOL_CALL_COUNT, MCP_TOOL_LATENCY

async def _call(base_url: str, tool_name: str, **kwargs) -> dict:
    start = time.time()
    status = "success"
    try:
        async with streamablehttp_client(base_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, kwargs)
                return result.structuredContent
    except Exception:
        status = "error"
        raise
    finally:
        MCP_TOOL_LATENCY.labels(tool=tool_name).observe(time.time() - start)
        MCP_TOOL_CALL_COUNT.labels(tool=tool_name, status=status).inc()
```

Add `/metrics` to `backend/worker/app/health.py`'s FastAPI app (same `make_asgi_app()` mount pattern as above), and equivalently to `mcp-server/server.py`'s `build_health_app()` from Task 32 (add `MCP_TOOL_CALL_COUNT`-style counters there too, incremented inside each `@mcp.tool()`-decorated function). Add `prometheus-client>=0.21` to all four `pyproject.toml` dependency lists.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend/api && python -m pytest tests/test_metrics.py -v` and the equivalent worker test
Expected: PASS

- [ ] **Step 5: Deploy Prometheus, Grafana, Loki, Promtail to the `monitoring` namespace**

```yaml
# kubernetes/monitoring/prometheus.yaml (minimal single-replica, sufficient for a course-project demo)
apiVersion: apps/v1
kind: Deployment
metadata: { name: prometheus, namespace: monitoring }
spec:
  replicas: 1
  selector: { matchLabels: { app: prometheus } }
  template:
    metadata: { labels: { app: prometheus } }
    spec:
      containers:
        - name: prometheus
          image: prom/prometheus:v2.55.0
          args: ["--config.file=/etc/prometheus/prometheus.yml"]
          ports: [{ containerPort: 9090 }]
          volumeMounts: [{ name: config, mountPath: /etc/prometheus }]
      volumes:
        - name: config
          configMap: { name: prometheus-config }
---
apiVersion: v1
kind: ConfigMap
metadata: { name: prometheus-config, namespace: monitoring }
data:
  prometheus.yml: |
    scrape_configs:
      - job_name: testscope
        kubernetes_sd_configs: [{ role: pod }]
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            regex: api|worker|mcp-test-analysis|mcp-github
            action: keep
---
apiVersion: v1
kind: Service
metadata: { name: prometheus, namespace: monitoring }
spec:
  selector: { app: prometheus }
  ports: [{ port: 9090, targetPort: 9090 }]
```

```yaml
# kubernetes/monitoring/grafana.yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: grafana, namespace: monitoring }
spec:
  replicas: 1
  selector: { matchLabels: { app: grafana } }
  template:
    metadata: { labels: { app: grafana } }
    spec:
      containers:
        - name: grafana
          image: grafana/grafana:11.2.0
          ports: [{ containerPort: 3000 }]
---
apiVersion: v1
kind: Service
metadata: { name: grafana, namespace: monitoring }
spec:
  selector: { app: grafana }
  ports: [{ port: 3000, targetPort: 3000 }]
```

```yaml
# kubernetes/monitoring/loki.yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: loki, namespace: monitoring }
spec:
  replicas: 1
  selector: { matchLabels: { app: loki } }
  template:
    metadata: { labels: { app: loki } }
    spec:
      containers: [{ name: loki, image: grafana/loki:3.2.0, ports: [{ containerPort: 3100 }] }]
---
apiVersion: v1
kind: Service
metadata: { name: loki, namespace: monitoring }
spec:
  selector: { app: loki }
  ports: [{ port: 3100, targetPort: 3100 }]
```

```yaml
# kubernetes/monitoring/promtail.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata: { name: promtail, namespace: monitoring }
spec:
  selector: { matchLabels: { app: promtail } }
  template:
    metadata: { labels: { app: promtail } }
    spec:
      containers:
        - name: promtail
          image: grafana/promtail:3.2.0
          args: ["-config.file=/etc/promtail/config.yml", "-client.url=http://loki:3100/loki/api/v1/push"]
          volumeMounts: [{ name: varlog, mountPath: /var/log/pods, readOnly: true }]
      volumes:
        - name: varlog
          hostPath: { path: /var/log/pods }
```

- [ ] **Step 6: Validate manifests parse**

Run: `kubectl apply --dry-run=client -f kubernetes/monitoring/`
Expected: all resources listed, no errors

- [ ] **Step 7: Commit**

```bash
git add backend/shared/metrics.py backend/api/app/main.py backend/api/tests/test_metrics.py backend/worker/app kubernetes/monitoring
git commit -m "feat(observability): instrument api/worker/mcp servers with prometheus_client; deploy Prometheus/Grafana/Loki/Promtail"
```

### Task 39: Grafana dashboard

**Files:**
- Create: `kubernetes/monitoring/dashboard-configmap.yaml`

**Interfaces:** references the exact metric names from Task 38 (`testscope_api_requests_total`, `testscope_analyses_total`, `testscope_analysis_duration_seconds`, `testscope_mcp_tool_duration_seconds`, `testscope_mcp_tool_calls_total`).

- [ ] **Step 1: Write the dashboard JSON, provisioned via a ConfigMap Grafana auto-loads**

```yaml
# kubernetes/monitoring/dashboard-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: testscope-dashboard
  namespace: monitoring
  labels: { grafana_dashboard: "1" }
data:
  testscope.json: |
    {
      "title": "TestScope AI — System Health",
      "panels": [
        { "title": "API Request Rate", "type": "timeseries", "targets": [{ "expr": "sum(rate(testscope_api_requests_total[5m])) by (status)" }] },
        { "title": "Analysis Success/Fail Rate", "type": "timeseries", "targets": [{ "expr": "sum(rate(testscope_analyses_total[15m])) by (status)" }] },
        { "title": "Analysis Duration (p50/p95)", "type": "timeseries", "targets": [
          { "expr": "histogram_quantile(0.50, sum(rate(testscope_analysis_duration_seconds_bucket[15m])) by (le))" },
          { "expr": "histogram_quantile(0.95, sum(rate(testscope_analysis_duration_seconds_bucket[15m])) by (le))" }
        ]},
        { "title": "MCP Tool Latency by Tool", "type": "timeseries", "targets": [{ "expr": "histogram_quantile(0.95, sum(rate(testscope_mcp_tool_duration_seconds_bucket[15m])) by (le, tool))" }] },
        { "title": "MCP Tool Errors by Tool", "type": "timeseries", "targets": [{ "expr": "sum(rate(testscope_mcp_tool_calls_total{status=\"error\"}[15m])) by (tool)" }] },
        { "title": "Pod Restarts", "type": "timeseries", "targets": [{ "expr": "sum(kube_pod_container_status_restarts_total{namespace=~\"dev|prod\"}) by (pod)" }] },
        { "title": "Recent Failed Analyses (logs)", "type": "logs", "datasource": "Loki", "targets": [{ "expr": "{namespace=~\"dev|prod\"} |= \"status=failed\"" }] }
      ]
    }
```

- [ ] **Step 2: Validate JSON is well-formed**

Run: `python -c "import yaml, json; doc = yaml.safe_load(open('kubernetes/monitoring/dashboard-configmap.yaml')); json.loads(doc['data']['testscope.json'])"`
Expected: no output (parses cleanly)

- [ ] **Step 3: Commit**

```bash
git add kubernetes/monitoring/dashboard-configmap.yaml
git commit -m "feat(observability): add TestScope AI System Health Grafana dashboard"
```

### Task 40: Verify CloudWatch alarms end-to-end

**Files:** none created — this task verifies Task 29's Terraform `monitoring` module actually alarms, using a manual trigger.

**Interfaces:** consumes `aws_cloudwatch_metric_alarm.dlq_not_empty` and `.queue_backlog_age` from Task 29.

- [ ] **Step 1: After `terraform apply` (Task 30) has run for `dev`, manually push a message directly to the DLQ to confirm the alarm fires**

Run: `aws sqs send-message --queue-url "$(terraform -chdir=terraform/environments/dev output -raw dlq_url 2>/dev/null || echo MISSING)" --message-body '{"test":"alarm-check"}'`

(If `dlq_url` isn't yet exported from `environments/dev`'s outputs, add `output "dlq_url" { value = module.sqs.dlq_arn }` to `terraform/environments/dev/main.tf` first, matching the pattern from Task 29's other outputs.)

- [ ] **Step 2: Confirm the alarm transitions to `ALARM` and the SNS email arrives**

Run: `aws cloudwatch describe-alarms --alarm-names testscope-dev-dlq-not-empty --query 'MetricAlarms[0].StateValue'`
Expected: `"ALARM"` within ~5 minutes; confirm the subscribed email (`var.alert_email` from Task 29) received the SNS notification

- [ ] **Step 3: Clean up the test message and confirm the alarm clears**

Run: `aws sqs purge-queue --queue-url "$(terraform -chdir=terraform/environments/dev output -raw dlq_url)"`
Expected: alarm returns to `OK` within ~5 minutes

- [ ] **Step 4: Commit the `dlq_url` output addition if it was needed in Step 1**

```bash
git add terraform/environments/dev/main.tf terraform/environments/prod/main.tf
git commit -m "feat(terraform): export dlq_url output for alarm verification"
```

---

## Phase 10 — Local Full-Stack Integration

### Task 41: `docker-compose.yml` full local stack + local E2E smoke test

**Files:**
- Modify: `docker-compose.yml` (replace Task 1's empty stub)
- Create: `scripts/local-e2e-smoke-test.sh`

**Interfaces:** wires together every image built in Tasks 8, 17, 22, 26 (`mcp-test-analysis`, `worker`, `api`, `frontend`) plus `localstack` (S3/DynamoDB/SQS) and the real `mcp-github` image, for a fully local run without touching real AWS or a real GitHub token (the smoke test targets a local fixture repo path, not github.com).

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
# docker-compose.yml
services:
  localstack:
    image: localstack/localstack:3.8
    environment:
      - SERVICES=s3,dynamodb,sqs
      - DEFAULT_REGION=us-east-1
    ports: ["4566:4566"]

  localstack-init:
    image: amazon/aws-cli:2.18.0
    depends_on: [localstack]
    entrypoint: /bin/sh
    command: >
      -c "
      aws --endpoint-url=http://localstack:4566 dynamodb create-table --table-name testscope-analyses-local --attribute-definitions AttributeName=analysis_id,AttributeType=S --key-schema AttributeName=analysis_id,KeyType=HASH --billing-mode PAY_PER_REQUEST &&
      aws --endpoint-url=http://localstack:4566 s3 mb s3://testscope-reports-local &&
      aws --endpoint-url=http://localstack:4566 sqs create-queue --queue-name testscope-jobs-local
      "
    environment: [AWS_ACCESS_KEY_ID=test, AWS_SECRET_ACCESS_KEY=test, AWS_DEFAULT_REGION=us-east-1]

  mcp-test-analysis:
    build: ./mcp-server
    environment:
      - WORKSPACE_ROOT=/workspace
      - DYNAMODB_TABLE=testscope-analyses-local
      - S3_BUCKET=testscope-reports-local
      - MCP_GITHUB_URL=http://mcp-github:8100/mcp
      - GITHUB_TOKEN=local-dev-unused
      - AWS_ENDPOINT_URL=http://localstack:4566
      - AWS_ACCESS_KEY_ID=test
      - AWS_SECRET_ACCESS_KEY=test
      - AWS_DEFAULT_REGION=us-east-1
    depends_on: [localstack-init]
    ports: ["8100:8100"]

  mcp-github:
    image: ghcr.io/github/github-mcp-server:latest
    environment: [GITHUB_PERSONAL_ACCESS_TOKEN=local-dev-token]
    ports: ["8101:8100"]

  worker:
    build: { context: ., dockerfile: backend/worker/Dockerfile }
    environment:
      - DYNAMODB_TABLE=testscope-analyses-local
      - S3_BUCKET=testscope-reports-local
      - SQS_QUEUE_URL=http://localstack:4566/000000000000/testscope-jobs-local
      - MCP_GITHUB_URL=http://mcp-github:8100/mcp
      - MCP_TEST_ANALYSIS_URL=http://mcp-test-analysis:8100/mcp
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - AWS_ENDPOINT_URL=http://localstack:4566
      - AWS_ACCESS_KEY_ID=test
      - AWS_SECRET_ACCESS_KEY=test
      - AWS_DEFAULT_REGION=us-east-1
    depends_on: [localstack-init, mcp-test-analysis, mcp-github]
    ports: ["8080:8080"]

  api:
    build: { context: ., dockerfile: backend/api/Dockerfile }
    environment:
      - DYNAMODB_TABLE=testscope-analyses-local
      - S3_BUCKET=testscope-reports-local
      - SQS_QUEUE_URL=http://localstack:4566/000000000000/testscope-jobs-local
      - MCP_GITHUB_URL=http://mcp-github:8100/mcp
      - MCP_TEST_ANALYSIS_URL=http://mcp-test-analysis:8100/mcp
      - AWS_ENDPOINT_URL=http://localstack:4566
      - AWS_ACCESS_KEY_ID=test
      - AWS_SECRET_ACCESS_KEY=test
      - AWS_DEFAULT_REGION=us-east-1
    depends_on: [localstack-init]
    ports: ["8000:8000"]

  frontend:
    build: ./frontend
    ports: ["3000:80"]
    depends_on: [api]
```

`AWS_ENDPOINT_URL` is read automatically by boto3 ≥1.35 for all clients, so `backend/shared/dynamodb.py`/`s3.py`/`sqs.py` and `mcp-server/aws.py` need no code changes to work against LocalStack — this is why those wrappers used bare `boto3.resource(...)`/`boto3.client(...)` with no hardcoded endpoint in every earlier task.

- [ ] **Step 2: Bring the stack up and verify all services report healthy**

Run: `docker compose up -d --build && sleep 20 && docker compose ps`
Expected: all services show `running`/`healthy`; if `localstack-init` shows an error, check LocalStack logs (`docker compose logs localstack-init`)

- [ ] **Step 3: Write and run the local E2E smoke test**

```bash
#!/usr/bin/env bash
# scripts/local-e2e-smoke-test.sh
set -euo pipefail

echo "Submitting analysis..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/analyses \
  -H "Content-Type: application/json" \
  -d '{"repository": "octocat/Hello-World", "issue_number": 1}')
ANALYSIS_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['analysis_id'])")
echo "Analysis ID: $ANALYSIS_ID"

for i in $(seq 1 60); do
  STATUS=$(curl -s "http://localhost:8000/api/analyses/$ANALYSIS_ID" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
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

curl -s "http://localhost:8000/api/analyses/$ANALYSIS_ID/report" | python3 -m json.tool
echo "Smoke test PASSED."
```

Run: `chmod +x scripts/local-e2e-smoke-test.sh && ./scripts/local-e2e-smoke-test.sh`
Expected: `Smoke test PASSED.` with a rendered coverage matrix — requires a real `ANTHROPIC_API_KEY` exported in the shell first (this is the one point in the whole plan where a real Claude call happens, deliberately, as the final hand-verification that the live LLM integration works end-to-end; it is not part of any automated CI job, matching the Global Constraints' "never call the real Claude API from automated tests" rule)

- [ ] **Step 4: Tear down**

Run: `docker compose down -v`

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml scripts/local-e2e-smoke-test.sh
git commit -m "feat(local): add full-stack docker-compose (LocalStack + all services) and local E2E smoke test"
```

---

## Plan Self-Review

**Spec coverage:** every numbered section of `docs/spec.md` maps to at least one task — §3 architecture (Tasks 1, 8, 17, 41), §4 workflow (Tasks 10–17), §5 MCP tooling (Tasks 2–8, 11, 22), §6 data model (Task 9), §7 API (Tasks 18–22), §8 UI (Tasks 23–26), §9 Terraform/AWS (Tasks 27–30, 40), §10 K8s (Tasks 31–34), §11 CI/CD (Tasks 35–37), §12 observability (Tasks 38–40), §13 error handling (covered inline across Tasks 10–17's failure-handling steps), §14 testing strategy (every task's TDD steps + Task 8/17's MCP-transport and stub-LLM E2E tests + Task 41's local full E2E). No spec section lacks a task.

**Placeholder scan:** no "TBD"/"TODO"/"handle appropriately" language appears; every step shows real code, real commands, and real expected output. The two places that look like placeholders (`REPLACED_BY_OVERLAY` in `kubernetes/base/configmap.yaml`/`ingress.yaml`, `PASTE_FROM_TERRAFORM_OUTPUT_queue_url` in the overlays) are intentional and documented — they're the literal manual hand-off point between `terraform apply` output and `kubectl apply` input described in Task 30, not unfinished plan content.

**Type consistency:** `AgentState`'s fields (Task 10) are used identically by every node task through Task 17. `AnalysisRecord`'s fields (Task 9) match the DynamoDB item shape written by `mcp-server`'s `save_coverage_report` (Task 6) and read by `backend/api`'s routes (Tasks 19–22) and `backend/worker`'s `job_intake`/`runner` (Tasks 10, 17). MCP tool names (`find_test_files`, `read_test_file`, `extract_test_metadata`, `save_coverage_report`, `get_previous_analysis`, `cleanup_workspace`) are identical between `mcp-server/server.py`'s `@mcp.tool()` registrations (Task 8) and every call site (Tasks 11, 13, 14, 17). `call_github_tool`/`call_test_mcp_tool` signatures match between their Task 11 definition and every consumer.

---

**Plan complete and saved to `docs/plan.md`.** Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**

