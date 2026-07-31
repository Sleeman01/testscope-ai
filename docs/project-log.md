# TestScope AI — Project Log

A running log of implementation progress, decisions, and deviations — kept so any new
Claude Code or Claude Desktop session can get up to speed quickly, and as a record for
the presentation's "how did you use AI" slide.

Update this after each phase (or whenever something worth remembering happens).

---

## How to use this file

- **Starting a new Claude Code session?** No need to paste this in — it reads the repo
  directly (plan.md, design.md, git log).
- **Starting a new Claude Desktop chat?** Paste the "Current State" section below at the
  start of the conversation so context carries over.

---

## Current State

**Phase:** 0 (complete, merged) → 1 (Tasks 2–8 all complete, not yet merged) → Phase 2
(`backend/shared`, Task 9) not started
**Branch pattern in use:** `feature/phase-<N>-<short-description>`, one PR per phase (docs-only
housekeeping like this entry uses `docs/<short-description>` instead)
**Current branch:** `feature/phase-1-mcp-test-analysis-server` (not yet merged to `main`)
**Last merged:** `docs/claude-md` → `main` (PR #8)
**mcp-server test suite:** 17/17 passing, 90% coverage (`--cov=. --cov-report=term-missing`
from `mcp-server/`), comfortably above the 80% target.
**Read before starting Task 9:** `docs/2026-07-30-testscope-ai-design.md` §5.2 — the GitHub
MCP tool-name assumptions there were found wrong during Task 8's live verification (see
Phase 1 entry below); Task 9 itself is unaffected (no GitHub MCP calls), but anyone
starting Phase 3 (Task 11) or Task 22 must read that section first, not spec's original text.

---

## Standing Decisions & Working Preferences

- Never commit/push directly to `main` — always branch first, PR + review before merge.
- One Claude Code chat session per phase (fresh context); reads plan.md/design.md +
  git log to catch up, no manual summaries needed.
- Model choice: default Sonnet; switch to Opus only when a task is genuinely stuck
  (real debugging, ambiguity, security-sensitive code); Haiku rarely needed.
- Any deviation from the plan's literal text must be flagged and explained before
  proceeding, not silently made.
- Dependency version bumps (e.g. npm audit fixes) require explicit approval —
  not auto-applied, even to fix vulnerabilities, since the plan is a reviewed document.
- Python dependencies must always go into the project's `.venv` (`source .venv/bin/activate`
  before any `pip install`) — never system Python.
- Course requirement: `docs/spec.md`/`docs/plan.md` were renamed to the Superpowers dated
  convention (`docs/2026-07-30-testscope-ai-design.md` / `-plan.md`) per instructor's
  explicit approval — documented in PR #2's description.

---

## Phase Log

### Phase 0 — Repo Scaffolding (Task 1) ✅ merged
- Editable-install package structure for `api`, `worker`, `shared`, `mcp-server`.
- Smoke tests for all 4 Python packages + frontend (Vitest). Docker-compose stub validated.
- **Deviation:** `shared`/`mcp-server` smoke tests use `importlib.metadata.version(...)`
  instead of `import app`, since those packages have no `app/` subdirectory (flat layout).
  Approved.
- **Security decision:** 7 npm audit findings (vitest/vite/esbuild — dev-only, unreachable;
  react-router-dom — accepted given no-auth/internal-only v1 scope) documented as accepted
  v1 limitations, not fixed. No version bumps taken.
- **Process fix:** discovered packages were installed into system Python, not an isolated
  venv. Fixed via a separate small PR (`fix/venv-isolation`) — `.venv` now required, documented
  in README.

### Phase 1 — Custom MCP Server (`mcp-test-analysis`) — ✅ complete (Tasks 2–8)
- Branch: `feature/phase-1-mcp-test-analysis-server`
- **Tasks 2–7 ✅** (`extract_test_metadata` → `find_test_files`/`WorkspaceManager` →
  `read_test_file` → `cleanup_workspace`/sweeper → `save_coverage_report` →
  `get_previous_analysis`), all TDD, full suite green after each task.
  - **Deviation (Task 3):** `mcp-server/github_client.py` didn't exist as a Files-list
    target with any shown content in Task 3's own steps, even though Task 8 called it
    "created in Task 3 as an interface stub." Added a minimal stub (`GithubClient` class,
    `get_repo_size_bytes` raising `NotImplementedError`) matching Task 8's eventual real
    shape — approved.
  - **Bug fix (Tasks 6 & 7):** `save_coverage_report`'s and `get_previous_analysis`'s test
    fixture both passed a native Python `float` for `coverage_summary.percent_covered`
    straight into `boto3`'s DynamoDB resource `put_item` — that API rejects floats outright
    (`TypeError: Float types are not supported. Use Decimal types instead.`). Fixed by
    wrapping in `Decimal` in both the implementation and the Task 7 fixture (pre-empted
    before running, once the Task 6 failure was already confirmed).
  - **Deviation (Task 6):** added the `mcp-server/tests/fixtures/sample_analysis_record.json`
    fixture that Task 6's interfaces text promised (kept in sync with Task 9's
    `backend/shared` copy) but that no step in Task 6 actually created — approved.
- **Task 8 ✅ (server wiring, `github_client.py` real implementation, MCP integration test)
  — major plan corrections found during live verification, all approved. Phase 1
  (Tasks 2–8) is now fully complete:**
  - **mcp-github's real deployed image (`ghcr.io/github/github-mcp-server:latest`, `v1.8.0`)
    exposes none of the tool names spec §5.2 assumed.** Verified against the live server
    (default toolset and `--toolsets=all`, 54 tools checked): `get_repository`, `get_issue`,
    `get_issue_comments`, `create_issue` do not exist under those names, in any toolset.
    Full findings, substitute-tool table, and the standing architectural decision (issue
    body fetch bypasses MCP via a direct GitHub REST call, since no MCP tool on this server
    returns a single issue's body) are recorded in
    `docs/2026-07-30-testscope-ai-design.md` §5.2 — read that before touching Task 11 or 22.
    `mcp-server/github_client.py` itself only ever needed `get_repo_size_bytes` (its one
    real caller, `find_test_files`); it has no issue-related methods — those belong to
    Task 11's/22's separate, not-yet-built MCP clients.
  - **Docker/auth setup also required correction:** the plain `docker run ... github-mcp-server`
    invocation plan.md showed starts an **stdio** server, not HTTP — exits immediately when
    run detached. Needs the `http --port 8100 --listen-host 0.0.0.0` subcommand. HTTP mode
    also requires the token as an `Authorization: Bearer <token>` header per request; the
    `GITHUB_PERSONAL_ACCESS_TOKEN` env var alone gets a 401.
  - **Installed `mcp` Python SDK resolved to `2.0.0`** (plan.md's `pyproject.toml` only
    pinned `mcp>=1.1`, an unpinned major-version jump that turned out to carry breaking
    changes) — `mcp.server.fastmcp.FastMCP` doesn't exist in this version at all; it's
    `mcp.server.MCPServer` (same `.tool()`/`.run()` pattern, but `.run(transport=...)`
    needs explicit `host=`/`port=` kwargs). Client-side: `streamablehttp_client` →
    `streamable_http_client` (now yields a 2-tuple, not 3), `Tool.inputSchema` →
    `Tool.input_schema`, `CallToolResult.structuredContent` → `structured_content`.
    **`structured_content` is `None` for any `-> dict`-annotated tool** — confirmed for
    *both* `mcp-github`'s tools and `mcp-server`'s own (all `-> dict`); it's general SDK
    behavior (no schema to derive structured output from), not an external-server quirk as
    first assumed — payload comes back as JSON text in `content[0].text` instead, parsed by
    a small `_payload()`/inline helper everywhere it's needed. All plan.md code snippets
    referencing these (Tasks 3, 8, 11, 17, 22, 39) were corrected in place; Tasks 11/14/19/22's
    *tool names* were left flagged as stale rather than redesigned now, since those tasks
    aren't built yet.
  - **Two more findings only surfaced by actually running the integration test, not from
    API docs alone:** the test subprocess's real startup latency (heavier imports — boto3,
    GitPython, the mcp/uvicorn/starlette stack) measured ~5-6s in this environment, not the
    plan's original `time.sleep(1.0)` — bumped to `8.0`. And `github_client.py`'s real
    `search_repositories`-parsing logic had **zero test coverage** — Task 3's `find_test_files`
    test mocks the GitHub client entirely, and the integration test can't hit a live GitHub
    server by design (hermetic/offline CI) — so nothing in the original plan actually
    exercised the new code. Added `mcp-server/tests/test_github_client.py` (mocks the MCP
    transport boundary) to close the gap; suite went from 85%→90% overall.
  - PAT used for verification was a disposable, read-only-scoped fine-grained token
    (`Contents: read` + `Issues: read`), supplied via a scratchpad env file outside the repo
    tree, referenced by `docker run --env-file`/`httpx2` headers without ever being printed
    to the transcript, and deleted immediately after verification completed.

---

## Open Questions / Things to Revisit

- **Correction to Phase 0's "process fix" entry above** (its literal wording is left as the
  contemporaneous record; this is the verified follow-up, per CLAUDE.md's "don't trust the
  log's claims if out of sync with the repo" rule). Re-checked by running `which python`,
  `which python3`, `python3 -m pip show boto3`, and inspecting package locations directly:
  1. **True system `dist-packages` was never touched.** `/usr/lib/python3/dist-packages`
     has no `boto3`/`testscope-*` and no matching `dpkg` package — ruled out entirely.
  2. **The real risk was PEP 668 not blocking user-site (`~/.local`) resolution.** This
     machine's `EXTERNALLY-MANAGED` marker blocks bare system-wide `pip install`, but a
     pre-existing personal toolkit already sits in `~/.local/lib/python3.12/site-packages`
     (boto3, mcp, pydantic, httpx, paramiko, etc. — dated ~6 days before this repo's first
     commit, unrelated to this project). Without an active `.venv`, a bare `python3`/`pip3`
     command silently resolves against that unrelated, unpinned copy instead of erroring —
     creating false confidence that "it's installed" when the project's own editable
     packages aren't on the path at all.
  3. **`.venv` correctly isolates the project.** Confirmed via `.venv/pyvenv.cfg`
     (`include-system-site-packages = false`) and by checking package locations directly:
     `.venv` has its own independent `boto3` (pulled in by `testscope-api`/`-worker`/
     `-shared`/`-mcp`/`moto`), and all four `testscope-*` packages exist only inside
     `.venv`, never in system or user site-packages.

  Net: the `fix/venv-isolation` PR's outcome (require `.venv`, check `which python` first)
  was the right call, just for this more precise reason — not "system Python pollution,"
  but "silent fallback to an unrelated pre-existing toolkit masking a missing venv."