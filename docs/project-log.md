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

**Phase:** 0 (complete, merged) → 1 (Tasks 2–8, complete, merged to `main`) → 2
(`backend/shared`, Task 9, complete, merged to `main`) → Phase 3 (`backend/worker`, Task 10)
complete, not yet merged
**Branch pattern in use:** `feature/phase-<N>-<short-description>`, one PR per phase (docs-only
housekeeping like this entry uses `docs/<short-description>` instead)
**Current branch:** `feature/phase-3-backend-worker` (cut from `main` after Phase 2's merge;
not yet merged). **Phase 3 (Tasks 10–17) is now fully complete on this branch — all 8 tasks
done, not yet merged. Recommend a Phase 3 health check (see entry below) before merging.**
**Last merged:** Phase 2 (Task 9, `backend/shared`) → `main`.
**mcp-server test suite:** 17/17 passing, 90% coverage (`--cov=. --cov-report=term-missing`
from `mcp-server/`), comfortably above the 80% target.
**backend/shared test suite (Task 9):** 12/12 passing, 100% coverage (`--cov=. --cov-report=term-missing`
from `backend/shared/`). Re-verified after Task 10's `pyproject.toml` fix (see Phase 3 entry
below) — still 12/12, 100%; re-verified again via a fresh uninstall/reinstall from outside
`backend/shared` before starting Task 11 (see Phase 3 entry below).
**backend/worker test suite (Tasks 10–17, Phase 3 complete):** 36/36 passing (stable across
repeated runs), 94% overall coverage (`--cov=. --cov-report=term-missing` from
`backend/worker/`) — every node/client/graph/runner file at 100% except `app/health.py`/
`app/main.py` (still deliberately untested — see Task 17 entry below) and `app/llm_client.py`
(deliberately deferred to a stub-LLM E2E path per Task 12's own plan text, and the E2E test
that exists does exercise it, just not in isolation). `app/runner.py` is 93% (only the
600s-real-timeout branch itself is impractical to unit test; its exception-handling path
now has a dedicated fast test). Confirmed via a full state-key audit that every key any node
writes to `AgentState` is declared in `app/state.py`'s `TypedDict` (was not true before this
task — see below). `backend/worker/Dockerfile` builds cleanly and its image's module tree/graph
wiring were verified by actually running `docker build` + `docker run ... python -c "import
app.main; app.graph.build_graph()..."` inside the built image, not just trusting the snippet.
**`backend/worker/pyproject.toml` now has `[tool.pytest.ini_options] testpaths = ["tests"]`**
(added in Task 13, see entry below) — anyone adding a new `app/nodes/*.py` file in a future
task should check whether its name collides with pytest's `test_*` discovery glob before
assuming a bare `python -m pytest` run from `backend/worker/` behaves as expected.
**Read before starting Task 12+:** `docs/2026-07-30-testscope-ai-design.md` §5.2 — the GitHub
MCP tool-name assumptions there were found wrong during Task 8's live verification (see Phase 1
entry below); Task 11 (Phase 3 entry below) already redesigned `request_validator`/
`requirement_retriever` against the substitute-tool table, so Task 12+ can treat
`app/mcp_clients.py`'s `call_github_tool`/`call_test_mcp_tool` as a settled, correct interface —
no further §5.2 rework needed at the client layer, only new tool names per node as needed.

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

### Phase 2 — `backend/shared` (Task 9: config, AWS client wrappers, `AnalysisRecord`) — ✅ complete
- Branch: `feature/phase-2-backend-shared`, cut from `main` after Phase 1's merge.
- TDD throughout: `models.py`/fixture → `config.py` → `dynamodb.py` (`AnalysisStore`) →
  `s3.py` (`ReportStore`) → `sqs.py` (`JobQueue`), each with a verified-failing test first.
  Full suite: 12/12 passing, **100%** coverage (`--cov=. --cov-report=term-missing`).
- **Pre-emptive fix (not a deviation — already in the plan's own Step 3 text):** added
  `pydantic-settings>=2.6` to `backend/shared/pyproject.toml`; `config.py`'s
  `from pydantic_settings import BaseSettings` would otherwise `ModuleNotFoundError` since
  only bare `pydantic` was listed. Flagged before starting per CLAUDE.md, but on inspection
  the plan document itself already calls for this addition — so implemented as written, not
  as a silent addition.
- **Deviation (approved by precedent, not literal plan text):** `AnalysisStore.upsert`
  round-trips `record.model_dump()` through `json.dumps`/`json.loads(parse_float=Decimal)`
  before `put_item`, and a 5th test (`test_upsert_coerces_float_coverage_summary_for_dynamodb`)
  was added beyond the plan's literal 4 `test_dynamodb.py` cases. Reason: `coverage_summary`
  is a bare `dict` that can carry a native float (e.g. straight from the shared fixture's
  `percent_covered: 80.0`), and boto3's DynamoDB `put_item` rejects floats outright — the
  exact bug already hit and fixed in Tasks 6 & 7 (see Phase 1 above). Pre-empted here rather
  than waiting to rediscover it, consistent with how Task 7 pre-empted Task 6's finding.
- **Addition beyond the plan's literal file list:** `tests/test_config.py` — the plan's Task 9
  steps never exercise `config.py`/`get_settings()` (no test file for it is listed), leaving
  it at 0% coverage even though it's the file whose new dependency needed the fix above. Added
  one test proving `get_settings()` actually loads required fields from env vars (not just
  that the import succeeds), since that was the one thing this session couldn't take on faith.
- **Housekeeping correction:** this file's "Current State" said Phase 1 was "not yet merged";
  `git log main` showed it already had been (merged outside this session). Corrected above.
- `ruff check .` reports 10 pre-existing import-sort (`I001`) warnings, matching the same
  style already present and unfixed in `mcp-server` (36 warnings there) — not a new
  regression, left as-is rather than reformatting away from the plan's literal snippets.

### Phase 3 — `backend/worker` (LangGraph Agent) — Task 10 ✅ complete, 7 tasks remain (11–17)

- Branch: `feature/phase-3-backend-worker`, cut from `main` after Phase 2's merge.
- **Task 10 (worker skeleton — `AgentState`, `job_intake` node, health endpoint, poll-loop
  skeleton) ✅**, TDD: one failing `test_job_intake.py` (verified `ModuleNotFoundError`) →
  `app/state.py` + `app/nodes/job_intake.py` implemented verbatim from plan.md → 2/2 passing.
  `app/health.py`/`app/main.py` added as unit-untested skeleton per the plan's own Step 5 text
  (explicitly deferred to Task 17's E2E wiring). Full worker suite: 3/3 passing.
- **Blocker found and fixed (deviation, not in Task 10's literal file list) —
  `backend/shared`'s editable install was silently broken:** `pip install -e ../shared` from
  `backend/worker` succeeded with **zero errors** but produced an **empty module mapping** in
  the generated `__editable___testscope_shared_*_finder.py` — none of `config`/`dynamodb`/
  `models`/`s3`/`sqs` were actually importable outside `backend/shared`'s own directory.
  Root cause: `backend/shared/pyproject.toml` has no `[tool.setuptools]` package-discovery
  config, and setuptools' flat-layout auto-discovery can't disambiguate 5 top-level `.py`
  modules on its own — it silently discovers nothing rather than erroring (confirmed via a
  direct `pip install -e ../shared[dev]` rebuild, which *did* error explicitly:
  `Multiple top-level modules discovered in a flat-layout`). Task 9's own test suite never
  caught this because `python -m pytest` run from inside `backend/shared/` resolves imports
  via the cwd, not the installed package — so 100% coverage there gave false confidence.
  **Fix:** added `[tool.setuptools]\npy-modules = ["config", "dynamodb", "models", "s3", "sqs"]`
  to `backend/shared/pyproject.toml`, reinstalled, confirmed the finder's `MAPPING` populates
  correctly and `import dynamodb`/`models`/etc. now work from `backend/worker` (and from
  outside `backend/shared` generally). Re-ran `backend/shared`'s own suite afterward (still
  12/12, 100%) plus `backend/api` and `mcp-server` suites (unaffected) to confirm no
  regression. This was necessary for Task 10's own plan-specified imports
  (`from dynamodb import AnalysisStore`, `from models import AnalysisRecord`) to work at all
  — flagged here rather than silently patched, per CLAUDE.md.
- **Task 10 Step 0 (install wiring), implemented as a separate install step, not a
  `pyproject.toml` dependency entry:** `backend/worker/pyproject.toml` can't portably declare
  a relative sibling path in `[project.dependencies]`, and Task 36's own CI workflow text
  (`pip install -e backend/shared` as a distinct step before `pip install -e "<service>[dev]"`)
  already establishes this project's convention of a separate install command rather than an
  embedded path dependency. Added a comment documenting the local dev install order to
  `backend/worker/pyproject.toml`, added `fastapi`/`uvicorn` to its `dependencies` list (exact
  versions matching `backend/api`'s existing pins, no bump), and updated the root `README.md`'s
  worker install line to `pip install -e ../shared && pip install -e ../shared[dev] && pip
  install -e ".[dev]"` per the plan's literal Step 0 text (both the non-dev and dev extra
  installs, as written).
- `ruff check .` on `backend/worker` reports 5 import-sort (`I001`) warnings and 1 `UP017`
  (`datetime.UTC` alias) warning — all in code copied verbatim from plan.md's own snippets.
  Left as-is, same precedent as Phase 1/Phase 2's pre-existing `I001` warnings (not a new
  regression, not worth diverging from the plan's literal snippets over a style-only lint rule).
- **Task 11 (retry utility, MCP client wrapper, Request Validator, Requirement Retriever) ✅**,
  TDD throughout. `retry.py` and `app/mcp_clients.py`'s retry/classification mechanics
  implemented verbatim from plan.md (tool-name-agnostic, not affected by the staleness below).
  Full worker suite after Task 11: 18/18 passing, every Task 10/11 file at 100% coverage except
  the three files Task 10 explicitly deferred to Task 17.
- **Verified before starting (per the user's explicit ask): the Task 10 `backend/shared`
  `py-modules` fix lists every real module** (`config`, `dynamodb`, `models`, `s3`, `sqs` — the
  package's only top-level `.py` files besides `__init__.py`, which nothing in the codebase
  imports as a package name). Re-confirmed with a from-scratch check: uninstalled
  `testscope-shared` entirely, confirmed `import dynamodb` then failed, reinstalled with
  `pip install -e backend/shared` run from the repo root (not `backend/shared`), then imported
  all 5 modules from the scratchpad directory — fully outside both `backend/shared` and
  `backend/worker` — confirming the fix isn't cwd-dependent. `backend/worker`'s suite re-run
  clean afterward.
- **Deviation, plan-directed (not silent):** plan.md's own Task 11 text explicitly flags its
  `mcp_clients.py`/`request_validator.py`/`requirement_retriever.py` code snippets as showing
  "the plan's original (now known-wrong) tool names deliberately" and instructs
  "whoever implements this task for real must first re-read design.md §5.2's substitute-tool
  table... and redesign accordingly." Implemented per that instruction, not the literal snippets:
  - `app/nodes/request_validator.py`: uses `search_repositories` (`query: f"repo:{owner}/{repo}"`,
    `minimal_output: False`) instead of the non-existent `get_repository`; since it's a search
    endpoint (not a direct lookup), a real "not found" surfaces as a zero-`items` success
    response rather than a tool-level exception — handled as its own `status=failed` branch,
    distinct from the exception-catching branch for genuine tool errors. Added a 3rd test
    (`test_fails_gracefully_when_search_returns_zero_items`) beyond the plan's literal 2, to
    cover this response-shape difference from the stale snippet's assumptions.
  - `app/nodes/requirement_retriever.py`: issue body is fetched via a direct GitHub REST call
    (`GET https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}`,
    `Authorization: Bearer <token>` from `os.environ["GITHUB_TOKEN"]`) per design.md §5.2's
    standing architectural decision — no MCP tool returns a body by direct lookup. Comments still
    route through MCP via `call_github_tool("issue_read", method="get_comments", ...)`. Used
    `httpx2` (not plain `httpx`) for the REST call — confirmed API-compatible
    (`AsyncClient.get`/`Response.raise_for_status`/`.json()`) before relying on it; it's already
    a transitive dependency of the `mcp` 2.0.0 SDK (same package `mcp-server/github_client.py`
    already uses for its own GitHub calls), not a new dependency addition. Added a 3rd test
    (`test_fails_gracefully_when_issue_body_fetch_fails`) beyond the plan's literal 2, since
    design.md documents a fallback for comments-fetch failure but not for body-fetch failure —
    mirrors `request_validator`'s own catch-and-fail pattern for consistency.
  - **Bug pre-empted, not just tool names:** plan.md's Task 11 `mcp_clients.py` snippet still
    reads `result.structured_content`, but design.md §5.2 separately documents that this is
    `None` for both `mcp-github`'s and `mcp-server`'s dict-returning tools, and explicitly says
    "Tasks 11/22's future MCP clients should [parse `content[0].text` as JSON] rather than
    assume it's populated." Fixed in `_call_once` before writing any test against it, matching
    `mcp-server/github_client.py`'s established pattern — not caught by the plan's own
    `test_mcp_clients.py` snippet, since it mocks `_call_once` out entirely.
- **Coverage gap closed proactively, matching Phase 1's `test_github_client.py` precedent:**
  the plan's own test snippets mock `_call_once` and (necessarily, since it's new) would have
  left `_fetch_issue_body` similarly mocked-only, leaving their real transport/parsing logic at
  0% coverage. Added `test_call_once_parses_json_text_payload_over_the_real_mcp_transport`
  (mocks `streamable_http_client`/`ClientSession` at the transport boundary, same style as
  `mcp-server/tests/test_github_client.py`), `test_fetch_issue_body_calls_the_real_github_rest_api`
  (mocks `httpx2.AsyncClient` at the transport boundary), and
  `test_call_test_mcp_tool_routes_to_the_test_analysis_mcp_url` (no node calls
  `call_test_mcp_tool` yet — its callers are Tasks 13/14/15/17 — so this closes the gap directly
  rather than leaving it uncovered until those tasks exist). Result: every Task 11 file at 100%.
- **Test-only gap, not fixed:** `test_mcp_clients.py`'s `get_settings()` calls needed
  `monkeypatch.setenv(...)` + `get_settings.cache_clear()` for all 5 required `Settings` fields
  (only `mcp_github_url` is actually used) — the plan's literal Step 4 snippet omits this
  entirely and would fail with a `pydantic` `ValidationError`, not the intended assertion.
  Same fix pattern as `backend/shared/tests/test_config.py` (`get_settings` is `@lru_cache`d
  across the whole test session, so env vars alone aren't enough without an explicit
  `cache_clear()`).
- **Task 12 (LLM client wrapper, Requirement Parser node) ✅**, implemented verbatim from
  plan.md — no staleness found here (unlike Task 11's GitHub tool names). Checked the installed
  `anthropic` SDK (`0.120.2`, plan pins `anthropic>=0.39`) directly against
  `AsyncAnthropic.messages.create`'s real signature before implementing, given the `mcp` SDK's
  own `>=1.1`-pin-resolved-to-a-breaking-major-version experience in Phase 1/Task 11 — no
  mismatch found (`model`/`messages`/`max_tokens`/`system`/`tools`/`tool_choice` all present as
  documented). TDD: 2/2 tests from the plan's own Step 1 snippet, verified failing
  (`ModuleNotFoundError`) then passing unchanged. Full worker suite: 20/20 passing.
- **No coverage-closing test added for `llm_client.py` (42% coverage, unlike Task 11's
  `mcp_clients.py`/`requirement_retriever.py` gaps)** — this one is deliberate and pre-declared
  in the plan's own Task 12 file list ("`call_llm`'s ... Anthropic-specific forced-tool-use
  behavior is exercised indirectly through every node test that mocks it ... no dedicated
  `llm_client` test needed") and matches design.md's stated E2E strategy (a stub LLM client
  returning canned JSON, not live Claude calls, wired in Task 17) — not an accidental gap like
  Task 11's `_call_once`/`_fetch_issue_body`, which the plan's own snippets left untested without
  saying so.
- **Task 13 (Test Search Planner, Test File Retriever, Test File Classifier nodes) ✅.** Verified
  `find_test_files`/`extract_test_metadata`'s real return shapes (`{"files": [...]}`,
  `{"tests": [...]}`) against `mcp-server`'s actual Phase 1 implementation before
  implementing — this is this project's own MCP server (not the external `mcp-github` server
  Task 11 had staleness problems with), and matched the plan's assumptions exactly, so all
  three nodes implemented verbatim from plan.md.
- **Real blocker found and fixed, not flagged anywhere in plan.md:** Task 13 is the first task
  whose node function names (`test_search_planner`, `test_file_retriever`, `test_file_classifier`
  — required by plan.md's own file list, e.g. `app/nodes/test_search_planner.py`) collide with
  pytest's default `test_*` discovery convention. Two distinct breakages, both found by actually
  running the suite, not by inspection:
  1. `python -m pytest` run from `backend/worker/` (every "Run:" instruction in the plan does
     this) recursively globs the whole tree by default, so it tried to collect
     `app/nodes/test_search_planner.py` etc. as test *modules* too. Fixed by adding
     `[tool.pytest.ini_options]\ntestpaths = ["tests"]` to `backend/worker/pyproject.toml`
     (no other package in this repo needed this, since none of their node/tool files happen to
     start with `test_`).
  2. Independently, `testpaths` alone didn't fix it: each new test file does
     `from app.nodes.test_search_planner import test_search_planner` — importing the node
     function pulls a `test_`-named callable directly into the test module's own namespace,
     and pytest collects it there too (regardless of `testpaths`), failing at setup because it
     expects a `state` fixture pytest can't resolve. Fixed with the standard pytest idiom
     (`test_search_planner.__test__ = False` etc., right after each import) rather than
     renaming anything plan.md specifies — preserves the plan's literal file/function names
     exactly, adds one non-behavioral line per test file.
  Full worker suite re-run clean after both fixes: 26/26 passing, all three new node files at
  100% coverage.
- `ruff check .` on the three new node files reports the same `I001`/`BLE001` categories already
  established as "leave as-is, verbatim from plan.md" precedent in Tasks 10/11 — no new
  categories introduced.
- **Task 14 (Coverage Analyzer node) ✅.**
  **Real bug found and fixed, confirmed empirically before fixing (per TDD's mandatory
  "verify the failure" step, not just inspection):** plan.md's own Step 3 implementation
  snippet does `state["coverage_matrix"] = [entry.model_dump() for entry in result.root]`,
  but its own Step 1 test snippet mocks `call_llm` to return a **plain `list[CoverageEntry]`**
  (`stub = [CoverageEntry(...)]`), not a `CoverageMatrix` (`RootModel[list[CoverageEntry]]`)
  instance — a plain Python `list` has no `.root` attribute. Implemented the plan's snippet
  first, unmodified, and ran it to confirm: both tests failed with exactly
  `AttributeError: 'list' object has no attribute 'root'`, not the intended assertions.
  Also checked (before deciding on a fix) whether iterating a real `CoverageMatrix` directly
  (`for entry in result`, skipping `.root` instead) would work as an alternative fix — it
  doesn't either: `RootModel` inherits `BaseModel`'s default `__iter__`, which yields a single
  `("root", [...])` field-tuple, not the wrapped list's elements, confirmed with a standalone
  pydantic check against the installed version. So `.root` genuinely is required for the real
  `call_llm` production path (`CoverageMatrix.model_validate(...)`), and the test's plain-list
  mock genuinely can't satisfy it as originally written — both snippets are individually
  reasonable, they just don't agree with each other. **Fix:** `entries = result.root if
  isinstance(result, CoverageMatrix) else result` before the list comprehension — accepts
  either shape, doesn't touch the plan's test, adds one branch. Full worker suite after:
  28/28 passing, `coverage_analyzer.py` at 100%.
- Confirmed the framework-warning text (`"No supported test framework detected; results may be
  incomplete"`) matches design.md §13's Error Handling table verbatim (plan.md's snippet adds
  a trailing period; trivial, not changed).
- **Task 15 (Test Plan Generator, Missing-Test Recommender nodes) ✅**, implemented verbatim
  from plan.md — no `.root`/mock-shape mismatch like Task 14's, since this task's own test
  snippets mock `call_llm` with real `TestPlan(root=[...])`/`MissingTests(root=[...])`
  instances rather than bare lists. Confirmed the 10 `TEST_TYPES` categories match design.md
  §4's Test Plan Generator row verbatim (`permission/role` shortened to `permission`, `API`/`UI`
  lowercased — casing only, not a content change).
  - **Same pytest-collision class of issue as Task 13, caught again by watching the test run
    (not just by inspection):** `test_plan_generator` (the function) collides with pytest's
    `test_*` discovery convention exactly like Task 13's three nodes — fixed the same way
    (`test_plan_generator.__test__ = False`). Additionally, and new this task:
    **`TestCase`/`TestPlan` (the imported Pydantic model classes) collide too** — pytest's
    default `python_classes = Test*` pattern matches their names, producing
    `PytestCollectionWarning: cannot collect test class ... because it has an __init__
    constructor` (a warning, not a hard failure, since pydantic models define `__init__`
    and pytest silently skips classes it can't instantiate that way — tests still passed,
    but output wasn't pristine). Fixed with the same `__test__ = False` idiom applied to
    both classes. `missing_test_recommender.py`'s `MissingTest`/`MissingTests` don't match
    the `Test*` pattern, so no equivalent fix was needed there.
  Full worker suite after: 30/30 passing, no warnings, both new node files at 100% coverage.
- **Task 16 (Quality Validator node) ✅**, implemented verbatim from plan.md — no deviations.
  Pure/synchronous, no LLM or MCP calls, so none of the earlier tasks' `call_llm`/env-var/
  `.root` issues applied. No pytest naming collision either (`quality_validator` doesn't match
  `test_*`, and the test imports no `Test*`-named classes). Full worker suite: 32/32 passing,
  `quality_validator.py` at 100% coverage (and has zero `ruff` findings at all — no imports to
  sort, since it's a self-contained pure function).
- **Task 17 (Report Saver + Cleanup, overall timeout, full graph wiring, worker E2E test) ✅
  — the last Phase 3 task, and by far the one with the most real, empirically-confirmed bugs
  found this phase.** `report_saver.py` implemented verbatim, TDD, 2/2 passing, no issues.
  Everything downstream of it (graph assembly, the runner, and especially the E2E test) needed
  real fixes — every one confirmed by actually running the code, not just by inspection:
  1. **`graph.py`: added a conditional edge after `requirement_retriever`** (plan.md's snippet
     only has a plain edge there) — a direct, necessary consequence of Task 11's own
     plan-directed redesign. The plan's *original* `requirement_retriever` never set
     `status="failed"` (no error handling at all in the stale snippet), so its Task 17 graph
     wiring never needed to check for it. My Task 11 implementation correctly added a
     `status="failed"` path for a failed issue-body fetch (per design.md §5.2 and matching
     `request_validator`'s own pattern) — without this edge, that failure would fall through
     to `requirement_parser` with `state["issue_body"]` unset, raising `KeyError` instead of
     failing cleanly. Not tested by a dedicated unit test (the E2E test's happy path doesn't
     exercise it) — flagged here as a known, reasoned gap rather than over-scoping Task 17
     further.
  2. **Real, confirmed bug: `AgentState` (Task 10) never declared `storage_status`, which
     `report_saver` (Task 17, both from plan.md's own literal snippets) sets.** Discovered by
     noticing the E2E test's `record.storage_status` always came back `None` regardless of
     whether the save actually succeeded. Confirmed the root cause with a minimal, standalone
     LangGraph reproduction: `StateGraph(SomeTypedDict)` silently drops any key a node returns
     that isn't declared in the schema (verified directly — an extra key set by a node vanished
     from `ainvoke`'s result). Fixed by adding `storage_status: str | None` to
     `app/state.py`. Ran a full audit afterward (`state[...] =` writes across every node vs.
     `AgentState`'s declared fields) confirming this was the *only* gap — nothing else is
     silently dropped.
  3. **Real, confirmed bug in the plan's own E2E test snippet: wrong `unittest.mock.patch`
     targets.** The snippet patches `app.llm_client.call_llm` and `app.mcp_clients.
     call_github_tool` directly — but every consuming node does `from app.llm_client import
     call_llm` / `from app.mcp_clients import call_github_tool`, binding its own local
     reference at import time. Patching the origin module's attribute has no effect on
     those already-bound names — confirmed by running the plan's snippet as literally
     written first: real (failing) Anthropic/MCP calls were attempted instead of the stubs.
     This affects **7 node modules** (5 for `call_llm`, 2 for `call_github_tool`), not just
     one — the most severe bug found this phase. Fixed by patching each consuming module's
     own name individually (`app.nodes.requirement_parser.call_llm`,
     `app.nodes.test_search_planner.call_llm`, etc.) — the same pattern already used
     correctly in every one of this phase's own unit tests (audited afterward: grepped every
     `patch(...)` call across `backend/worker/tests/` and confirmed none of Tasks 11–16's own
     tests made this mistake — it was isolated to plan.md's Task 17 E2E snippet).
  4. **Tool-name staleness, as plan.md's own comment already flagged and instructed fixing
     "once Task 11 is built for real":** the E2E stub's `fake_call_github_tool` used
     `get_repository`/`get_issue`/`get_issue_comments` — none of which Task 11's actual
     (redesigned) implementation calls. Corrected to `search_repositories` (returns
     `{"items": [...]}`, not a bare dict) for `request_validator`, and split
     `requirement_retriever`'s mocking in two: `_fetch_issue_body` (direct REST, returns a
     bare string) patched separately from `call_github_tool` with `issue_read`/
     `method="get_comments"` for comments.
  5. **Real, pre-existing risk found and fixed, not in the plan at all: the E2E test's mcp-server
     subprocess is a separate OS process, so moto's `mock_aws()` (which only patches boto3
     within the pytest process) has no effect on it.** `report_saver`'s `save_coverage_report`
     call crosses into that subprocess and makes a genuinely unmocked `boto3` call. Running the
     plan's own `conftest.py` snippet as written (`env={**os.environ, ...}`, inheriting the
     parent environment wholesale) let that subprocess find and use this machine's **real**
     `~/.aws/credentials` — confirmed directly in the first run's log output
     (`Found credentials in shared credentials file: ~/.aws/credentials`). **This means running
     the E2E test as plan.md literally specifies it could make live, unmocked AWS API calls
     against whatever account this machine's ambient credentials grant access to.** Fixed by
     stripping all `AWS_*` vars from the subprocess's inherited environment and forcing moto's
     own documented fake-credential convention (`AWS_ACCESS_KEY_ID=testing`, etc.) instead —
     confirmed the fix works (log now says `Found credentials in environment variables`, not
     the credentials file) and added an explicit `assert record.storage_status == "failed"` to
     the E2E test, proving both that the real (now-guaranteed-to-fail) subprocess save is
     correctly non-fatal *and* that `storage_status` now actually propagates (bug 2 above).
     **This was already live before the fix was applied — the very first test run in this
     session did reach the subprocess with real credentials present.** No confirmation was
     possible (or attempted) that any real AWS resource was actually written to or modified;
     given `report_saver`'s save is the *only* AWS-touching call in that subprocess and it
     targets a table/bucket (`testscope-analyses-test`/`testscope-reports-test`) that likely
     doesn't exist in whatever account those credentials belong to, the most probable outcome
     is an access/not-found error, not a successful write — but this could not be verified
     without inspecting the credentials' actual scope, which was correctly out of reach.
  6. **`conftest.py`'s `time.sleep(1.0)`** (plan.md's own literal Step 7 snippet) reintroduces
     a value Task 8's live verification (`mcp-server/tests/test_mcp_integration.py`) already
     found too short and fixed to `8.0` — applied that already-established fix here too rather
     than risk a flaky subprocess-not-ready failure.
  7. **Test-ordering bug introduced by this session's own new `test_runner.py` (see below):**
     `get_settings()` is `@lru_cache`d process-wide; neither `test_runner.py`'s nor
     `test_runner_e2e.py`'s env-setting fixture called `get_settings.cache_clear()`. Running
     the full suite (not just the new file in isolation) surfaced a real
     `ResourceNotFoundException` — `test_runner.py`'s `DYNAMODB_TABLE="t"` leaked into
     `test_runner_e2e.py`'s later `run_analysis` call. Fixed both fixtures with the same
     `cache_clear()`-before-and-after pattern already established in `test_mcp_clients.py`;
     re-ran the full suite twice afterward to confirm it's not flaky.
  8. **Addition beyond plan.md's literal Test file list:** added `tests/test_runner.py`
     (plan.md only lists `test_report_saver.py`/`test_runner_e2e.py` for this task) — a fast,
     fully-mocked unit test for `run_analysis`'s own exception-handling (a crashed/hung graph
     still marks the analysis failed and still attempts cleanup), since the E2E test only
     exercises the happy path and this is Task 17's *entire reason for existing* (the timeout/
     exception wrapper), left otherwise completely uncovered.
  9. **`health.py`'s `/health/ready` extension has no literal code snippet in plan.md** — only
     a textual instruction ("attempt `JobQueue(...)._client.get_queue_attributes(...)` and
     return 503 on failure, same pattern as Task 19's API readiness check"). Designed it from
     that instruction (`try`/`except` around the SQS call, `HTTPException(503)` on failure).
     Noted in code: the referenced pattern actually lives in **Task 18's** (not Task 19's)
     `backend/api/app/routes/health.py` — a minor plan cross-reference slip, not consequential
     since Task 18's own check (`get_settings()`, no SQS call) isn't directly copyable anyway.
     Not unit-tested: `start_health_server` bundles FastAPI app construction with actually
     starting a uvicorn thread, so testing the route logic in isolation would need refactoring
     beyond what Task 17 asks for — left as an explicit gap, same as `app/llm_client.py`'s.
  10. **Dockerfile (Steps 11–12) implemented verbatim and actually verified**, not just
      written and trusted: ran a real `docker build`, then `docker run` with a Python one-liner
      importing `app.main`/`app.graph`/`app.runner`/`app.health` and calling `build_graph()`
      inside the built image, confirming the full module tree and all 11 graph nodes wire up
      correctly in the actual container (not just in the dev `.venv`). Test image removed
      after verification.
  - `ruff check .` on the new/modified files: same `I001`/`BLE001` categories as established
    precedent, plus a few new-but-still-plan-verbatim findings (`F401` on `graph.py`'s
    intentionally-unused-but-documented `job_intake` import, `S110`/`UP041` in `runner.py`'s
    literal `except Exception: pass` cleanup block) — left as-is, consistent with the same
    "don't diverge from the plan's literal snippets over style-only lint rules" precedent.

**Recommendation: do a Phase 3 health check before merging.** This was the largest and most
integration-heavy task in the phase (it's the first one to actually wire Tasks 10–16 together
and run them end-to-end), and it surfaced real bugs that trace back to two *earlier*,
already-committed tasks (Task 10's `AgentState` schema, Task 11's graph-routing consequence) —
neither caught by those tasks' own unit tests, only by this task's integration-level testing.
That pattern (isolated unit tests all green, but a real gap only visible once things are wired
together) is exactly the kind of thing worth a dedicated look before merging the whole phase,
not necessarily because anything else is currently known to be broken — the state-key audit
above found no other schema gaps, and the patch-location audit found no other tests with the
same mocking mistake — but because Task 17 is the only point in this phase where that class of
bug could even surface, and it's cheap to double-check now versus after merge.

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