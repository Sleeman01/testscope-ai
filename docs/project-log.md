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
(`backend/shared`, Task 9, complete, merged to `main`) → 3 (`backend/worker`, Tasks 10–17,
complete, merged to `main` via PR #12) → 4 (`backend/api`, Tasks 18–22, complete, merged to
`main` via PR #13) → 5 (`frontend`, Tasks 23–26, complete, merged to `main` via PR #14) → 6
(`terraform`, Tasks 27–31, complete, merged to `main` via PR #15) → 7 (`kubernetes`, Tasks 32–35,
complete, merged to `main` via PR #16 code + PR #17 docs) → 8 (`CI/CD`, Tasks 36–38, complete,
merged to `main` via PR #18) → 9 (`observability`, Tasks 39–42, complete, merged to `main` via
PR #19) → 10 (`local full-stack integration`, Task 43) — **Phase 10 ✅ complete, local E2E smoke
test genuinely PASSED end-to-end (`status: completed`, verified by reading real output, not
inferred) — merged to `main` via PR #21.** Task 43 is the first task in the whole project to run every
service via its real Docker entrypoint and make real Claude/GitHub API calls simultaneously —
that exposed five previously-undetected production bugs no earlier phase's mocked-boundary
tests could reach: `backend/worker/Dockerfile`'s `CMD` (broken since Task 17 — `python
app/main.py` vs. `python -m app.main`), three LLM nodes' `RootModel[list[...]]` tool schemas
(invalid Anthropic `input_schema`, since Task 13/16/17), `llm_client.py`'s `max_tokens=4096`
(too small for real structured output, truncating tool calls), `requirement_retriever.py`'s
`issue_read`/`get_comments` shape assumption (wrong since Task 11, silently discarding every
real comment), and `s3_report_key` never persisted to any completed analysis's DynamoDB record
(since Task 17 — `GET .../report` has been unreachable for every real analysis this project has
ever completed). All five fixed and verified; full detail in the Phase 10 entry below. Also
ported the k8s auth-proxy sidecar pattern into `docker-compose.yml` for the GitHub-auth gap, and
replaced the plan's `octocat/Hello-World` smoke-test target with a purpose-built fixture issue
(`Sleeman01/testscope-ai#20`) after confirming empirically that repo can never produce a
`completed` result.
**Post-Phase-10 CI/infra saga (PRs #22–27, undocumented by task number — see the dedicated
entries at the end of the Phase Log below for full detail of each):** GHCR tag-casing and
`packages: write` permission fixes, the `SQS_QUEUE_URL`/`AWS_DEFAULT_REGION` config gap,
self-hosted runner + `production` Environment now genuinely live (real `deploy-prod.yml` runs
against the real cluster), prod `api-hpa` `minReplicas` fix, prod CPU-request reduction for
shared-node capacity, `SQS_QUEUE_URL` durability fix, and a kustomize multi-document patch split
root-caused to a kubectl/kustomize version mismatch between the dev machine and the
control-plane's actual pinned version. Both `dev` and `prod` are now fully live-deployed.
**Branch pattern in use:** `feature/phase-<N>-<short-description>`, one PR per phase (docs-only
housekeeping like this entry uses `docs/<short-description>` instead)
**Current branch:** `docs/task-44-test-plan` (cut fresh from `main` after confirming via
`gh pr list`/`git fetch` that PR #27 had merged — local `main` was 2 commits behind at session
start, fast-forwarded first). Phase 11, Task 44 (`docs/test-plan.md`) pre-work: backfilled this
file's Phase Log with PRs #25–27 (see those entries below), now drafting `docs/test-plan.md`
itself.
**Last merged:** PR #27 (`fix/prod-resources-patch-split`, kustomize patch split for the
kubectl-version mismatch) → `main`, confirmed via `gh pr list`/`git fetch` (PRs #22–26 merged
before it — see the Post-Phase-10 CI/infra saga note above and their individual Phase Log
entries).
**Session-start correction (Phase 9):** local `main` was 4 commits behind `origin/main` (the PR
#18 merge happened upstream but hadn't been fetched locally). Confirmed via `gh pr list` (shown
MERGED) before trusting it, then `git fetch origin` + `git checkout main` +
`git merge --ff-only origin/main` caught it up (`3ded5a7` → `097e720`) before branching Phase 9
off of it — same verify-before-trusting principle as every prior phase's session-start correction,
now the fourth occurrence.
**Session-start correction (Phase 8):** local `main` was 9 commits behind `origin/main` (the PR
#16/#17 merges happened upstream but hadn't been fetched locally). Confirmed via `gh pr list`
(both shown MERGED) before trusting it, then `git fetch origin` + `git checkout main` +
`git pull --ff-only origin main` caught it up (`961a920` → `3ded5a7`) before branching Phase 8 off
of it — same verify-before-trusting principle as every prior phase's session-start correction.
**Session-start correction:** local `main` was behind `origin/main` by 13 commits (the PR #13
merge happened upstream but hadn't been fetched locally). Confirmed via `gh pr list` (PR #13
shown MERGED) before trusting it, then `git fetch origin` + `git checkout main` +
`git pull --ff-only origin main` caught it up (`463479f` → `ffde7be`) before branching Phase 5
off of it. Same verify-before-trusting principle as the Phase 4 note below, now the second
occurrence of this exact pattern — worth treating as a standing habit (always `gh pr list` +
fetch/pull `main` at session start) rather than a one-off.
**Session-start correction (Phase 4, kept for history):** local `main` was 21 commits behind
`origin/main` (the PR #12 merge happened upstream but hadn't been fetched locally) — `git log
main` looked like Phase 3 was still unmerged until `git fetch origin main` + `git pull
--ff-only` caught it up. Confirmed via `gh pr list` (PR #12 shown MERGED) before trusting it.
Flagging per CLAUDE.md's "don't rely solely on the log's claims" rule — this wasn't the log
being wrong, it was the local clone being stale, but the same verify-before-trusting principle
applied.
**frontend test suite (Tasks 23–26 + routing smoke test):** 9/9 passing (`npm test` from
`frontend/`, Vitest, across 6 files) — the pre-existing smoke test, 2 `client.test.ts` cases, 1
`Home.test.tsx` case, 1 `Results.test.tsx` case, 1 `History.test.tsx` case, and 3
`App.test.tsx` cases (real-router routing smoke test, added in place of a full Phase 5 health
check). `npm run build` (`tsc -b && vite build`) is fully green end-to-end; `frontend/Dockerfile`
builds and serves real HTTP traffic (verified via `docker run` + `curl`). Repo-wide regression
check: `backend/worker` 38/38, `backend/shared` 12/12, `backend/api` 16/16, `mcp-server` 17/17 —
all unchanged from Phase 4's baseline.
**mcp-server test suite:** 17/17 passing, 90% coverage (`--cov=. --cov-report=term-missing`
from `mcp-server/`), comfortably above the 80% target.
**backend/shared test suite (Task 9):** 12/12 passing, 100% coverage (`--cov=. --cov-report=term-missing`
from `backend/shared/`). Re-verified after Task 10's `pyproject.toml` fix (see Phase 3 entry
below) — still 12/12, 100%; re-verified again via a fresh uninstall/reinstall from outside
`backend/shared` before starting Task 11 (see Phase 3 entry below).
**backend/worker test suite (Tasks 10–17, Phase 3 complete):** 38/38 passing (stable across
repeated runs), 94% overall coverage (`--cov=. --cov-report=term-missing` from
`backend/worker/`) — every node/client/graph/runner file at 100% except `app/health.py`/
`app/main.py` (still deliberately untested — see Task 17 entry below) and `app/llm_client.py`
(deliberately deferred to a stub-LLM E2E path per Task 12's own plan text, and the E2E test
that exists does exercise it, just not in isolation). `app/runner.py` is 94% (only the
600s-real-timeout branch itself is impractical to unit test; its exception-handling paths —
both the original graph-exception one and the two added by the post-health-check
job_intake/final-upsert fix — all have dedicated fast tests). Confirmed via a full state-key
audit that every key any node writes to `AgentState` is declared in `app/state.py`'s
`TypedDict` (was not true before this task — see below). `backend/worker/Dockerfile` builds
cleanly and its image's module tree/graph wiring were verified by actually running
`docker build` + `docker run ... python -c "import app.main; app.graph.build_graph()..."`
inside the built image, not just trusting the snippet.
**`backend/worker/pyproject.toml` now has `[tool.pytest.ini_options] testpaths = ["tests"]`**
(added in Task 13, see entry below) — anyone adding a new `app/nodes/*.py` file in a future
task should check whether its name collides with pytest's `test_*` discovery glob before
assuming a bare `python -m pytest` run from `backend/worker/` behaves as expected.
**Read before starting Task 18+ (Phase 4, `backend/api`) or Task 22 specifically:**
`docs/2026-07-30-testscope-ai-design.md` §5.2 — the GitHub MCP tool-name assumptions there were
found wrong during Task 8's live verification (see Phase 1 entry below); Task 11 (Phase 3 entry
below) already redesigned `backend/worker`'s `request_validator`/`requirement_retriever` against
the substitute-tool table, so `backend/worker/app/mcp_clients.py`'s `call_github_tool`/
`call_test_mcp_tool` are a settled, correct interface — no further §5.2 rework needed there.
Task 22 (`backend/api/app/mcp_client.py`) is a separate, not-yet-built client and will need the
same substitute-tool-table treatment from scratch — it doesn't inherit Task 11's fix.

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
- Architectural/dependency-version decisions must be surfaced and answered in the chat itself,
  not resolved via a tool-mediated prompt — explicit as of Phase 7 (Tasks 34/35), after a Task 33
  approval happened through a UI tool rather than a plain-text exchange. A report claiming
  something was "approved"/"decided" must be traceable to an actual chat exchange.
- PRs are opened/merged by the user directly on GitHub, not by Claude — explicit as of Phase 7
  (contrast with Phase 6, where Claude ran `gh pr create` without it being flagged as wrong at the
  time; treat "push only, no PR" as the default going forward unless told otherwise).
- `ruff check .` must pass with zero findings and zero blanket category-ignores across all 4
  Python services, going forward — explicit as of Phase 8, after turning it into a real CI gate
  (Task 36) surfaced 10–36 pre-existing findings per service that every earlier phase had
  individually reviewed and left as "verbatim from plan.md, not worth diverging over a style-only
  lint rule." Offered a blanket-ignore-list option matching that precedent; the user chose to fix
  everything instead. Any new lint finding in future phases should be fixed the same way (a real
  code change, e.g. adding the missing `logger.exception(...)` for `BLE001`), not suppressed —
  see the Phase 8 entry below for the specific fixes and reasoning applied to each category.
- CI severity/security gates (Trivy image scans, and by extension similar tooling later) should
  distinguish "no fix exists upstream" from "a fix exists and we haven't taken it" before deciding
  what blocks a build — explicit as of Phase 8, after confirming via `trivy image --format json`'s
  own `Status`/`FixedVersion` fields (not assumed from table output) that base-image CRITICAL
  findings fell into both categories differently. `--ignore-unfixed` is the mechanism for the
  former; a version bump (needing the same approval as any dependency change) is the fix for the
  latter — don't blanket-suppress a whole severity level when some of what it contains is
  genuinely actionable.

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

### Phase 3 — `backend/worker` (LangGraph Agent) — Tasks 10–17 ✅ complete (all 8 tasks)

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

### Phase 3 health check (post-Task 17, pre-merge) — ✅ run, 1 new finding, not yet fixed

- **Full `backend/worker` suite: 36/36 passing across 3 repeated runs (94% coverage, stable,
  no flakiness).** Repo-wide regression check: `backend/shared` 12/12 (100%), `backend/api`
  1/1, `mcp-server` 17/17 (90%) — all unaffected by this branch's changes.
- **Fresh end-to-end re-read of `graph.py`/`runner.py`, with one new finding (see below).**
  Re-confirmed the node-ordering and conditional-edge wiring matches design.md §4 exactly, and
  ran a targeted grep across every node for any *other* place `status="failed"` gets set beyond
  the three already-gated nodes (`request_validator`, `requirement_retriever`,
  `requirement_parser`) — none found, so the conditional-edge fix from Task 17 is complete;
  no other graph-routing gaps exist.
- **Re-audited every node's state read/write against `AgentState`'s declared schema from
  scratch (independent of Task 17's own audit) — clean, no gaps.** Incidentally noted:
  `notes` (`AgentState`/`AnalysisRecord`/the whole request pipeline from the frontend down)
  is plumbed through every layer but never actually read by any Task 10–17 node — checked
  the full plan, not just Phase 3, and no task claims to consume it in a prompt. Not a Phase
  3 defect (nothing crashes or behaves wrong because of it), just an observation for whoever
  builds Phase 5 (frontend) or revisits prompt design later.
- **Re-verified the AWS-credential-isolation fix across 3 repeated E2E runs, not just the
  original one-off confirmation:** every run logged `Found credentials in environment
  variables` (the fake, injected ones), never `Found credentials in shared credentials file`
  (the real ones). Did not additionally re-run the *pre-fix* vulnerable version to double-prove
  the vulnerability would still reproduce without the fix — doing so would mean deliberately
  risking another real, unmocked AWS call for no real additional confidence, given it was
  already directly observed once before the fix existed.
- **`docs/project-log.md` itself was stale in two places, now fixed:** the "Phase:" summary
  line still said "Phase 3 (`backend/worker`, Task 10) complete" (should've said Tasks 10–17),
  and the Phase 3 section header still said "Task 10 ✅ complete, 7 tasks remain (11–17)" —
  both left over from right after Task 10, never updated as Tasks 11–17 landed even though
  each task's own entry below them was added correctly. Also updated the "Read before starting
  Task 12+" note (Task 12 is done now) to correctly point at Task 18+/Task 22 instead, and to
  clarify that Task 22's `backend/api/app/mcp_client.py` is a separate client that does **not**
  inherit Task 11's `backend/worker` fix — it'll need its own pass against design.md §5.2.
- **Finding from the health check — now fixed:** `run_analysis`'s call to `job_intake`
  (before the `try` block) and the final `store.upsert(...)` inside the `finally` block both
  had **no exception handling** — copied verbatim from plan.md's own Task 17 `runner.py`
  snippet. Confirmed empirically (not just by inspection): forced `job_intake` to hit a real
  `ClientError` (bad table) and watched the exception propagate **uncaught** out of
  `run_analysis`. `main.py`'s poll loop has nothing wrapping `asyncio.run(run_analysis(...))`
  either, so this exception would propagate all the way out of `poll_forever()` and crash the
  worker process — not just fail the one job. This directly contradicted design.md §4's own
  stated intent for Job Intake: *"Malformed message → log, ack, skip (no infinite redrive)."*
  SQS's own redrive policy (3 receives → DLQ) bounds the worst case (this isn't an infinite
  crash loop), but it still meant: (a) unnecessary pod restarts for what should be a
  single-job failure, (b) no structured logging of the failure reason beyond the default
  unhandled-exception traceback, and (c) if the crash happened in the *final* upsert rather
  than `job_intake` itself, the `AnalysisRecord` was left permanently stuck at `status=running`
  (already written earlier by `job_intake`) with no terminal state ever recorded — a
  user-facing symptom (an analysis that never finishes) worse than a clean `status=failed`.
  **This was a gap in plan.md's own `runner.py` design, not a deviation introduced by any
  earlier Phase 3 task.**
  - **Fix (TDD):** wrapped `job_intake` in its own `try`/`except`, logging via
    `logger.exception(...)` and returning immediately (no cleanup/final-upsert attempt — there's
    nothing meaningful to finalize since Job Intake never got to record anything) rather than
    letting the exception propagate; wrapped the final `store.upsert(...)` in its own
    `try`/`except` the same way. Introduced `logging` — no prior usage anywhere in this
    codebase (`backend/`, `mcp-server/`) to match, so this is a new but minimal, standard
    convention, not a deviation from an established one. Two new tests written first and
    verified failing against the unfixed code (`test_run_analysis_logs_and_returns_when_job_intake_fails`,
    `test_run_analysis_logs_and_returns_when_final_upsert_fails` — the latter uses a
    call-counting `AnalysisStore.upsert` patch so `job_intake`'s own upsert succeeds
    normally but the *final* one fails, isolating the two code paths), then passing after the
    fix. Re-ran the exact original empirical reproduction (forcing the real `ClientError`)
    from the health check and confirmed it now logs the full traceback and returns normally
    instead of crashing. Full worker suite after: 38/38 passing (stable across 3 repeated
    runs), 94% coverage, `runner.py` at 94% (only the genuine 600s-timeout branch remains
    untested, same as before — unchanged, not a new gap). `ruff` flags nothing new on either
    of the two new `except` blocks — it doesn't treat `except Exception:` followed by
    `logger.exception(...)` as a "blind except" (`BLE001`), unlike the pre-existing
    `except: pass` a few lines away, which is still flagged (unchanged, verbatim from plan.md,
    same "leave as-is" precedent as always).
- **Verdict: Phase 3 is sound and ready to merge.** No regressions anywhere in the repo, all
  prior fixes (schema, mocking, AWS credentials, test ordering) hold up under repeated runs,
  and the one finding from the health check is now fixed and verified both by new unit tests
  and by re-running the original empirical reproduction.

### Phase 4 — `backend/api` (FastAPI) — all 5 tasks (18–22) complete, merged via PR #13

- Branch: `feature/phase-4-backend-api`, cut from `main` after confirming PR #12 (Phase 3)
  merged (see Current State note above re: stale local `main`).
- **Task 18 (API skeleton — app factory, schemas, health endpoints) ✅**, TDD, implemented
  verbatim from plan.md. `backend/api` suite: 3/3 passing (2 new + the Phase 0 smoke test).
  Repo-wide regression check: `backend/worker` 38/38, `backend/shared` 12/12, `mcp-server`
  17/17 — all unaffected.
- **Real, repo-wide environment gotcha found during the mandatory TDD "verify RED" step (Step
  2), not a bug in this task's own code — flagging per CLAUDE.md rather than silently working
  around it:** `backend/api` and `backend/worker` both use a top-level package literally named
  `app` (per plan.md's own file layout for every backend service). Each service's
  `pip install -e` generates its own setuptools editable-install finder
  (`__editable___testscope_<name>_finder.py`), and every one of those finders registers `app`
  in its own `MAPPING` dict. Confirmed by direct inspection of the generated finder files and a
  `sys.meta_path`/`sys.path` dump under pytest: when a submodule (e.g. `app.main`) doesn't yet
  exist in the service actually being tested, that service's own finder correctly returns `None`
  for it — but the *fallback* branch each finder uses for "immediate children of a mapped
  package" ignores the real, already-narrowed `path` argument the import system passes in and
  substitutes its own hardcoded `MAPPING["app"]` value instead. Since finders are checked in
  `sys.meta_path` order (alphabetical by package name at `.pth`-load time — `api`, `mcp`,
  `shared`, `worker`), a missing `app.main` in `backend/api` fell through past `api`'s own
  (correctly-`None`) finder all the way to `worker`'s finder, which *does* have a real
  `app/main.py` — so `from app.main import create_app` in the not-yet-implemented
  `test_health.py` silently imported **`backend/worker`'s** `app/main.py` instead of failing
  with a clean `ModuleNotFoundError`, and then failed several imports deeper on an unrelated
  `ModuleNotFoundError: No module named 'retry'` (a `backend/worker`-only module). Reproduced
  and root-caused with a throwaway debug test (not committed) dumping `sys.meta_path`/`sys.path`
  before concluding this rather than guessing. **Not fixed at the packaging level** — the
  generated finder files are regenerated on every `pip install -e` and aren't meant to be
  hand-edited, and a real fix (e.g. renaming every service's top-level package away from `app`)
  would be an invasive, repo-wide rename touching already-merged Phase 0–3 code, out of scope
  for a single task and not something to do silently. **Practical impact is narrow and
  self-resolving:** it only manifests transiently, during a RED-verification step, for a
  submodule path that (a) doesn't yet exist in the service under test and (b) happens to exist
  at the exact same dotted path in another service (here, `app.main` in both `api` and
  `worker`). The moment the real file is created (Step 3, as normal), `PathFinder` finds it
  directly via the already-narrowed path *before* any editable finder is even consulted, and the
  collision permanently disappears for that path. **Flagging forward for Tasks 19–22 and beyond:**
  if a future RED-verification failure doesn't look like a clean `ModuleNotFoundError` for the
  missing `backend/api` file — e.g. it fails several frames deeper, or the traceback shows
  `../worker/app/...` paths — that's very likely this same collision, not a real regression;
  check the traceback's file paths before assuming the test or feature is broken.
- **Task 19 (`POST /api/analyses`) ✅**, TDD, implemented verbatim from plan.md — no deviations.
  RED-verification confirmed clean this time (`404`/`KeyError`, the route simply not existing
  yet — not the Task 18 app-package collision; checked the traceback shape per that note before
  trusting it, since this was exactly the scenario flagged to watch for).
  - **Checked design.md §5.2's substitute-tool table against this task's plan.md snippet before
    implementing, per the standing Task 8 finding — not applicable here.** Task 19's own code
    (`app/routes/analyses.py`) makes no GitHub/MCP calls at all; it only touches
    `AnalysisStore.upsert`/`JobQueue.send_job` (Task 9, `backend/shared`) and enqueues a job for
    the worker to pick up later. §5.2's stale-tool-name findings only affect Tasks 11/22 (the two
    GitHub MCP client callers) — confirmed by reading Task 19's plan.md text in full rather than
    assuming.
  - **Verified `AnalysisStore.upsert`'s and `JobQueue.send_job`'s real signatures against
    `backend/shared`'s actual implementation before trusting the plan's snippet** (same
    precedent as Task 12's Anthropic-SDK check) — both match exactly
    (`AnalysisStore(table_name=...)`, `.upsert(AnalysisRecord(...))`,
    `JobQueue(queue_url).send_job(analysis_id, repository, issue_number, notes)`), no staleness
    found, implemented as literally written.
  - No credential/secret handling in this task (no MCP/GitHub/Anthropic calls) — nothing to flag
    on that front.
  - `backend/api` suite: 5/5 passing, **100%** coverage (`--cov=. --cov-report=term-missing`) —
    `app/schemas.py` now exercised (was 0% after Task 18, deliberately, since nothing consumed
    those models yet) via `CreateAnalysisRequest`/`CreateAnalysisResponse`. Repo-wide regression
    check: `backend/worker` 38/38 (94%), `backend/shared` 12/12 (100%), `mcp-server` 17/17
    (90%) — all unchanged from Task 18's baseline, unaffected by this branch.
  - `ruff check .` on the two new/modified files: same `I001` import-sort category already
    established as "leave as-is, verbatim from plan.md" precedent, plus one new-but-same-class
    `UP017` (`datetime.UTC` alias) finding — matches the identical `UP017` already left as-is in
    `backend/worker/app/runner.py` (Phase 3), not a new category of issue. Left as-is per that
    precedent.
- **Task 20 (`GET /api/analyses/{id}` and `GET /api/analyses`) ✅**, TDD.
  - **RED-verification note:** `test_get_returns_404_for_unknown_id` passed immediately, before
    any implementation existed — a harmless coincidence (a nonexistent *route* also 404s,
    indistinguishable at that point from a *record* not found), not the Task 18 app-package
    collision (checked: no `ModuleNotFoundError`, no `../worker/app/...` in any traceback this
    task). The other two tests failed cleanly (`404`/`405`, route/method not found) before
    implementation, and the test still exercises the real lookup-miss code path after
    implementation — no action needed, noting only for the next session's awareness.
  - **Real bug found and fixed, deviation from plan.md's literal Step 1 text — flagged, not
    silently applied:** Step 1 says "Reuses the `client` fixture pattern from
    `test_create_analysis.py` — copy the fixture verbatim into this file." Doing exactly that
    and running Step 2 empirically confirmed a real failure beyond the expected one:
    `test_list_returns_recent_analyses` failed with
    `botocore.errorfactory.ResourceNotFoundException: Invalid index: recent-index for table:
    testscope-analyses-test` — `AnalysisStore.list_recent` (Task 9) queries a `recent-index` GSI
    that the copied fixture's `ddb.create_table(...)` call never creates (it only declares the
    base `analysis_id` hash key, no `GlobalSecondaryIndexes` at all). This isn't the Task 18
    collision (no import failure, a genuine AWS/moto error surfaced deep in the FastAPI request
    stack) and isn't fixable in production code — the GSI has to exist on the test table for the
    query to succeed. **Fix:** copied the exact table schema (`AttributeDefinitions` for
    `repository_issue`/`created_at`/`gsi2_pk`, both `repository_issue-index` and `recent-index`
    GSIs) already established and working in `backend/shared/tests/test_dynamodb.py`'s own
    `store` fixture, rather than inventing a new schema — same index names/key schemas, proven
    correct there. Verified this was necessary (not a workaround) by confirming
    `query_by_repo_issue` also depends on `repository_issue-index`, which the plan's literal
    fixture likewise never created. No credential/secret handling and no architectural decision
    involved — purely a test-fixture completeness gap in the plan's own literal instruction.
  - **Addition beyond plan.md's literal 3-test file list, same precedent as Tasks 11/13/17's
    proactive coverage-gap closures — flagged, not silent:** the plan's own 3 tests never
    exercise `list_analyses`'s `repository`+`issue_number` filter branch (lines calling
    `_store().query_by_repo_issue(...)`), even though it's part of Task 20's own declared
    interface (`GET /api/analyses?repository=&issue_number=...`). Left uncovered, `analyses.py`
    sat at 95% (2 lines missed). Added
    `test_list_filters_by_repository_and_issue_number` (not in the plan's Test file list) to
    close it — required the GSI fix above to even run, since `query_by_repo_issue` hits
    `repository_issue-index` the same way `list_recent` hits `recent-index`.
  - `backend/api` suite: 9/9 passing, **100%** coverage (`--cov=. --cov-report=term-missing`,
    up from Task 19's 5/5). Repo-wide regression check: `backend/worker` 38/38 (94%),
    `backend/shared` 12/12 (100%), `mcp-server` 17/17 (90%) — all unchanged.
  - `ruff check .`: same `I001`/`UP017` categories as Task 19, plus one new `I001` finding at
    `app/routes/analyses.py:29` — a direct, expected consequence of Step 3's own literal "append
    below `create_analysis`" instruction placing a second import block mid-file rather than
    merging it into the top-of-file imports. Same "leave as-is, verbatim from plan.md" precedent,
    no new category.
- **Task 21 (`GET /api/analyses/{id}/report`) ✅**, TDD, implemented verbatim from plan.md — no
  deviations in the implementation itself.
  - **No GitHub/MCP calls in this task either** (confirmed by reading the full task text before
    starting, same check as Tasks 19–20) — only `AnalysisStore.get` and `ReportStore.read_json`/
    `.presigned_url`. Verified both `ReportStore` methods' real signatures in `backend/shared/s3.py`
    against the plan's snippet before trusting it — exact match, no staleness.
  - **DynamoDB fixture checked against Task 20's GSI finding before assuming plan.md's literal
    copy-paste instruction was complete — this time it genuinely was, confirmed empirically, not
    assumed.** Step 1 says to copy the fixture verbatim from `test_create_analysis.py` (the
    *original*, GSI-less table schema — not `test_get_and_list_analyses.py`'s fixed one) plus add
    an S3 bucket. Checked first whether this task's own two tests call anything requiring a GSI:
    they only exercise `AnalysisStore.get` (`get_item`), `AnalysisStore.upsert` (`put_item`, via
    the `POST` helper), and a raw `ddb.update_item` — none of which touch `repository_issue-index`
    or `recent-index`. Implemented the literal instruction as-is and ran Step 2: RED failed clean
    (`404`, route not found, both tests) — no `ResourceNotFoundException` this time, confirming
    the GSI-less fixture is genuinely sufficient here, not another instance of Task 20's gap.
  - RED-verification traceback shape checked against the Task 18 note both times (Step 2 and
    while diagnosing) — plain `404`s, no `ModuleNotFoundError`, no `../worker/app/...` — not the
    app-package collision.
  - No credential/secret handling and no architectural decisions in this task.
  - **Addition beyond plan.md's literal 2-test file list, same precedent as Tasks 11/13/17/20:**
    the plan's own two tests never exercise `get_report`'s "analysis doesn't exist" branch, even
    though Task 21's own **Interfaces** line explicitly declares it ("404 if the analysis itself
    doesn't exist") — left `analyses.py` at 98% (1 line missed). Added
    `test_returns_404_for_unknown_id` to close it.
  - `backend/api` suite: 12/12 passing, **100%** coverage (up from Task 20's 9/9). Repo-wide
    regression check: `backend/worker` 38/38 (94%), `backend/shared` 12/12 (100%), `mcp-server`
    17/17 (90%) — all unchanged.
  - `ruff check .`: same `I001`/`UP017` categories as Tasks 19–20, plus one new `I001` at
    `app/routes/analyses.py:51` — same mid-file "append" import pattern as Task 20's finding, not
    a new category.
- **Task 22 (`POST /api/analyses/{id}/github-issue`) ✅ — the last Phase 4 task, and by far the
  one with the most real findings, some fixed, one left open and unresolved.**
  - **Tool-name staleness, plan-directed (not silent) — same class as Task 11's:** plan.md's own
    Task 22 text explicitly flags its literal `"create_issue"` snippet as STALE ("Task 8
    confirmed it doesn't exist; `issue_write(method='create')` is the substitute") and instructs
    implementing the correction, not the literal code. Implemented `call_github_tool("issue_write",
    method="create", owner=owner, repo=repo, ...)` accordingly. Cross-checked against
    design.md §5.2's substitute-tool table directly (not just the plan's inline comment) before
    trusting it — table entry matches exactly.
  - **`structured_content` fix applied, same established precedent as Task 11's
    `mcp_clients.py`:** `backend/api/app/mcp_client.py` parses `content[0].text` as JSON instead
    of relying on `result.structured_content` (which design.md §5.2 documents as `None` for this
    server's dict-returning tools) — matches `backend/worker/app/mcp_clients.py`'s
    already-established, working fix exactly.
  - **Real verification performed, not assumed, for the plan's explicitly-flagged "unconfirmed"
    response shape:** design.md §5.2 says `issue_write(method="create")`'s success response
    shape — specifically whether it returns `html_url` — was never confirmed during Task 8
    (avoided creating a real GitHub issue, same no-side-effects policy applied again here).
    Verified without any live API call or credential: extracted the actual installed
    `ghcr.io/github/github-mcp-server:latest` binary (`docker cp` from a stopped container, no
    network calls) and grepped its embedded UI bundle for the `issue_write` tool's own
    first-party React widget (`appName: "github-mcp-server-issue-write"`) — found
    `let s=e.html_url||e.url||e.URL||"#"` as the primary link the widget renders after a
    successful create/update, i.e. GitHub's own UI code confirms the response includes
    `html_url`. This satisfies plan.md's explicit instruction ("must be verified for real (or
    against the installed image's docs) before Task 22 ships, don't assume") via the "installed
    image's docs" path, with zero side effects and no token needed. Implemented
    `result["html_url"]` as the plan's snippet already assumed — no code change needed here,
    just verification that it's safe to trust.
  - **Significant finding, NOT resolved — flagged for the user's decision, not silently
    applied either way:** live-tested the real `github-mcp-server` container's HTTP mode
    directly (`curl`-equivalent POST to `/mcp` with no `Authorization` header) and got a clean
    `401 Unauthorized`, confirming design.md §5.2's own documented finding that HTTP mode
    requires a per-request `Authorization: Bearer <token>` header (the `GITHUB_PERSONAL_ACCESS_TOKEN`
    env var alone doesn't authenticate requests). **This is in direct, unresolved tension with
    design.md §9's own explicit secrets boundary: "GitHub token mounted only in
    `mcp-github`/`mcp-test-analysis`... Neither reaches `api` or `frontend`."** `backend/api`
    cannot both (a) never hold the GitHub token and (b) send a per-request Bearer token that
    only it could supply. Also discovered, while investigating this, that **`backend/worker`'s
    already-merged `call_github_tool`/`_call_once` (Task 11, Phase 3) has the exact same gap** —
    it never sends an Authorization header either (confirmed by reading
    `backend/worker/app/mcp_clients.py` in full — no `Authorization`/`Bearer` anywhere in that
    file; only `requirement_retriever.py`'s *separate* direct-REST body-fetch call sends one).
    Neither worker's `request_validator`'s `search_repositories` call nor
    `requirement_retriever`'s `issue_read`/`get_comments` call would authenticate successfully
    against the real server as currently written — this was never caught before because every
    existing test (worker's and this session's new `backend/api` ones) mocks the MCP transport
    boundary (`streamable_http_client`/`ClientSession`), so a missing auth header never surfaces
    as a test failure, only against a real server. **Implemented Task 22's `mcp_client.py`
    without an Authorization header, matching both plan.md's own literal snippet and the stated
    "Neither reaches api" secrets boundary** — this is the more conservative choice (doesn't
    introduce new credential handling into `api` unilaterally) but means
    `POST /api/analyses/{id}/github-issue` will currently 401 against the real `mcp-github`
    server as deployed, same as worker's two MCP-routed GitHub calls would. Resolving this for
    real needs an infrastructure-level decision (e.g. a sidecar/gateway that injects the bearer
    token in front of `mcp-github`, keeping the raw token out of `api`'s/`worker`'s own process;
    or revisiting the "Neither reaches api" boundary) — likely a Phase 6 (Terraform)/Phase 7
    (k8s) concern, not a single backend task's code change. **Not fixed in this branch; explicitly
    flagged here and in Current State above for a deliberate decision, not silently worked
    around either by adding the header (violates the stated boundary) or ignoring the finding.**
  - **Real bug found and fixed, confirmed empirically via an actual `docker build` + module
    import check (same verification discipline as Task 17's Dockerfile check) — not just
    written and trusted:** `backend/api/pyproject.toml` never listed the `mcp` SDK as a
    dependency (no earlier Phase 4 task needed it; Task 22's `mcp_client.py` is the first). It
    worked in this session's own `.venv` only because `mcp` was already present there
    transitively (pulled in by the already-installed `testscope-worker`/`testscope-mcp`
    packages) — masking the gap completely in local dev. Building the real Docker image and
    running `python -c "import app.main; import app.mcp_client; ..."` inside it (a clean,
    isolated environment with only `backend/api`'s own declared dependencies) reproduced a
    genuine `ModuleNotFoundError: No module named 'mcp'`. **Fixed:** added `"mcp>=2.0,<3.0"` to
    `backend/api/pyproject.toml`'s dependencies — deliberately matching `mcp-server/pyproject.toml`'s
    already-corrected pin, **not** `backend/worker/pyproject.toml`'s `"mcp>=1.1"`, since
    design.md's own SDK version note explicitly documents that unpinned-major-version pin as the
    root cause of Task 8's breaking-change surprise (`mcp` 1.x → 2.0 changed `FastMCP`,
    `streamablehttp_client`'s tuple arity, `Tool.inputSchema`, and more) — reusing the
    already-corrected, narrower pin rather than repeating a known mistake. Re-ran `docker build`
    + the import check after the fix: clean pass, no errors. Re-ran the full local test suite
    afterward too (16/16, 100%) to confirm the dependency addition didn't disturb anything.
  - **No GSI needed for this task's fixture, confirmed by checking what the task's own DB calls
    require before assuming either Task 20's or Task 21's schema style applied** (per the user's
    explicit ask) — same as Task 21: only `AnalysisStore.get`/`.upsert` (via the `POST` helper)
    and a raw `ddb.update_item`, no `list_recent`/`query_by_repo_issue`. Used the plain,
    GSI-less schema; RED failed clean (`404`/`AttributeError`, both expected-reason failures)
    confirming this was correct, not another instance of Task 20's gap.
  - **RED-verification traceback shape checked against the Task 18 collision note at every
    step** — plain `404`s and one `AttributeError` (attribute not yet defined, since
    `mcp_client.py` didn't exist yet when the test's `patch(...)` call ran) — no
    `ModuleNotFoundError`, no `../worker/app/...`, not the collision.
  - **Credential/secret handling — flagged explicitly, not silently applied:** this is the
    first task in `backend/api`'s history to touch GitHub-related code at all. As implemented,
    `backend/api` still holds **zero** credentials (no `GITHUB_TOKEN`, no change to `Settings`)
    — consistent with design.md §9's stated boundary. The credential-handling question that
    *is* open is the unresolved auth-header gap above, not anything actually added to `api` in
    this branch.
  - **Addition beyond plan.md's literal 2-test file list, same precedent as Tasks
    11/13/17/20/21:** added `test_returns_404_for_unknown_id` to `test_create_github_issue.py`
    (the plan's own 2 tests never exercise the "analysis doesn't exist" branch) and a new
    `tests/test_mcp_client.py` with one transport-boundary test
    (`test_call_github_tool_parses_json_text_payload_over_the_real_mcp_transport`, mirroring
    worker's own `test_call_once_parses_json_text_payload_over_the_real_mcp_transport` from
    Task 11) — the plan's own Step 5 bar ("≥80% coverage on `app/`") was already met at 95%
    without either addition, but `mcp_client.py`'s real transport/parsing logic was at 0% direct
    coverage (every route test mocks it at the boundary), the same class of gap this session has
    consistently closed rather than leaving on the table.
  - `backend/api` suite: 16/16 passing, **100%** coverage on `app/` (plan's own bar was ≥80%).
    Repo-wide regression check: `backend/worker` 38/38 (94%), `backend/shared` 12/12 (100%),
    `mcp-server` 17/17 (90%) — all unchanged.
  - `ruff check .`: same `I001`/`UP017` categories as Tasks 19–21, plus one new category —
    `SIM117` (nested `with` statements) in `app/mcp_client.py:7` — confirmed this is **not** a
    new class of finding by checking `backend/worker/app/mcp_clients.py`, which has the
    identical nested-`with` transport pattern and the identical, already-unaddressed `SIM117`
    finding there too. Left as-is, same precedent.
  - `backend/api/Dockerfile` added (Step 7/8), verified for real: `docker build` succeeded, and
    `docker run ... python -c "import app.main; import app.mcp_client; import
    app.routes.analyses; import app.routes.health"` succeeded inside the built image after the
    `mcp` dependency fix above — full module tree wires up correctly in the actual container,
    not just the dev `.venv`. Verification image removed after confirming.

**Recommendation: a Phase 4 health check is warranted before merging, same as Phase 3's.**
Reasoning: (1) there is a real, **unresolved** architectural/credential gap (GitHub token
custody vs. required per-request Bearer auth) that means the final task's entire feature
(`POST /api/analyses/{id}/github-issue`) will not work against the real `mcp-github` server as
currently deployed — this needs a deliberate decision recorded, not to be merged over silently.
(2) Every Phase 4 task's tests use their own separate `client` fixture with independently
provisioned (and, per Task 20's finding, sometimes incomplete) AWS resources — nothing in this
phase exercises the full request lifecycle (create → get → list → report → github-issue) in one
continuous flow against a single, fully-provisioned table, the way Phase 3's Task 17 E2E test
did for the worker. (3) This session already found and fixed three real, empirically-confirmed
gaps that inspection alone would have missed (Task 20's missing GSIs, Task 22's missing `mcp`
dependency, Task 22's stale tool name) purely by *actually running things* rather than trusting
snippets — suggesting a dedicated, fresh-eyes pass (matching Phase 3's health-check format) is
cheap insurance before merging a 5-task, first-ever-build-of-this-service phase, consistent with
the same reasoning Phase 3's own health-check recommendation gave.

### Phase 4 health check (post-Task 22, pre-merge) — ✅ run, no new blocking findings

- **Full `backend/api` suite: 16/16 passing across 3 repeated runs (100% coverage on `app/`,
  stable, no flakiness).** Repo-wide regression check, also run 3x each: `backend/worker` 38/38
  (94%), `backend/shared` 12/12 (100%), `mcp-server` 17/17 (90%) — all stable, all unaffected by
  this branch.
- **State-of-branch audit, fresh grep/read pass (independent of each task's own inline
  claims) — clean, no gaps found:**
  - All 5 tasks' files present and accounted for (`schemas.py`, `main.py`, `routes/health.py`,
    `routes/analyses.py`, `mcp_client.py`, `Dockerfile`, plus 6 test files) — confirmed via a
    fresh `find` and a `git diff --stat main...feature/phase-4-backend-api` (14 files changed,
    exactly Phase 4's scope, nothing stray).
  - Zero `TODO`/`FIXME`/`XXX`/`HACK` markers anywhere in `backend/api`.
  - Zero stale `create_issue` references anywhere (the corrected `issue_write` name is used
    consistently in both the implementation and its test).
  - `structured_content`/`structuredContent` appears exactly once, in a comment explaining why
    it's *not* used — no leftover reliance on it anywhere in actual code.
  - `mcp>=2.0,<3.0` present in `backend/api/pyproject.toml`, matching `mcp-server`'s
    already-corrected pin (not `worker`'s stale `mcp>=1.1`).
  - GSI usage in test fixtures is consistent with each task's own DB calls: only
    `test_get_and_list_analyses.py` (the only file whose tests call `list_recent`/
    `query_by_repo_issue`) has `GlobalSecondaryIndexes` in its table setup; the other four
    fixtures correctly use the plain schema.
  - Working tree clean; only this doc's own health-check edit is uncommitted at write time.
  - **Runtime route-table check, not just file inspection:** built a live `TestClient`, hit
    `/openapi.json`, and confirmed all 6 real endpoints from Tasks 18–22 are registered exactly
    once each with the correct methods (`POST/GET /api/analyses`, `GET /api/analyses/{id}`,
    `GET /api/analyses/{id}/report`, `POST /api/analyses/{id}/github-issue`, `GET /health/live`,
    `GET /health/ready`) — the whole module tree wires together correctly at runtime, not just
    on paper.
- **The GitHub-auth architectural gap is now recorded in two places, not just buried in one
  task's narrative:** the detailed reasoning stays in the Task 22 entry above, and a concise,
  explicit, forward-looking entry was added to **"Open Questions / Things to Revisit"** below
  (the doc's own dedicated section for exactly this kind of standing follow-up) — clearly
  labeled **"KNOWN FOLLOW-UP TASK, not yet scheduled to a phase"**, stating plainly that
  `POST /api/analyses/{id}/github-issue` is not functional against the real `mcp-github` server
  pending an infra-layer fix (most likely a token-injecting sidecar/gateway in front of
  `mcp-github`, keeping both `api` and `worker` token-free), that the same gap independently
  affects two of `backend/worker`'s already-merged GitHub calls (Task 11), and that this belongs
  to Phase 6/7, not a single backend task. Not silently implicit.
- **Secrets check: clean.** Grepped `backend/api` for token-like patterns
  (`ghp_`/`github_pat_`/`AWS_SECRET`/inline `api_key=`/`token=` literals) — none found. No
  `.env`/`.env*` files anywhere in the repo. No `GITHUB_TOKEN` reference anywhere in
  `backend/api` (correct — it's never supposed to hold one). Scanned this branch's full
  `git log -p` diff against `main` for secret-shaped strings (`ghp_`, `github_pat_`, a raw
  `Bearer <20+ char token>`, AWS access-key patterns) — none found. **This session never
  actually used a real GitHub token at any point** — the 401 check that surfaced the auth-header
  finding was a deliberately *unauthenticated* request against the live `github-mcp-server`
  container, proving the requirement without ever touching a real credential (unlike Task 8's
  disposable-PAT verification, no token was needed here at all). Two harmless, non-secret debug
  artifacts from earlier in this session were found and removed as routine hygiene: a
  `/tmp/debug_test.py` `sys.meta_path` dump (Task 18's collision investigation) and a stale
  `.pyc` for a since-deleted debug test file — neither contained anything sensitive. No leftover
  Docker containers, images, or extracted binaries from any of this session's live-server
  verification work.
- **"Run it for real" checks, deliberately going beyond the task-level test suites — this is
  where Task 20's GSI gap and Task 22's missing dependency were actually caught, so the same
  discipline was repeated here rather than trusting the suites alone:**
  1. **Docker build + live HTTP requests against the running container** (not just a module
     import check like Task 17's/Task 22's own verification): built the image, ran it with
     `docker run -p ...`, and hit real endpoints with `curl` — `/health/live` and `/health/ready`
     both `200`, `/openapi.json` lists all 6 routes correctly, `POST /api/analyses` with a bad
     payload correctly returns FastAPI's standard `422` (not a crash), and
     `GET /api/analyses/does-not-exist` correctly reaches real `app/routes/analyses.py` code
     (confirmed via the traceback) before failing on `botocore.exceptions.NoCredentialsError` /
     `NoRegionError` — expected and correct, since this bare smoke-test container has no AWS
     region/credentials configured at all (real deployment gets both from the EC2 instance
     profile per design.md §9). The traceback's only application-code frame is the `_store().get()`
     call site itself; everything past that is stock `botocore` — confirms no hidden defect in
     `backend/api`'s own code, just the absence of AWS config in an intentionally bare container.
  2. **Fresh, fully isolated venv — not the shared dev `.venv`** — containing *only*
     `backend/shared` and `backend/api`'s own declared dependencies (no `testscope-worker`/
     `testscope-mcp` installed at all, so nothing could transitively mask a missing dependency
     the way the `mcp` gap was hidden before): `pip install -e backend/shared && pip install -e
     "backend/api[dev]"` into a brand-new venv, then `import app.main; import app.mcp_client; ...`
     — clean. Ran the full suite in that same isolated venv: 16/16 passing, 100% coverage — full
     confirmation `pyproject.toml`'s dependency list is now genuinely complete and self-sufficient,
     not just "complete enough to pass in an environment with other packages' transitive installs
     still present."
  3. **Directly verified, not just reasoned about, a behavior this session had only inferred
     from pydantic's documented default:** `_to_status_response`'s reliance on pydantic v2's
     default `extra="ignore"` behavior to safely drop `AnalysisRecord`'s `s3_report_key`/
     `tool_call_trace`/`user_feedback` fields (none of which `AnalysisStatusResponse` declares)
     had never actually been exercised by any test against a record with `s3_report_key` set —
     Tasks 21/22's tests that populate it call `/report`/`/github-issue`, not
     `GET /api/analyses/{id}`. Constructed a record with all three extra fields populated and
     called `_to_status_response` directly: clean conversion, no error, extra fields dropped as
     expected. Closes a previously-assumed-but-unverified corner.
  - **No new latent gaps found** beyond the already-documented, already-flagged GitHub-auth
    architectural question — every other check (build, live HTTP, isolated-venv import/test run,
    the pydantic corner case) came back clean.
- **Verdict: Phase 4 is sound and safe to merge from a code-correctness standpoint.** All tests
  pass, stably, across repeated runs and in a fully isolated environment; the branch's file state
  is consistent with no stray or stale artifacts; secrets handling is clean; and the Dockerfile
  builds and serves real traffic correctly. **The one open item — GitHub MCP authentication —
  is a known, clearly-documented, deliberately-unresolved architectural gap, not a code defect
  in this branch, and not something any amount of further `backend/api` code changes could fix
  alone** (it needs an infra-layer decision spanning `api`, `worker`, and the `mcp-github`
  deployment itself). Recommend merging Phase 4 as-is and tracking the GitHub-auth fix as its
  own explicitly-scheduled follow-up (flagged in "Open Questions" below) rather than blocking
  this merge on an infrastructure phase that hasn't started yet.

### Phase 5 — `frontend` (React) — Tasks 23–26 ✅ complete (all 4 tasks)

- Branch: `feature/phase-5-frontend`, cut from `main` after confirming PR #13 (Phase 4) merged
  (see Current State note above re: stale local `main`, second occurrence of the same pattern
  as Phase 4's own session-start correction).
- **Checked project-log for standing findings before starting, per the user's explicit ask —
  none apply to Task 23:** the app-package-name import collision (Task 18) is Python-packaging-
  specific (`app` as a top-level module name across `backend/*` services); `frontend/` has no
  Python package and isn't affected. The DynamoDB GSI-vs-plain-fixture distinction (Tasks 20/21)
  is backend-only; Task 23 makes no DynamoDB calls at all (it's a pure API-client/routing
  skeleton, backed by `vi.stubGlobal("fetch", ...)` mocks, not a real backend). The GitHub-auth
  infra gap (Task 22, still an open follow-up) doesn't apply yet either — `createGithubIssue` in
  `client.ts` is a thin fetch wrapper with no MCP/GitHub call of its own; the gap only matters
  once a page actually invokes it against a real deployment (Task 25 or later), not at the
  client-wrapper level Task 23 builds.
- **Task 23 (Frontend skeleton — API client, routing, Vitest config) ✅.** TDD: wrote
  `client.test.ts` first, verified RED (`Failed to resolve import "./client"` — Vite's actual
  wording for the plan's expected "Cannot find module", same underlying cause, not a concern).
  - **Real, empirically-confirmed bug in the plan's own literal `client.ts`/`client.test.ts`
    snippets, found via the mandatory RED→implement→verify-GREEN step, not by inspection:**
    implementing `request<T>(path: string, options?: RequestInit)` exactly as written and running
    the `getAnalysis` test (which calls `request` with no `options` arg) failed —
    `expect(fetch).toHaveBeenCalledWith("/api/analyses/a1", expect.anything())` doesn't match,
    because `fetch(`${BASE_URL}${path}`, options)` with `options` left `undefined` still passes an
    explicit second argument (`arguments.length === 2`), and Vitest/Jest's `expect.anything()`
    explicitly excludes `undefined` (confirmed directly: a throwaway debug test logged the actual
    captured call args as `["/api/analyses/a1", undefined]`, length 2 — removed after confirming).
    **Fix:** changed the parameter to `options: RequestInit = {}` (default instead of optional) —
    one-line change, doesn't touch either test file, `createAnalysis`'s test (which does pass
    explicit options) is unaffected. Full frontend suite after: 3/3 passing (1 pre-existing smoke
    test + 2 new).
  - **Two more real gaps found via `npm run build` (`tsc -b && vite build`) — not part of Task
    23's own literal verification step (`npm test -- client.test.ts`), but checked anyway per this
    project's established "run it for real, don't just trust the snippet" discipline:**
    1. `import.meta.env.VITE_API_BASE_URL` (`client.ts`, straight from the plan's own snippet)
       doesn't type-check — `tsconfig.json`'s `types` array never included `vite/client`. Fixed
       directly (config-only change, `vite/client`'s types ship inside the already-installed
       `vite` devDependency — not a new dependency, so no approval needed). Confirmed the fix by
       re-running `tsc -b`: the `ImportMeta`/`env` error is gone.
    2. **Not fixed, flagged instead:** every `.tsx` file fails to type-check
       (`TS7016: Could not find a declaration file for module 'react'`, etc.) —
       `frontend/package.json` has never had `@types/react`/`@types/react-dom` in
       `devDependencies`, since Task 23 is the first task to write real JSX (Phase 0's Task 1 smoke
       test was plain `.ts`, no JSX). This is a genuine new-dependency addition, not a config fix,
       so per CLAUDE.md's dependency-approval rule it's left unresolved here rather than
       `npm install`ed unilaterally. **Does not block Task 23 itself** — `npm test` (Vitest, via
       esbuild) doesn't need type declarations to run and passes cleanly; it only blocks
       `npm run build`'s `tsc -b` step, which nothing in Task 23's plan text requires. Will need a
       decision before Task 36 (CI pipeline, if it type-checks the frontend) or before relying on
       `npm run build` for anything real.
  - Housekeeping: removed `frontend/tsconfig.tsbuildinfo`, a `tsc -b` build-cache artifact
    generated by this session's own verification `npm run build` run (not part of the plan's file
    list) — added `frontend/*.tsbuildinfo` to `.gitignore` so it doesn't reappear as an untracked
    file for the next session.
  - `frontend` suite: 3/3 passing. Repo-wide regression check (Python suites, unaffected by a
    frontend-only branch — checked anyway, same discipline as every prior phase):
    `backend/worker` 38/38, `backend/shared` 12/12, `backend/api` 16/16, `mcp-server` 17/17 — all
    unchanged from Phase 4's baseline.
  - No credential/secret handling in this task — `createGithubIssue`/`getReport` are thin fetch
    wrappers with no token of their own; `git diff` scanned clean for secret-shaped strings.
- **`@types/react`/`@types/react-dom` added, user-approved.** Read the installed React version
  from `frontend/package.json` and cross-checked against `node_modules/react/package.json` before
  installing, per the user's explicit ask (both agreed: `18.3.1`) — installed
  `@types/react@^18`/`@types/react-dom@^18` (resolved to `18.3.31`/`18.3.7`) as `devDependencies`
  only. `package-lock.json` diff is additive-only (37 insertions, 0 deletions) — no other
  package's version changed. `npm audit`: 8 pre-existing findings (5 moderate, 2 high, 1
  critical), all traced individually via `npm audit --json` and `npm ls` — none attributable to
  the two new packages (their only deps are `@types/prop-types`/`csstype`, neither flagged).
  `nanoid` is new to the *audit list* since Task 23 but not new to the *tree*: confirmed via
  `git show HEAD:frontend/package-lock.json` that it was already present (`3.3.16`, transitive via
  `vite`→`postcss`) before this install — not introduced by it. Full breakdown: `esbuild`/`vite`/
  `vitest`/`vite-node`/`@vitest/mocker` chain (moderate/high/critical, dev-only) and
  `react-router`/`react-router-dom` (moderate) are the same categories Phase 0 already accepted as
  v1 limitations (`nanoid` wasn't itemized in Phase 0's own prose but is part of the same
  pre-existing `vite` dev-dependency chain) — no new category introduced, `npm audit fix` not run.
  - **Confirmed genuinely resolving, not silently ignored, per the user's explicit ask:**
    `tsc -b --explainFiles` shows `vite/client` as an explicit type-library entry point
    (`Entry point of type library 'vite/client' ... node_modules/vite/client.d.ts`), and a
    throwaway probe file (`const x: string = import.meta.env.VITE_API_BASE_URL`) compiled with
    zero errors — removed after confirming.
  - **`npm run build`'s `tsc -b` step now passes cleanly — no new type errors in Task 23's code**
    (the `@types/react`/`@types/react-dom` install alone fixed every `TS7016`/`TS7026` finding from
    before). `vite build` itself still fails, but on a **separate, real, pre-existing plan gap
    unrelated to this install — flagged, not fixed:** grepped the entire plan document for
    `index.html` and found none — no task anywhere creates `frontend/index.html`, which Vite
    requires as its default build entry point (and dev-server entry). This was invisible until now
    because every prior `npm run build` attempt failed earlier, at the `tsc` step, before ever
    reaching `vite build`. Not part of Task 23's or Task 24's own file list, so not added here;
    needs a decision (add a minimal `index.html` now as a small out-of-band fix, or leave it
    flagged until a task that references frontend serving — Task 34's nginx-ingress or Task 43's
    local full-stack E2E smoke test — forces the issue).
- **Task 24 (Home page — repo/issue form) ✅**, implemented verbatim from plan.md — no deviations,
  no plan bugs found this time (unlike Task 23's `options?: RequestInit`/`expect.anything()`
  mismatch, the third plan-snippet bug found this project — see Task 23 above, Task 14, and Task
  20 for the first two classes). RED-verification failed clean (`Unable to find a label with the
  text of: /repository/i` — stub `Home` has no form elements, exactly as the plan predicted).
  Two harmless `React Router Future Flag Warning` messages on stderr (v7-migration warnings,
  informational only, not failures) — noted, not treated as a finding.
  - `frontend` suite: 4/4 passing (up from Task 23's 3/3). `tsc -b` still passes cleanly (no new
    type errors from `Home.tsx`/`Home.test.tsx`); `vite build` still blocked by the same
    pre-existing `index.html` gap noted above, unrelated to this task. Repo-wide regression check:
    `backend/worker` 38/38, `backend/shared` 12/12, `backend/api` 16/16, `mcp-server` 17/17 — all
    unchanged.
  - No credential/secret handling, no new dependencies.
- **RESOLVED, decision made by the user: `frontend/index.html` added now, out-of-band, same class
  of fix as the Task 10/20/22 precedents.** Before creating it, verified (per the user's explicit
  ask) rather than assumed:
  1. Grepped the *entire* plan for `index.html` — appears exactly once, in Task 34's
     `frontend/nginx.conf` (`try_files $uri /index.html`), which **serves** the file, not creates
     it. Confirmed directly that neither Task 34 nor Task 43 (nor any other task) ever creates
     `frontend/index.html`.
  2. Confirmed the real entry module path and mount target from the actual repo content, not
     assumed: `frontend/src/main.tsx` (the only `main.ts*`/`index.ts*` candidate in `src/`) calls
     `document.getElementById("root")`.
  3. Created a minimal `frontend/index.html`: doctype, `charset`/`viewport` meta, a plain title,
     `<div id="root">`, and `<script type="module" src="/src/main.tsx">` — nothing beyond that, no
     scope creep.
  4. Verified it actually unblocks both: `npm run build` now produces a real `dist/index.html` +
     bundled JS (previously failed at `Could not resolve entry module "index.html"`); `npm run dev`
     booted, served `HTTP 200` at `localhost:5173`, and was stopped cleanly afterward.
- **Task 25 (Results page — polling, coverage matrix, actions) ✅**, implemented verbatim from
  plan.md's `Results.tsx` snippet — no deviations there.
  - **Real, empirically-confirmed plan bug found via the mandatory RED-verification step (the
    fourth plan-snippet bug found this project — see Task 23's `options?`/`expect.anything()`
    mismatch above, and Tasks 14/20 in Phase 3/4 for the first two):**
    `@testing-library/jest-dom` has been a `devDependency` since Task 1 (and its type declarations
    are in `tsconfig.json`'s `types` array), but **no task, anywhere, ever actually wires it up** —
    no `setupFiles` entry, no import for its `expect.extend` side effect. Confirmed via a second
    whole-plan grep (`setupFiles`/`jest-dom`): the only hit is Task 1's own devDependency list
    line. This stayed invisible through Tasks 23–24 because neither of their tests used a
    jest-dom-specific matcher (`toBe`/`toHaveBeenCalledWith`/RTL's own queries are enough) — Task
    25's own literal test snippet is the first to call `toBeInTheDocument()`, and running it
    exactly as written failed with `Invalid Chai property: toBeInTheDocument`, even though the
    rendered DOM was already fully correct (confirmed by inspecting the test's own debug output —
    every expected string was present, the matcher itself just didn't exist). **Fix:** added
    `frontend/src/setupTests.ts` (one line: `import "@testing-library/jest-dom/vitest"` — the
    already-installed package's own Vitest-specific auto-extend subpath, not a new dependency) and
    wired it into `vitest.config.ts`'s `test.setupFiles`. No code/test changes needed beyond that;
    re-ran `Results.test.tsx` after the fix: clean pass.
  - Two more harmless `React Router Future Flag Warning` messages on stderr, same as Task 24 —
    noted, not a finding.
  - `frontend` suite: 5/5 passing (up from Task 24's 4/4). `npm run build` **now stays green
    end-to-end** (both `tsc -b` and `vite build`, confirming the `index.html` fix above holds under
    a second, independent task). Repo-wide regression check: `backend/worker` 38/38,
    `backend/shared` 12/12, `backend/api` 16/16, `mcp-server` 17/17 — all unchanged.
  - No credential/secret handling — `createGithubIssue`'s call site in `Results.tsx` still carries
    no token of its own (same as Task 23's client wrapper); the GitHub-auth infra gap (Task 22,
    still open) applies once this button is used against a real deployment, not to anything added
    in this task's own code.
- **Task 26 (History page) ✅**, implemented verbatim from plan.md — no deviations, no plan bugs
  found (unlike Tasks 23's/25's). RED-verification failed clean (stub `History` renders nothing
  matching). `frontend` suite: 6/6 passing (up from Task 25's 5/5).
  - **Step 7/8, `frontend/Dockerfile` (multi-stage, nginx) — verified for real, same discipline as
    Tasks 17/22, not just written and trusted:** `docker build -f frontend/Dockerfile .` (repo-root
    context, matching `backend/worker`'s/`backend/api`'s established convention) succeeded; then
    `docker run` + `curl` against the live container confirmed nginx actually serves the built
    bundle (`HTTP 200`, real `index.html` with the correct hashed script tag) — proves the Task
    23/25 `index.html` fix holds *inside the container* too, not just local dev. Verification
    image/container removed after confirming.
  - **Observation, not a plan bug (the build succeeded as written, nothing the plan requires
    failed) — noted for the record only:** the Dockerfile's Step 7 text copies only
    `frontend/package.json` into the build stage, not `frontend/package-lock.json`, so
    `RUN npm install` inside the image re-resolves versions independently rather than reproducing
    the checked-in lockfile. Confirmed this actually causes drift, not just a theoretical
    possibility: the container build's own `npm install` log reported **7** `npm audit` findings
    where the host (lockfile-resolved) `npm audit` reports **8** — different dependency
    resolution, not a copy-paste discrepancy. Doesn't fail anything the plan's own steps check for,
    so not fixed here (would mean deviating from Step 7's literal `COPY frontend/package.json .`),
    but worth knowing before Task 32/37/38 build this image for real deployment: image contents
    aren't guaranteed to exactly match what `npm test`/`npm run build` verified locally.
  - `npm run build` still fully green end-to-end. Repo-wide regression check: `backend/worker`
    38/38, `backend/shared` 12/12, `backend/api` 16/16, `mcp-server` 17/17 — all unchanged.
  - No credential/secret handling, no new dependencies.

**Phase 5 self-check (post-Task 26, before push/merge):**
- Grepped `frontend/src/`, `index.html`, `Dockerfile`, `vitest.config.ts`, `tsconfig.json`,
  `package.json` for `TODO`/`FIXME`/`XXX`/`HACK` markers, `console.log`/`console.debug`/
  `console.warn`/`console.error`/`debugger` statements, and secret-shaped strings
  (`ghp_`/`github_pat_`/`AWS_SECRET`/inline `api_key=`/`token=` literals) — **all clean, zero
  hits.** No `.env`/`.env*` files anywhere under `frontend/`. No leftover debug/scratch files
  (this session's own throwaway debug tests and probe files were removed immediately after each
  one confirmed its finding, per the same hygiene precedent as Phase 4's health check).
- **File-state audit:** `git diff --stat main...feature/phase-5-frontend` shows exactly 20 files
  changed — all Phase 5 scope (the 4 tasks' page/test files, `api/client.ts`/`types.ts`,
  `App.tsx`/`main.tsx`, `index.html`, `Dockerfile`, `vitest.config.ts`, `setupTests.ts`,
  `tsconfig.json`, `package.json`/`package-lock.json`, `.gitignore`, this doc) — nothing stray.
  Working tree clean; no leftover Docker images/containers from this session's verification runs.
- **Housekeeping correction while checking this doc's own accuracy (per the user's explicit
  ask):** the Phase 4 section header above still read "not yet merged" even though PR #13 merged
  it (confirmed at the start of this phase) — fixed to say "merged via PR #13," same class of
  stale-header fix as Phase 3's own health check made.
- **This phase found four real bugs in the plan's own literal snippets/setup, all fixed or
  explicitly flagged, none silent:** Task 23's `options?: RequestInit`/`expect.anything()`
  mismatch (fixed), the missing `@types/react`/`@types/react-dom` (flagged, then user-approved and
  added), the missing `frontend/index.html` (flagged, then user-approved and added), and the
  never-wired `@testing-library/jest-dom` (fixed, no new dependency). All four are documented
  above in their originating task's entry, with the empirical evidence that confirmed each one
  before fixing — none applied on inspection alone.

**Is a dedicated Phase 5 health check (matching Phase 3's/4's format) warranted before
push/merge? No — recommend skipping it, for reasons specific to this phase's shape, not as a
default:**
- **Risk profile is fundamentally smaller than Phase 3/4.** Every Phase 5 task is a thin,
  presentational React component consuming an already-tested `client.ts` wrapper; there's no
  business logic, no real external service call, no AWS resource, and no credential/auth boundary
  anywhere in this phase's own code (`fetch` is mocked in every test, and the GitHub-auth gap
  belongs to `backend/api`'s Task 22, not anything added here). Phase 3's health check mattered
  because Task 17 wired 16 already-merged nodes together for the first time and found real,
  state-corrupting bugs (a dropped `AgentState` key, wrong `unittest.mock.patch` targets, live
  AWS credentials leaking into a subprocess); Phase 4's mattered because of real DynamoDB
  GSI/dependency/auth gaps with production consequences. Nothing in Phase 5 has that class of
  blast radius — the worst-case failure mode here is a broken link or a page that shows "Loading…"
  forever, immediately visible in a browser, not silent data corruption or a security exposure.
- **The "run it for real" checks a dedicated health check would add were already done, per-task,
  throughout this phase — not concentrated at the end the way Phase 3/4 did it.** `npm run build`
  was run after every single task (not just once at the end); the Dockerfile was built *and* run
  *and* hit with a real `curl` request in this same session, not deferred; the repo-wide Python
  regression check ran after every task, four times total, not once. A dedicated health check's
  main value-add over what already happened would be re-running things an extra time to catch
  flakiness — a much smaller marginal gain here than it was for Phase 3/4's first-time
  integration risk.
- **One residual gap worth naming honestly, even though it doesn't change the recommendation:**
  no test in this phase renders `<App />` itself and exercises real routing between pages — every
  page test uses its own isolated `MemoryRouter` (per the plan's own literal snippets), so nothing
  proves `/` → `/analyses/:id` → `/history` navigation actually works end-to-end through the real
  route table. This is the same *class* of gap Phase 3's Task 17 health check went looking for
  (isolated unit tests green, nothing proving the wiring), but the consequence here is far
  smaller (a broken `<Route>` path is immediately obvious the first time anyone opens the app,
  not a silent state-corruption bug) — flagging it as optional, cheap insurance if extra
  confidence is wanted (one small `App.test.tsx` rendering `<App />` inside a `MemoryRouter` and
  clicking through), not a blocker for merging as-is.

**Decision: skip the full health check, close the one flagged gap as targeted insurance
instead.** Added `frontend/src/App.test.tsx` (3 cases) — renders the real `App` (its actual
`BrowserRouter`/`Routes` tree, not a re-declared route list) via `window.history.pushState(...)`
+ `render(<App />)`, so the paths exercised are whatever `App.tsx` really has, not a copy that
could drift from it. Covers: mounts cleanly and renders `Home` at `/`; renders `Results` at
`/analyses/:id`, confirming the `:id` param reaches `getAnalysis` (mocked, since this is a
routing check, not a re-test of `Results`' own already-covered rendering logic); renders
`History` at `/history`. **Sanity-checked that the test actually catches breakage, not just that
it passes:** temporarily mangled `/analyses/:id` to `/wrong-path/:id` in `App.tsx`, re-ran — the
new test failed exactly as expected (the `getAnalysis` call never happened, so `waitFor` timed
out); reverted (`git diff` on the file came back empty afterward, confirming a clean revert) and
re-ran to confirm green again. Deliberately minimal, per the user's ask — one file, a handful of
cases, no duplication of each page's own already-existing coverage.
- `frontend` suite: **9/9 passing** across 6 files (up from Task 26's 6/6 — this test file adds 3
  cases). `npm run build` still fully green end-to-end. Repo-wide regression check (re-run once
  more before push, per the user's ask): `backend/worker` 38/38, `backend/shared` 12/12,
  `backend/api` 16/16, `mcp-server` 17/17 — all unchanged.
- No credential/secret handling, no new dependencies.

---

### Phase 6 — Terraform — Task 27 (`networking` module + `shared` environment scaffolding) ✅ complete

- Branch: `feature/phase-6-terraform`, cut from `main` after confirming PR #14 (Phase 5) merged
  (local `main` was 14 commits behind `origin/main`, same stale-clone pattern as every prior
  phase — confirmed via `gh pr list` before trusting it, then `git fetch` + `git pull --ff-only`,
  `ffde7be` → `84c7536`).
- **Pre-work (before Task 27): re-verified the GitHub-auth follow-up empirically instead of
  trusting the existing log entry's wording.** Confirmed Phase 6 (Tasks 27–31) has no GitHub/MCP
  scope at all, and live-tested `ghcr.io/github/github-mcp-server:latest` (`v1.8.0`) directly:
  `GITHUB_PERSONAL_ACCESS_TOKEN` set in the container's own environment does **not** satisfy HTTP
  mode's auth — an unauthenticated request still gets `401` with a
  `WWW-Authenticate: Bearer resource_metadata=...` challenge; a request with a real
  `Authorization: Bearer` header succeeds. Conclusion: a token-injecting sidecar/gateway is
  genuinely needed and remains **explicitly unscheduled** (not assigned to Phase 6 or 7). Full
  evidence and the corrected Open Questions entry are below; committed alone
  (`3d369ac docs: correct project-log's GitHub-auth follow-up...`) before starting Task 27 itself.
- **Task 27 ✅**, implemented from plan.md with two syntax fixes (both confirmed empirically via
  `terraform init`, not just by inspection) and one plan-gap fill:
  1. **Real, confirmed bug: the plan's `main.tf` snippet writes the security group's
     `ingress`/`egress` blocks as semicolon-separated single lines**
     (`ingress { description = "..."; from_port = 22; ... }`) — this is invalid HCL. Confirmed
     empirically: ran `terraform init` against the literal snippet first, got
     `Error: Invalid character` / `Error: Invalid single-argument block definition` pointing at
     line 35. Fixed by expanding each `ingress`/`egress` block to one argument per line (standard
     HCL block syntax) — same six blocks, same argument values, no semantic change.
  2. **Real, confirmed bug: the plan's `variables.tf` snippets use comma-separated single-line
     variable blocks** (`variable "admin_cidr" { type = string, description = "..." }`,
     and `shared/variables.tf`'s `aws_region` the same way) — also invalid HCL (`Error: Invalid
     single-argument block definition`, same class of error as #1). Fixed the same way — one
     argument per line, values unchanged. Both bugs are the same underlying mistake (the plan's
     condensed one-line presentation isn't valid Terraform syntax, only valid-looking shorthand),
     not two independent issues.
  3. **Plan gap, flagged rather than silently filled: `terraform/environments/shared/backend.tf`
     is listed in Task 27's Files list but no task anywhere in plan.md shows its content** —
     grepped the full plan and design.md for `backend.tf`/`backend "s3"`/`tfstate`; the only hits
     are Task 30's `dev`/`prod` `main.tf`, which reads `shared`'s state via
     `terraform_remote_state` with `backend = "local"` (Terraform's implicit default when no
     `backend` block is configured — needs no file content to work) and a comment
     (`# or "s3" with a real backend config — see backend.tf`) that treats `backend.tf` as a
     reserved-but-unused location for a future remote backend, never actually defining one.
     Task 31's own validation command (`terraform init -backend=false`) forces local state
     regardless, so this file's content has no effect on anything the plan itself checks. Filled
     it with a comment-only placeholder documenting exactly this (local state is the default;
     file reserved for a future `backend "s3"` block) — inert, zero effect on `init`/`validate`,
     easy to replace later if remote state is adopted. Not a stop-and-ask case per CLAUDE.md's
     dependency-version-bump carve-out (nothing to approve, no version change) — flagged here per
     the "explain, don't silently make" rule instead.
  4. **Not a bug, not fixed:** `shared/main.tf`'s `provider "aws" {}` block has no matching
     `required_providers.aws` entry (only `random`/`tls`/`local` are declared) — this is the
     plan's own literal text, and Terraform's implicit-provider inference from the `aws_*`
     resource-type prefix handles it fine; `terraform init` resolved `hashicorp/aws v6.58.0`
     (latest, unconstrained) alongside `random v3.9.0`/`tls v4.3.0`/`local v2.9.0` (all satisfying
     their `~>` constraints). Flagging only because an unconstrained provider can resolve to a
     different version on a future `init` — not a version bump I made or am asking to make, just
     the plan's as-written behavior, worth knowing about before Task 28 adds `ec2` resources on
     top of it.
  - **Validation:** `cd terraform/environments/shared && terraform init && terraform validate` —
    `Success! The configuration is valid.` (re-run clean from a fresh `.terraform`/lock-file
    state to confirm it isn't order-dependent). No `terraform apply` run — out of scope per the
    plan (Task 31 documents the real apply order; that's a real-AWS-spend action requiring
    explicit confirmation first).
  - `terraform fmt -recursive -check -diff` (run informationally, not required by this task) flags
    one cosmetic misalignment in `aws_subnet.public`'s `=` columns — present verbatim in the
    plan's own snippet, left as-is since Task 31 is explicitly the task that runs `fmt` across the
    whole tree.
  - `.gitignore` already covers `.terraform/`, `terraform.tfstate*`, and `*.pem` — no changes
    needed there for this task. `.terraform.lock.hcl` is committed (Terraform's own
    recommendation), `.terraform/`'s downloaded provider binaries are not (already gitignored).
  - No credential/secret handling — this task never touches the GitHub-auth question at all
    (that's Task 28+/Phase 7 territory); no AWS credentials were used since no `apply` ran.

### Task 28 (`ec2` module — control-plane + worker via kubeadm) — ✅ **complete, cluster verified converged for real (third apply attempt)**

- Created `terraform/modules/ec2/{main,variables,outputs}.tf` +
  `cloud-init-{control-plane,worker}.yaml.tpl`; wired `module "ec2"` into
  `terraform/environments/shared/main.tf` alongside Task 27's `networking` module, per plan.md.
- **Three plan-snippet bugs found, all confirmed empirically via `terraform init`/`validate`
  against the literal snippets first, not by inspection:**
  1. & 2. **Same class of bug as Task 27's two findings, reproduced fresh here:**
     `ec2/variables.tf`'s `instance_type` used a comma-separated single-line block
     (`variable "instance_type" { type = string, default = "t3.large" }`) — invalid HCL,
     confirmed via `Error: Invalid single-argument block definition` pointing at the exact line.
     Fixed the same way as Task 27 (one argument per line, values unchanged). This is now the
     second phase-6 task with this exact mistake in the plan's own condensed one-liner
     presentation — worth expecting again in Tasks 29/30.
  3. **New bug class, only catchable by provider-schema validation, not syntax
     inspection:** `local_sensitive_file.ssh_private_key` used `file_permissions` (plural) —
     `terraform validate` (which loads the initialized `local` provider's real schema, not just
     HCL grammar) failed with `Error: Unsupported argument ... Did you mean "file_permission"?`.
     Fixed by renaming to the singular `file_permission`, value (`"0600"`) unchanged. This
     wouldn't have been caught by `terraform fmt` or syntax review alone — only by actually
     initializing the provider and validating against its schema, same "run it for real, don't
     just read it" discipline as every prior phase's health checks.
- **Plan-list inaccuracies, flagged rather than silently resolved:**
  - Task 28's Files list says "Modify: `terraform/environments/shared/main.tf`, `variables.tf`"
    but Step 4 only shows a `main.tf` diff — no new root variable is actually needed for the
    `ec2` wiring (`instance_type` has a module-level default; `public_subnet_id`/
    `security_group_id` come from `module.networking`'s own outputs, not new user-supplied
    variables). Left `shared/variables.tf` unchanged rather than inventing an unneeded variable.
  - Step 4 also says to append `*.pem` and the specific
    `terraform/environments/shared/testscope-k8s-keypair.pem` path to `.gitignore` — both are
    already fully covered by the `*.pem` line Task 27 added (see Task 27 entry above). Skipped
    re-adding to avoid a duplicate/redundant line; `git check-ignore` behavior is unchanged
    either way.
- **Noted, not acted on (per the user's explicit instruction — this is the same unconstrained
  `aws` provider flagged in Task 27, still not pinned by any task's plan text):** `terraform init`
  in this task's own directory re-resolved `hashicorp/aws` — landed on the same `v6.58.0` as
  Task 27's init (no drift observed between the two), alongside `random v3.9.0`/`tls v4.3.0`/
  `local v2.9.0` all still satisfying their `~>` constraints. Not a version bump made or
  requested — just confirming the earlier flag hasn't silently become a problem yet.
- **Validation:** `terraform init && terraform validate` — `Success! The configuration is
  valid.` `terraform fmt -check -diff` (informational only) flags the `module "ec2"` block's
  column alignment, present verbatim in the plan's own snippet — left for Task 31.
- **`terraform plan -var="admin_cidr=176.229.150.57/32"` reviewed and shown to the user first**
  (this machine has real, live AWS credentials — `aws sts get-caller-identity` resolves to
  account `228281126655`) — 15 resources to add, 0 to change, 0 to destroy, security group
  correctly scoped `admin_cidr` to SSH/6443 only. User confirmed the plan before any `apply` ran.
- **First `apply` attempt: partial failure, a real plan bug only catchable by the live AWS API.**
  13 of 15 resources created, then failed on the security group's ingress rules:
  `from_port (0) and to_port (65535) must both be 0 to use the 'ALL' "-1" protocol!` — the
  plan's "Cluster-internal" self-referencing rule (`protocol = "-1"`, `from_port = 0`,
  `to_port = 65535`) violates an AWS API constraint that `terraform validate` has no way to
  check (it's AWS-side semantics, not HCL/provider schema). No `aws_instance` had been created
  yet at this point (they depend on the security group's output) — **zero compute billing**
  during this failure. Fixed `to_port` from `65535` to `0` — semantically identical, since AWS
  ignores the port range entirely for protocol `-1` (already means "all ports"); this only
  satisfies the API's validation, doesn't change what the rule allows.
- **Second `apply` attempt (after the fix): blocked by a real, intentional account guardrail,
  not a bug.** `403 UnauthorizedOperation` on `ec2:RunInstances`, explicit deny. Decoded via
  `aws sts decode-authorization-message` (read-only) rather than guessing: an IAM policy named
  **`DenyLargeInstanceTypes`** blocks `ec2:RunInstances`/`ec2:ModifyInstanceAttribute` for
  anything outside `{t2,t3,t4g}.{nano,micro,small,medium}` — the plan's `instance_type` default
  (`t3.large`) is one size above the allowed ceiling. **Flagged to the user rather than silently
  routed around; user chose `t3.medium`** (largest allowed). Changed `ec2/variables.tf`'s default
  from `t3.large` to `t3.medium`, with an inline comment recording why. Still zero compute
  billing at this point (still no `aws_instance` created).
- **Third `apply` attempt: blocked by a second account guardrail, same pattern.** New explicit
  deny, this time on the EBS volume resource. Decoded the same way: **`LimitVolumeSize`** denies
  any EC2 volume over 30GB — the plan's `root_block_device { volume_size = 40 }` exceeds it.
  Flagged to the user; **user chose 30GB** (the max allowed). Changed both instances'
  `root_block_device.volume_size` from `40` to `30` in `ec2/main.tf`, with an inline comment.
- **Fourth `apply` attempt: succeeded.** `Apply complete! Resources: 2 added, 0 changed, 0
  destroyed.` Real resources created:
  - `control_plane`: instance `i-06bab93b4c588e5c3`, public IP `3.87.92.4` (at creation time)
  - `worker`: instance `i-0819b40cfaece6ae4`, public IP `54.242.230.30` (at creation time)
  - `worker_iam_role_arn`: `arn:aws:iam::228281126655:role/testscope-k8s-worker-role`
  - `ssh_private_key_path`: `./testscope-k8s-keypair.pem`, confirmed `-rw-------` (0600),
    owned by the local user, never printed/logged
  - Both launched `2026-08-09T20:50:3x/5xZ` UTC.
- **Cluster-convergence verification (Step 5) could NOT be completed — the actual outcome, not
  "apply succeeded":** while polling `cloud-init status --wait` over SSH on the control-plane,
  the SSH session was cut and both instances' public IPs disappeared. `describe-instances`
  showed both **`stopped`** (`Client.UserInitiatedShutdown`). Root-caused via CloudTrail (read-only
  `aws cloudtrail lookup-events`): an automated Lambda, `aws-learning-budget-keeper-function`
  (role `LearningBudgetKeeperLambdaRole`), issued `StopInstances` against both instances at
  **2026-08-09T21:00:5xZ** — roughly **10 minutes after launch**. This Lambda runs on a fixed
  schedule via EventBridge rule `learning-budget-keeper-schedule`
  (`cron(0 13,21 * * ? *)` — every day at **13:00 and 21:00 UTC**), confirmed via `aws events
  list-rules` (read-only). Ten minutes is nowhere near enough time for cloud-init's
  apt-get-install-through-metrics-server sequence to finish, so **kubeadm never converged** —
  this is an account-level constraint discovered live, not a code or config defect in Task 28
  itself. **Not investigated further and not acted on** (no attempt to modify, pause, or route
  around the Lambda/EventBridge rule — that's the user's account automation and their call).
- **Current real state (as of this entry): both instances `stopped`, not terminated** — EBS
  volumes and all other resources intact. Public IPs deallocated (normal AWS behavior for a
  stopped non-Elastic-IP instance) — the IPs above are now stale. **Operationally important:**
  simply restarting these two specific stopped instances will *not* re-run cloud-init's
  `runcmd` — cloud-init treats a stop/start of the same instance-id as "first boot already
  happened" and will not redo the kubeadm bootstrap, so whatever partial state apt/kubeadm was
  in when power was cut is what's there now (not a working cluster). A clean redo needs a fresh
  `terraform destroy`/`apply` cycle (new instance-ids → cloud-init runs fresh), timed to land
  outside the 13:00/21:00 UTC stop windows.
- **Billing status at time of writing:** both instances `stopped` → EC2 compute charges paused
  (AWS does not bill compute time for stopped instances), no public-IPv4 charge (address
  released). The two 30GB root EBS volumes are still live and still billing their small storage
  cost (~$4.80/month combined) until the instances are destroyed. Full instance-hour billing
  would resume immediately if/when the instances are restarted or replaced.
- Code committed on `feature/phase-6-terraform` — module/wiring fixes (`t3.medium`, `30GB`)
  included.
- **User confirmed the instances were unrecoverable (cloud-init won't re-run on a stop/start of
  the same instance-id) and directed a full teardown.** Ran `terraform plan -destroy` first and
  showed the exact 15-resource list before doing anything else — matched the 15 resources this
  same `apply` had created, `0 to add, 0 to change, 15 to destroy`, nothing partial or
  unexpected. User confirmed; ran `terraform destroy -auto-approve` with the same `admin_cidr`.
  **`Destroy complete! Resources: 15 destroyed.`**
- **Verified nothing billing-relevant remains — via `terraform state list` (empty) and, more
  importantly, direct live AWS checks (not just trusting Terraform's own bookkeeping), each
  scoped to this project's own tagged/named resources rather than a broad account-wide scan**
  (this AWS account turned out to be a shared multi-tenant classroom/learning account with many
  other users' resources visible on an unfiltered `describe-instances` — noted for awareness,
  not investigated further, and nothing from it is recorded here beyond that fact):
  - Both EC2 instances (`i-06bab93b4c588e5c3`, `i-0819b40cfaece6ae4`): `terminated`.
  - EBS volumes tagged `testscope-*`: none (`[]`) — the two 30GB root volumes went with their
    instances via `delete_on_termination` (the plan's default, never overridden).
  - VPC tagged `testscope-vpc`, security group named `testscope-k8s-cluster`: none (`[]`).
  - Key pair `testscope-k8s-keypair`: `InvalidKeyPair.NotFound` (confirms deleted).
  - IAM role `testscope-k8s-worker-role` / instance profile `testscope-k8s-worker-profile`:
    `NoSuchEntity` (confirms deleted).
  - Local `testscope-k8s-keypair.pem`: no longer on disk (destroyed by
    `local_sensitive_file`'s own destroy).
  - **No billing-relevant resources remain from this apply.** The only real-money exposure this
    session was the ~10 minutes both `t3.medium` instances were actually running before the
    budget-keeper Lambda stopped them, plus a few hours of two 30GB EBS volumes existing before
    this destroy — both trivial.
- **Retry, timed by the user for ~7 hours of margin before the next 13:00 UTC (16:00 Jerusalem)
  budget-keeper window: `terraform apply -var="admin_cidr=176.229.150.57/32"` (plan already
  reviewed in the prior attempt, auto-approve used per the user's explicit instruction).**
  Succeeded cleanly, 15/15 resources, no guardrail/API errors (both fixes from the prior attempt
  held). New instances: `control_plane` `i-071f33fcd461aa949` (`13.220.54.97`), `worker`
  `i-00f5f584bf5de5a46` (`3.95.219.158`). **Actively monitored, not just polled once** — SSH in
  repeatedly to check `cloud-init status` and tail `/var/log/cloud-init-output.log` on both
  instances rather than assuming success.
- **A second real, confirmed bug found this way — cloud-init was not actually stuck, it was
  looping forever on a bug that had already failed:** after ~20 minutes both instances still
  showed `cloud-init status: running`, which is unusual on its own — checked the actual log
  content (not just the status field) rather than continuing to wait, and found `kubeadm init`
  had failed at the very first preflight check:
  `[ERROR FileContent--proc-sys-net-ipv4-ip_forward]: /proc/sys/net/ipv4/ip_forward contents are
  not set to 1`. **Root cause: plan.md's `cloud-init-control-plane.yaml.tpl`/
  `cloud-init-worker.yaml.tpl` never set the standard, always-required kubeadm networking
  prerequisites** (`br_netfilter`/`overlay` kernel modules, `net.ipv4.ip_forward=1`,
  `net.bridge.bridge-nf-call-iptables=1`) before calling `kubeadm init`/`kubeadm join` — a plain
  omission from the plan's own script, not an environment quirk. Because `kubeadm init` never
  produced `/etc/kubernetes/admin.conf`, every subsequent `kubectl` call in the script failed,
  including the one inside `until kubectl ... get deployment ingress-nginx-controller ...; do
  sleep 5; done` — that loop could **never** exit on its own (kubectl would never succeed), which
  is why `cloud-init status` stayed `running` indefinitely rather than erroring out cleanly. The
  worker was independently stuck in its own `until nc -z ... 6443; do sleep 10; done` loop for
  the same underlying reason (API server never started). Neither instance would have converged
  no matter how long they were left running.
  - **Fixed in both templates** (control-plane and worker both run `kubeadm init`/`kubeadm join`
    and both hit the identical preflight check) by adding the standard, official kubeadm
    prerequisite sequence right after the `containerd` restart and before the Kubernetes apt
    repo setup: load `overlay`/`br_netfilter` kernel modules, write
    `net.bridge.bridge-nf-call-iptables`/`net.bridge.bridge-nf-call-ip6tables`/`net.ipv4.ip_forward`
    to `/etc/sysctl.d/k8s.conf`, `sysctl --system`. User confirmed destroy-fix-reapply rather than
    continuing to inspect the stuck instances.
  - Destroyed the broken instances first (`terraform destroy -auto-approve`, ran in the
    background past the 120s foreground limit — confirmed complete via a direct
    `aws ec2 describe-instances` check rather than waiting on buffered output, then
    `Destroy complete! Resources: 15 destroyed.` once the buffered log flushed), applied the
    cloud-init fix, `terraform validate` clean, re-applied.
- **Third apply attempt: succeeded, and the cluster converged for real this time — verified, not
  assumed.** New resources: `control_plane` `i-0887a982c0501958c` (`107.23.155.19`), `worker`
  `i-0606ccf79b1c0c1af` (`3.80.37.183`). Monitored the same way (repeated `cloud-init status` +
  log tail checks, not a single poll):
  - `apply` invoked 06:37:10 UTC → completed 06:38:23 UTC.
  - Control-plane `cloud-init status: done` at 06:39:06 UTC.
  - Worker `cloud-init status: done` at 06:39:22 UTC (`kubeadm join` succeeded — log showed the
    standard "Run 'kubectl get nodes' on the control-plane to see this node join the cluster").
  - All pods across all namespaces reached `Running`/`Completed` by 06:40:44 UTC (polled every
    20s, checked via `kubectl get pods -A` for anything not in those two states).
  - **Total wall-clock from `apply` invocation to fully-converged cluster: ~3.5 minutes** — far
    faster than the ~7-hour safe margin before the next budget-keeper window; gives a real,
    observed number for planning future applies/retries instead of guessing.
  - **Verified against the plan's exact Step 5 success criteria, not just "pods are Running":**
    `kubectl get nodes` — both `Ready` (`ip-10-0-1-35` control-plane, `ip-10-0-1-176` worker).
    `kubectl get pods -n ingress-nginx` — controller `1/1 Running`; confirmed `hostNetwork: true`
    genuinely took effect (not just set in the spec) via
    `kubectl get pod ... -o jsonpath='{.status.hostIP} {.status.podIP}'` — both equal
    `10.0.1.176`, the worker's own node IP, exactly the plan's stated proof criterion.
    `kubectl get pods -n kube-system -l k8s-app=metrics-server` — `1/1 Running`; functionally
    confirmed (not just pod-status) via `kubectl top nodes`, which returned real CPU/memory
    numbers for both nodes. Calico (`calico-node` ×2, `calico-kube-controllers` ×1, all in
    `kube-system` — this Calico manifest version doesn't use a separate `calico-system`
    namespace, unlike some others) — all `Running`.
  - **Extra, beyond-the-plan verification:** `curl http://<worker_public_ip>/` from this machine
    directly (not via SSH, a genuine external request) — `HTTP 404`, ingress-nginx's own default
    backend response (expected and correct, since no application `Ingress` resource exists yet)
    — proves the controller is really listening on the worker's public IP via `hostNetwork`,
    reachable from the real internet, not just internally reachable within the VPC.
- **Status: Task 28 is genuinely complete** — module code committed, real cluster stood up and
  independently verified converged against every one of the plan's Step 5 criteria plus one
  extra external check. Cluster is currently live and **billing** — both `t3.medium` instances
  running, will be auto-stopped by the account's budget-keeper Lambda at 13:00 UTC (16:00
  Jerusalem) if still running at that time.

### Task 29 (`iam`/`s3`/`dynamodb`/`sqs` modules, parameterized by `env`) — ✅ complete, validate-only (no `apply` — plan doesn't call for one)

- Created `terraform/modules/{iam,s3,dynamodb,sqs}/*` per plan.md — four standalone,
  independently-validated modules, none wired into any environment yet (that's Task 30's job).
  Confirmed against plan.md before starting: **Task 29's own Step 5 is validate-only**
  (`for m in s3 dynamodb sqs iam; do terraform init -backend=false && terraform validate; done`)
  — no `apply` anywhere in this task's text, and these modules have no environment root to apply
  *from* yet regardless (`dev`/`prod` don't exist until Task 30). So there was nothing to apply
  and, per the user's specific ask, no possibility of a new account-guardrail IAM deny surfacing
  this session — that check only becomes possible once Task 30 actually applies these modules
  for real.
- **One plan-snippet bug found, same class as Tasks 27/28's recurring one, confirmed empirically
  via `terraform validate` against the literal snippet first:** `dynamodb/main.tf`'s four
  `attribute` blocks used semicolon-separated single-line arguments
  (`attribute { name = "analysis_id"; type = "S" }`) — invalid HCL, same
  `Error: Invalid character`/`Invalid single-argument block definition` as Task 27's
  ingress/egress blocks and identical in shape. Fixed the same way: one argument per line, values
  unchanged. This is now the **third** occurrence of this exact plan-authoring mistake across
  Phase 6 (Task 27's `ingress`/`egress`, Task 28's `instance_type`/`file_permissions`-adjacent
  variable blocks, now this) — condensed single-line block syntax in the plan's own snippets is
  reliably wrong wherever it appears; worth assuming Task 30's `monitoring` module snippet
  (`aws_cloudwatch_metric_alarm`, similar block-heavy shape) will need the same treatment.
- **Not a bug — worth distinguishing from the above:** the `iam` module's inline policy
  statements (`{ Effect = "Allow", Action = [...], Resource = "..." }`, comma-separated on one
  line inside `jsonencode({...})`) validated cleanly with no changes needed. These are HCL
  **object-constructor expressions** (map literals), not block syntax — commas *are* valid there,
  newlines are also valid; only block syntax (`resource`/`variable`/`ingress`/`attribute`/etc.)
  forbids commas. Confirmed by the fact `terraform validate` raised zero complaints about this
  file, unlike the three prior findings — checked deliberately before assuming this task would
  have a fourth instance of the same bug class.
- **Deprecation warning, not an error, not fixed:** `dynamodb/main.tf` validates with `Success!`
  but 4 warnings — `hash_key is deprecated. Use key_schema instead` (the top-level `hash_key` plus
  3 more from the same underlying cause, likely the GSIs' `hash_key`/`range_key` args under the
  currently-resolved `hashicorp/aws v6.58.0`). Plan's snippet still works as written and this
  doesn't block anything `terraform validate`/`plan`/`apply` check for — left as-is rather than
  rewriting to `key_schema`, consistent with the "don't diverge from the plan's literal snippets
  over non-blocking findings" precedent already set for Tasks 27/28's `fmt`-only issues (deferred
  to Task 31, which is the task that actually owns a repo-wide cleanup pass).
- **Validation:** `terraform init -backend=false && terraform validate` — `Success!` for all four
  modules (`s3`, `sqs`, `iam` with zero warnings; `dynamodb` with the 4 deprecation warnings
  noted above, still `Success!`). Each module's own `.terraform.lock.hcl` committed per
  Terraform's own recommendation, matching Tasks 27/28's precedent.
- **Environment note, not a plan issue:** `terraform init`/`validate` in this sandboxed
  environment intermittently hung for 15–60+ seconds *after* printing `Success!` — root-caused to
  Terraform's default "checkpoint" upgrade-check phoning home, likely slow/blocked on this
  network. Added `CHECKPOINT_DISABLE=1` to `~/.bashrc` (a local tooling speedup, not a repo
  change) rather than re-diagnosing this again in Task 30/31.
- No credential/secret handling, no AWS resources created or touched (validate-only, no live AWS
  calls beyond provider-plugin download/registry lookups).

### Task 30 (`monitoring` module + `dev`/`prod` environments) — ✅ complete, validate-only (no `apply` — plan doesn't call for one, confirmed before starting per the user's explicit ask)

- Created `terraform/modules/monitoring/{main,variables}.tf` and
  `terraform/environments/{dev,prod}/{main,variables,backend}.tf` per plan.md — this is the
  first task wiring `networking`/`ec2`/`iam`/`s3`/`dynamodb`/`sqs`/`monitoring` together into
  real environment roots, but doing so is still validate-only: Task 30's own Step 3 is
  `terraform init -backend=false && terraform validate` for `dev`/`prod`, no `apply` anywhere in
  this task's text. **Confirmed explicitly before starting, per the user's specific question:**
  no real apply happens in Task 30, so there was no possibility of this creating a second live
  cluster alongside Task 28's — `dev`/`prod` don't touch `ec2`/`networking` at all (they only
  wire `s3`/`dynamodb`/`sqs`/`iam`/`monitoring`), and even those aren't applied here. (For
  context, not part of this task: the Task 28 cluster was still `running`, not yet auto-stopped,
  as of this task's start — unrelated to Task 30's own scope.)
- **Plan-snippet bugs found: exactly the two predicted, both confirmed empirically via
  `terraform validate`/`init` against the literal snippets first, not assumed from precedent
  alone:**
  1. `dev/variables.tf` (and identically `prod/variables.tf`, same snippet substituted verbatim):
     `variable "aws_region" { type = string, default = "us-east-1" }` — the same
     comma-separated single-line block bug as Task 27's `shared/variables.tf` and Task 28's
     `ec2/variables.tf`. Fixed the same way, values unchanged.
  2. `dev/main.tf`'s (and `prod/main.tf`'s) three `module` one-liners —
     `module "s3" { source = "../../modules/s3"; env = "dev" }` (and identically for
     `dynamodb`/`sqs`) — the same semicolon-separated single-line block bug as Task 27's
     `ingress`/`egress` and Task 29's `attribute` blocks. `terraform init`/`validate` only
     surfaced the first (`module "s3"`) explicitly before stopping enumeration in that file, but
     since `dynamodb`/`sqs` are byte-identical in shape, fixed all three preemptively rather than
     rediscovering the same bug twice more; re-validated clean afterward, confirming no further
     surprises in that file. Fixed the same way — one argument per line, values unchanged.
  - **Correctly predicted NOT to have the bug, and confirmed clean:** the `monitoring` module's
    `aws_cloudwatch_metric_alarm` blocks are fully multi-line in the plan's own snippet (each
    argument already on its own line, including `dimensions = { QueueName = "..." }`, which is a
    single-key object-constructor value assignment — not block syntax, and not this bug class
    regardless of key count). Validated clean on the first pass, no fix needed — checked
    deliberately rather than assuming every block-shaped resource in this task would need the
    same treatment, same discipline as Task 29's `iam` module finding.
- **Plan-doc/code inconsistency, flagged rather than silently resolved or silently ignored:**
  Task 30's own **Interfaces** text states `dev`/`prod` consume `worker_iam_role_arn`,
  `control_plane_public_ip`, `worker_public_ip` "from `environments/shared` ... referenced via
  `terraform_remote_state` data source" — and the `data "terraform_remote_state" "shared"` block
  is indeed declared in both `main.tf` files. **But nothing in either file's actual code reads
  `data.terraform_remote_state.shared.outputs.*` anywhere** — `module "iam"`'s
  `instance_role_name` is a hardcoded literal `"testscope-k8s-worker-role"` instead, and
  `control_plane_public_ip`/`worker_public_ip` aren't referenced at all in this task's code.
  Not fixed: the hardcoded string happens to be correct (it's exactly what Task 28's `ec2` module
  names the role), so nothing is functionally broken and `terraform validate` raises no complaint
  about the unused data source — but the Interfaces text and the actual code disagree about
  *how* that value gets there. Left as a documentation/code mismatch to be aware of, not silently
  smoothed over by rewriting the code to match the prose (that would be more than the minimal fix
  this task's own validate step calls for) or by editing the prose (out of scope for implementing
  a task, not documenting one).
- **Validation:** `terraform init -backend=false && terraform validate` — `Success!` for
  `monitoring`, `dev`, and `prod` (the latter two carry the same 4 non-blocking `dynamodb`
  `hash_key`/`range_key` deprecation warnings already noted in Task 29, nothing new). Each
  directory's own `.terraform.lock.hcl` committed per established precedent.
- No credential/secret handling, no AWS resources created or touched.

### Task 31 (Terraform validation and documented apply order) — ✅ complete, Phase 6's designated cleanup point for everything flagged in Tasks 27–30

- **Confirmed against plan.md before starting:** Task 31's own scope is fmt + validate + a
  documentation file (`terraform/README.md`) — "Interfaces: none — this task documents and
  verifies, it doesn't add new resources." No `apply` anywhere in this task's text either.
- **Item 1 — `aws` provider left unconstrained (flagged Task 27): asked before deciding, per
  standing convention.** User chose to pin to `~> 6.58` (matching the version resolved
  consistently across every `init` this phase — Tasks 27–30 all landed on `v6.58.0`, zero
  drift observed). **Implementation note beyond what the question anticipated:** `shared` was
  the only root with a `required_providers` block at all (for `random`/`tls`/`local`) — `dev`
  and `prod` had *no* `required_providers` block whatsoever, meaning each would independently
  resolve "latest `aws`" on its own `init`, completely unaffected by anything declared in
  `shared` (separate Terraform root configurations don't share provider constraints). Added the
  `~> 6.58` pin to all three roots' own `required_providers` blocks, not just `shared`'s, so the
  pin is actually effective everywhere. Re-validated all three afterward — `Success!` for all,
  same `v6.58.0` resolved, lock files now record the constraint (hashes/version unchanged, only
  a new `constraints = "~> 6.58"` line added — confirmed via diff, not just assumed).
- **Item 2 — `terraform fmt` cosmetic alignment quirks (flagged Tasks 27/28): user directed to
  just run it, no question needed.** `terraform fmt -recursive -check -diff` across the whole
  tree found 8 files with misalignment (the two originally flagged, plus `iam`'s wrapped
  `Resource` line, `monitoring`'s and `sqs`'s inline-comment spacing, and a couple more of the
  same class not individually flagged before) — all purely whitespace, zero semantic diffs (spot
  checked the diff output before applying). Ran `terraform fmt -recursive` (no `-check`) to fix,
  re-ran `-check` to confirm clean (exit 0). Re-ran `fmt -check` once more after the provider-pin
  edits (which touched 3 of the same files) to confirm those hand-edits didn't reintroduce drift
  — still clean.
- **Item 3 — `dynamodb`'s 4 `hash_key`/`range_key` deprecation warnings (flagged Task 29): decided
  document, not fix — this one didn't need to be asked (no version bump, no design tradeoff, just
  an implementation-style choice), so decided directly per the user's "decide fix vs document,
  flag which" instruction.** Reasoning: migrating to `key_schema` changes the resource's
  attribute shape beyond a same-values reformat (unlike every other fix this phase), and would be
  the first Phase 6 change to genuinely diverge from the plan's snippet rather than just correct
  its HCL syntax — consistent with the standing "don't diverge from the plan's literal snippets
  over non-blocking findings" precedent already applied to the `fmt`-only quirks in Tasks 27/28.
  No live `dynamodb` table has ever been applied from this config (Tasks 29–31 are all
  validate-only), so there's no risk of the warning masking a real behavioral issue today either.
  Documented here and in `terraform/README.md`'s provider-versions note is *not* where this
  lives — it's `hash_key`/`range_key` argument-level, not provider-version-level, so recorded
  only in this log entry as the authoritative "decided, not forgotten" record.
- **Item 4 — the `terraform_remote_state` doc/code mismatch (flagged Task 30): asked before
  deciding, per standing convention (explicitly framed as a real design tradeoff, not a
  syntax fix).** User chose to update the docs to match the code (hardcoded role-name literal),
  not wire up `terraform_remote_state` for real. **Per this project's established convention of
  never editing `plan.md`'s historical task text** (deviations get recorded in this log instead;
  `design.md` is the living technical reference that does get corrected, e.g. §5.2's GitHub
  tool-name table in Phase 1) — updated `docs/2026-07-30-testscope-ai-design.md` §9's IAM bullet
  instead of touching `plan.md`'s Task 30 Interfaces text. New sentence explains the hardcoded
  name is deliberate (keeps `dev`/`prod` decoupled from `shared`'s state file, at the cost of the
  role name being a convention rather than something Terraform enforces structurally) and notes
  the tradeoff explicitly for anyone revisiting this later. `data
  "terraform_remote_state" "shared"` stays declared-but-unused in `dev`/`prod`'s `main.tf` —
  removing it wasn't part of either option the user was offered, and it's harmless as-is.
- **Full validation pass (Step 2), all three roots, run twice (once before the two decisions'
  code changes, once after, to confirm neither introduced a regression):**
  `terraform init -backend=false && terraform validate` for `shared`, `dev`, `prod` — all
  `Success!` both times. `dev`/`prod` still carry the same 4 non-blocking `dynamodb` deprecation
  warnings (Item 3, deliberately not fixed); `shared` and `monitoring` clean with zero warnings.
  **`shared`'s real `terraform.tfstate` (the live, currently-`running` cluster from Task 28)
  confirmed untouched throughout** — `-backend=false` and deleting `.terraform`/
  `.terraform.lock.hcl` only affect provider-plugin caching/lock metadata, never the state file
  itself; verified via `terraform state list` still showing all 15 real resources before and
  after.
- **`terraform/README.md` written** — the plan's own apply-order text (Step 3), plus three
  sections the plan's literal snippet doesn't have, added because writing the apply order
  without them would be actively misleading given what Tasks 28-31 actually found: (1) **Known
  account-specific constraints** — `DenyLargeInstanceTypes`/`LimitVolumeSize` and their resulting
  `t3.medium`/30GB defaults, and the `aws-learning-budget-keeper-function` Lambda's 13:00/21:00
  UTC daily auto-stop schedule, including the "stopped instances don't self-heal, cloud-init
  won't re-run" operational gotcha from Task 28's second apply attempt; (2) **Provider versions**
  — records the `~> 6.58` pin decided in this task; (3) **`dev`/`prod` and `shared`'s state —
  intentionally decoupled** — records Item 4's decision and reasoning inline, not just in this
  log, since README.md is what someone actually running `apply` will read first.
- **Environment note, informational only:** each `terraform init -backend=false` invocation in
  this sandboxed environment took noticeably longer than expected even with
  `CHECKPOINT_DISABLE=1` and a warm plugin cache (several ran past the 90s foreground limit and
  moved to background) — consistent with Task 29's finding that this network is just slow for
  Terraform's registry/provider-download calls generally, not a new or different issue.
- No credential/secret handling. No AWS resources created, modified, or destroyed by this task
  itself — `shared`'s live cluster (still `running` as of this task, confirmed via
  `aws ec2 describe-instances`) is untouched, not because of anything this task did, but because
  this task never runs `apply`/`destroy` at all.

**Phase 6 closing summary — everything still open before Phase 7 planning starts:**

- **Live, billing AWS resources right now:** `environments/shared`'s cluster — control-plane
  `i-0887a982c0501958c`, worker `i-0606ccf79b1c0c1af`, both `running` as of this task
  (2026-08-10, ~07:30 UTC). Will auto-stop at 13:00 UTC (16:00 Jerusalem) via the account's
  `aws-learning-budget-keeper-function` if still running then — see `terraform/README.md`'s new
  "Known account-specific constraints" section for the full detail on that Lambda and the two
  IAM guardrails (`DenyLargeInstanceTypes`, `LimitVolumeSize`). No `dev`/`prod`/`monitoring`
  resources have ever been applied — those modules are validated-only, zero AWS spend from them.
- **KNOWN FOLLOW-UP TASK, still explicitly unscheduled to any phase (re-confirmed, not
  resolved, during this phase's pre-work):** the GitHub-auth gap (`mcp-github`'s HTTP mode
  requires a per-request `Authorization: Bearer` header; `GITHUB_PERSONAL_ACCESS_TOKEN` env var
  alone doesn't satisfy it, empirically re-verified before Task 27). Phase 6 had no GitHub/MCP
  scope at all (confirmed), and Phase 7's Task 33 (`mcp-github` K8s manifests) as currently
  written only sets a container-level env var, which does **not** close this gap either — see
  the Open Questions entry below. Worth raising explicitly when Phase 7 planning reaches Task 33.
- **Still unfixed, unrelated to Terraform, no change this phase:** the `app`/`app` Python
  package-name import collision (Task 18, Phase 4) — backend-only, doesn't affect anything Phase
  6 touched. The `frontend/Dockerfile` `package-lock.json` gap (Task 26, Phase 5) — relevant once
  Phase 7/8 actually build that image for real deployment, not before.
- **Decided and closed this phase, not carrying forward:** `aws` provider now pinned (`~> 6.58`,
  all three roots). `dynamodb`'s `hash_key`/`range_key` deprecation warnings — deliberately
  documented, not fixed (Item 3 above); will keep appearing in every future `dynamodb`
  `validate`/`plan`/`apply` output in Tasks 32+ — expected, not a new regression each time it
  shows up again. `terraform_remote_state` doc/code mismatch — resolved via `design.md` §9
  correction; `dev`/`prod` are intentionally decoupled from `shared`'s state, not a gap.
- **Pattern worth carrying into Phase 7:** every Phase 6 task that copied plan.md's HCL verbatim
  hit the same single-line-block-with-`;`/`,`-separators bug (5 for 5 across Tasks 27–30):
  `terraform validate`/`init` catches it immediately and the fix is always mechanical
  (one argument per line, values unchanged) — expect it again if Phase 7/8's plan text contains
  similarly condensed HCL or YAML (Kubernetes manifests, GitHub Actions YAML), and verify
  empirically the same way rather than assuming a fix is needed or not needed.

### Phase 7 — Kubernetes Manifests (kubeadm cluster) — Tasks 32–35 ✅ complete

- Branch: `feature/phase-7-k8s-manifests`, cut from `main` after pushing and merging Phase 6's
  own branch first (it had never been pushed — see the Current State correction above), the only
  phase so far where local `main` didn't also need a separate fast-forward at session start.
- Pre-work (separate from Task 32 itself) answered five explicit applicability questions before
  any code was written: confirmed Task 33's plan text has no token-injection design at all (only
  a bare `GITHUB_PERSONAL_ACCESS_TOKEN` container env var); confirmed the `app`/`app` package
  collision (Task 18) doesn't apply to Phase 7 (pure YAML, no Python installs); confirmed Phase 7
  doesn't build/deploy any image for real (all validation is client-side `dry-run`/`kustomize`,
  no `docker build`, no live apply — that's Phase 8); flagged that the session had started in Auto
  Mode despite being asked to confirm manual mode, and treated the user's explicit instruction as
  overriding the default for the rest of the project; and verified the Task 28 cluster
  (`i-0887a982c0501958c` control-plane, `i-0606ccf79b1c0c1af` worker) live via `aws ec2
  describe-instances` rather than trusting the log — both still `running` at pre-work time.
- **Task 32 (base `api`/`worker` manifests) ✅**, implemented verbatim from plan.md, cross-checked
  against design.md §10's resource/probe requirements — no mismatch. **Real environment gap found
  running Step 4's literal validation command**, not a manifest bug: `kubectl apply
  --dry-run=client -k kubernetes/base` timed out trying to fetch OpenAPI schema from a stale
  control-plane IP (two different stale IPs across two kubeconfigs on this machine, neither
  matching the cluster's actual current public IP) — client-side dry-run in this kubectl version
  still needs live API discovery from a reachable server, which the plan's own "no live cluster
  required" framing doesn't hold. Confirmed unfixable from this machine by design, not just
  inconvenience: the cluster's port 6443 is intentionally security-group-restricted to
  internal-only (design.md §9) — the only legitimate way to run the literal command is from
  inside the VPC. Substituted `kubectl kustomize` (pure client-side render) + a YAML-parse check
  for the rest of the phase; deferred the live-cluster gap to Phase 8 rather than opening up
  network access to work around it. Committed as `fec3159`.
- **Task 33 (`mcp-test-analysis`/`mcp-github` manifests + GitHub-auth sidecar) ✅ — the most
  consequential task this phase.** The user made an explicit, pre-declared architectural decision
  (not decided by Claude): close the GitHub-auth gap with an `nginx` sidecar in the `mcp-github`
  pod that intercepts inbound traffic and injects `Authorization: Bearer <token>` (from the
  existing `github-token` Secret) before proxying to the real `github-mcp-server` container, moved
  to a `127.0.0.1`-only internal port. Gateway/ingress-level injection and an oauth2-proxy-style
  reverse proxy were both explicitly considered and rejected by the user (routing coupling,
  overkill for a single static PAT) before implementation started. `worker`/`api`/
  `mcp-test-analysis` all stay token-free — confirmed by reading `mcp-server/github_client.py`
  directly that `mcp-test-analysis` already sends its own valid bearer header on outbound calls to
  `mcp-github` (holds its own token per design.md §5.1), and that the sidecar's unconditional
  header injection is harmless/idempotent against that, not a conflict.
  - **Implementation choice, distinct from the architecture itself, flagged not defaulted:** the
    sidecar is `nginx:1.27-alpine` (the exact image/version already used in `frontend/Dockerfile`
    — no new dependency-version decision) using the official image's built-in envsubst-on-templates
    feature to inject the Secret-sourced token into the proxied request, rather than a custom-built
    image.
  - **Independent bug fixed in the same container, not part of the sidecar decision:** Task 33's
    own `mcp-github` manifest snippet had no `args`/`command` at all — the bare entrypoint starts
    an stdio server that exits immediately when run detached, the same class of bug Task 8 already
    found and fixed for local Docker verification (design.md §5.2). Fixed via
    `args: ["http", "--port", "8101", "--listen-host", "127.0.0.1"]`.
  - **New dependency addition surfaced and approved in this chat before being applied, per the
    user's explicit instruction not to decide dependency versions unilaterally:** `mcp-server`
    needed `fastapi`/`uvicorn` added for its new `/health/live`/`/health/ready` endpoints (plan's
    own Task 33 text). Recommended matching `backend/api`'s/`backend/worker`'s existing
    `fastapi>=0.115`/`uvicorn[standard]>=0.32` pins (no new version anywhere in the repo);
    user confirmed in-chat before it was added.
  - **Real, pre-existing packaging bug found and fixed while reinstalling — same class as Task
    10's `backend/shared` fix:** `mcp-server` had never been reinstalled since Phase 1, so its own
    flat-layout module-discovery ambiguity (5 top-level `.py` files, no `[tool.setuptools]`
    config) had never been triggered. Surfaced by adding the new dependency and running
    `pip install -e ".[dev]"` for the first time in this phase. Fixed identically to Task 10:
    `py-modules = ["aws", "github_client", "server", "sweeper", "workspace"]`.
  - **Test-only gap found via the mandatory RED-verification step:** `test_health.py` is the first
    test in this suite to import `server` directly at module scope — `server.py`'s module-level
    `GithubClient()` needs `MCP_GITHUB_URL`/`GITHUB_TOKEN` set *before* import, which
    `monkeypatch` (used everywhere else in this suite) can't do at collection time. Fixed with
    `os.environ.setdefault(...)` (placeholder value only) scoped to just this test file.
  - Full `mcp-server` suite after: 19/19 passing, 94–96% coverage depending on run (see the
    flakiness note below), zero new `ruff` findings after cleaning up two unnecessary `noqa`
    comments in the new test file. Repo-wide regression: `backend/worker` 38/38, `backend/api`
    16/16, `backend/shared` 12/12 — unaffected. Committed as `6ce8d1e`.
  - **Flakiness observed, not fixed in this task — fixed as its own follow-up before Task 34
    (see below):** the new health-server thread's extra imports measurably added to `mcp-server`'s
    real subprocess startup time; `test_mcp_integration.py`'s existing `sleep(8.0)` budget
    occasionally wasn't enough under full-suite+coverage runs (~2 failures in 5 runs), though the
    same test passed 5/5 in isolation. Not touched here since the "right" fix (sequencing vs.
    bumping the sleep vs. reducing import cost) was the user's call, not a mechanical one.
- **Task 33 follow-up fix (done first, before Task 34, per explicit instruction) ✅:** the health
  thread now polls (cheap TCP-connect loop, no `fastapi`/`uvicorn` work) until the main MCP
  transport is confirmed listening before calling `uvicorn.run(...)` — the costly part. `sleep(8.0)`
  itself and import cost both left untouched, exactly as instructed; the fix is pure sequencing.
  **Verified resolved, not just attempted: 6/6 clean full-suite+coverage runs afterward (0
  failures, vs. 2/5 before), runtime also dropped from 17–29s to 13–14s per run**, consistent with
  reduced startup contention rather than a coincidence. Committed separately as `cb4c75e` so it's
  distinguishable from Task 33's own work.
- **Task 34 (`frontend` manifests + `Ingress`) ✅**, implemented verbatim from plan.md — no
  plan-text deviations. **Real bug found by actually building and running the Dockerfile (not
  just written and trusted, matching Task 17/26 precedent):** `nginx`'s static
  `proxy_pass http://api:8000;` resolves that hostname once at config-load time and refuses to
  start at all if unresolvable then — confirmed directly, the container crash-looped in an
  isolated `docker run` with no `api` host present (`nginx: [emerg] host not found in upstream
  "api"`); re-verified clean with a fake `--add-host=api:127.0.0.1` entry (both `/` and a
  client-side SPA route returned `200` via the `try_files` fallback, config content matched
  exactly). **Not fixed** — in the real cluster this shouldn't bite under this project's
  apply-the-whole-`kustomize`-`base`-together pattern (the `api` Service DNS entry exists as soon
  as its Service object does, independent of pod readiness), but it is a real crash, not a
  graceful per-request failure, if `frontend`'s pod is ever scheduled before `api`'s Service
  object exists. The proper fix (`resolver` + variable-based `proxy_pass`, deferring DNS
  resolution to request time) is a new nginx pattern beyond this task's literal scope and needs a
  resolver-source decision — flagged for the user, not applied. Verification image/container
  removed after confirming. Committed as `9b203df`.
- **Task 35 (`dev`/`prod` kustomize overlays + `monitoring` namespace placeholder) ✅**,
  implemented verbatim from plan.md — no deviations, no new bugs found. `SQS_QUEUE_URL` is left
  as the plan's literal `PASTE_FROM_TERRAFORM_OUTPUT_queue_url` placeholder in both overlays
  (correctly, not a gap): `dev`/`prod` Terraform environments have never actually been applied
  (Phase 6 was validate-only by design), so no real queue URL exists anywhere to paste yet; the
  plan's own snippet already anticipates this by using concrete deterministic names for
  `DYNAMODB_TABLE`/`S3_BUCKET` (derivable from the env name alone) while leaving only the
  apply-dependent `SQS_QUEUE_URL` as a placeholder. Validated both overlays render correctly
  (14/14 resources each) and that patches actually take effect (`ENV`, table/bucket names,
  `Ingress` host, replica counts all inspected field-by-field, not just "did it parse").
  Committed as `c9a06ea`.

### Phase 7 health check (post-Task 35, pre-push) — ✅ run, one real finding, fixed

- **Repo-wide regression: all clean.** `backend/worker` 38/38, `backend/api` 16/16,
  `backend/shared` 12/12, `mcp-server` 19/19 (3/3 repeated clean runs with coverage, re-confirming
  the Task 33 follow-up fix still holds), `frontend` 9/9 (pre-existing React Router v7
  future-flag warnings only, unrelated to this phase).
- **Full manifest re-render, base + dev + prod together, patches re-verified not just
  re-parsed:** `kubectl kustomize` on all three (12/14/14 resources respectively), plus a
  targeted deep-check that Task 33's sidecar survives Task 35's namespace/patch machinery
  correctly — it does: both `mcp-github` containers, the `auth-proxy` ConfigMap volume mount, and
  the Service's port 8100 all render intact and correctly namespaced in both `dev` and `prod`
  (kustomize's namespace transformer doesn't touch cross-resource name references here, since no
  `configMapGenerator`/hash-suffixing is used anywhere in this tree). Also explicitly confirmed
  `ingressClassName: nginx` from base survives the `dev`/`prod` `ingress-patch.yaml` strategic
  merge in both overlays (a field a patch can silently drop if merge semantics are wrong — they
  aren't here).
- **Secrets sweep across the full phase (all 5 Task commits, 28 files): clean of any actual
  token/credential-shaped strings.** But found one real, substantive gap:
  `kubernetes/base/mcp-test-analysis/secret.yaml.example`'s own comment claims a copied
  `secret.yaml` is gitignored — it wasn't; no `.gitignore` pattern actually covered it, confirmed
  via `git check-ignore` returning nothing for that path. If the documented copy-and-fill-in
  workflow were followed literally, a real GitHub PAT would have been committable. **Fixed as its
  own follow-up (see below), not silently patched in the health check itself** — flagged to the
  user first.
- **Cross-task consistency: coheres correctly overall, one known tension restated (not new).**
  Every consumer of the GitHub token — `mcp-test-analysis`'s container, `mcp-github`'s real
  container, and the `auth-proxy` sidecar — references the same `secretKeyRef: {name:
  github-token, key: token}`. Since Secrets are namespace-scoped by name, this means only *one*
  underlying Secret object can exist per namespace, shared by all three, not "their own" instance
  as design.md §5.1's language implies — already flagged during Task 33, restated here since
  Task 35 doesn't resolve it either (no Secret object is created anywhere in this repo yet, only
  the `.example` template — applying `dev`/`prod` as-is today would leave every pod needing this
  Secret unable to start until someone creates it manually per namespace, which is expected/
  intentional, just worth stating plainly as a Phase 8 precondition).
- **Verdict: Phase 7 is sound.** No regressions, manifests structurally correct and consistent
  end-to-end, no accidental secrets committed. The one real finding (`.gitignore` gap) was fixed
  as an explicit, scoped follow-up, described next.

### `.gitignore` fix (post-health-check, pre-push) — ✅ complete

- Added `kubernetes/**/secret.yaml`. **Verified both directions, not just pattern-matched:**
  copied `secret.yaml.example` to a real `secret.yaml`, confirmed `git check-ignore -v` matches it
  and `git status` does *not* list it as untracked, then confirmed `secret.yaml.example` itself is
  still *not* ignored (stays tracked) — removed the temporary copy afterward. Also confirmed the
  glob covers any depth/service dir (`dev`, `prod`, `mcp-github`, etc.), not just the one path
  that prompted the fix.
- **Repo-wide sweep for the same convention gap, as explicitly asked, found nothing else.** The
  `secret.yaml.example` file is the only `*.example` in the entire repo (`git ls-files` +
  filesystem `find` agree). Broadened the search past filenames to a text grep for "copy to" /
  "gitignored" / "never commit" / "REPLACE_WITH"-style comments across `.yaml`/`.yml`/`.tf`/
  `.md`/`.tpl`/`.example` files: the only other "copy and fill in, expect gitignored" case in the
  repo is Terraform's generated SSH private key
  (`terraform/environments/shared/testscope-k8s-keypair.pem`) — checked against the real file,
  which exists on disk right now (the live Phase 6 cluster's key), and confirmed it's already
  correctly covered by the pre-existing `*.pem` rule and not tracked in git. `terraform/modules/
  ec2/*.tpl` files are Terraform `templatefile()` inputs rendered by Terraform itself, a different
  pattern entirely, not a gap. Committed as `92f30b5`.

---

### Phase 8 — CI/CD (GitHub Actions) — Tasks 36–38 ✅ complete

- Branch: `feature/phase-8-cicd`, cut from `main` after confirming PR #16 (Phase 7 code) and
  PR #17 (Phase 7 docs) merged (see Current State's session-start correction above — local `main`
  was 9 commits behind). Pre-work also confirmed which of the six standing open items applied to
  this phase's scope: the live-cluster dry-run gap (directly in scope — this is where `deploy-dev`/
  `deploy-prod` finally reach a live cluster for the first time), the `github-token` Secret
  convention gap (in scope as a precondition), the missing mcp-github/sidecar probes (not fixed,
  but flagged as weakening `kubectl wait --for=condition=available`'s signal in the smoke test),
  the frontend Dockerfile lockfile gap (in scope — Task 36 builds this exact image), the nginx
  `proxy_pass` static-resolution risk (not this phase's to fix, but exercised for the first time
  by a real `kubectl apply`), and the `app`/`app` package collision (confirmed not applicable —
  Task 36's matrix installs one service per isolated job).
- **Task 36 (`pr.yml`) ✅ — by far the most consequential task this phase: three separate CI gates
  (`ruff check .`, `npx eslint src`, Trivy image scan) all failed immediately against the current,
  already-merged repo state when actually run, not just written from the plan's snippet.** Every
  one was diagnosed empirically (`ruff check . --statistics`, `npx eslint src` run directly,
  `docker build` + a real local `trivy image` scan) before deciding how to handle it, per this
  project's standing "run it for real" discipline.
  - **`ruff check .` failed in all 4 services** (10–36 pre-existing findings each: `I001`,
    `UP017`, `BLE001`, `SIM117`, `F401`, `S110`, `TRY002`, `UP035`, `UP041`, `ASYNC220`,
    `ASYNC251`, `F841`, `N999`) — every one previously reviewed phase-by-phase and left in place
    as "verbatim from plan.md." Offered a blanket-ignore-list option matching that precedent
    (new standing decision above); **the user chose to fix everything instead, zero ignores.**
    Fixed for real, not suppressed:
    - Auto-fixable categories (`I001`, `UP017`, `UP035`, `UP041`, most `F401`) via
      `ruff check --fix`.
    - **`BLE001`** (8 sites, all in `backend/worker`): added `logger.exception(...)` calls to
      `runner.py`'s two flagged sites and five sibling node files (`report_saver`,
      `request_validator`, `requirement_retriever` ×2, `test_file_classifier`,
      `test_file_retriever`) that had the identical "broad except, no logging" gap `runner.py`
      itself was already fixed for in the Phase 3 health check — this rule specifically exempts
      `except Exception:` blocks that call `logging.exception(...)`, so applying that
      already-established pattern to its five untouched siblings is a genuine fix, confirmed by
      re-running `ruff check` clean afterward, not a suppression.
    - **`S110`** (`runner.py`'s best-effort cleanup `except: pass`): changed to
      `logger.warning(..., exc_info=True)` — still non-fatal, just no longer silent.
    - **`SIM117`** (6 sites across `backend/api/app/mcp_client.py`, `backend/worker/app/
      mcp_clients.py`, `mcp-server/github_client.py`, and 3 test files): merged nested
      `with`/`async with` blocks into single parenthesized multi-context managers (Python
      3.10+ syntax, safe given every Dockerfile's `python:3.11-slim` base).
    - **`TRY002`** (a test helper raising bare `Exception`): changed to `RuntimeError` — the
      retry-classification logic under test (`_is_retryable_tool_error`) is purely string-based,
      confirmed this doesn't change test semantics.
    - **`N999`** (`mcp-server/__init__.py` — invalid module name for the hyphenated directory):
      deleted. Confirmed via grep it was never imported anywhere and isn't part of the
      `py-modules` flat-layout config Task 33 already established.
    - **`ASYNC220`/`ASYNC251`/`F841`** (`mcp-server/tests/test_mcp_integration.py` — the
      real-subprocess integration test with a documented flakiness history, Task 33's follow-up
      fix): converted `subprocess.Popen`/`time.sleep` to `asyncio.create_subprocess_exec`/
      `asyncio.sleep`, dropped an unused `clone_url` binding. Given this file's history, ran it
      3x alone and 3x as part of the full coverage suite afterward — stable every time, same
      ~9s runtime, no regression.
    - Full regression after all fixes: **85/85 tests passing** across all 4 services (12+16+38+19),
      coverage unchanged (100%/100%/94%/94%).
  - **`npx eslint src` couldn't run at all** — no `eslint` devDependency, no config file anywhere
    in the repo. New dependencies surfaced and approved in-chat before being applied:
    `eslint@^10.8`, `typescript-eslint@^8.66`, `eslint-plugin-react-hooks@^7.1`,
    `eslint-plugin-react-refresh@^0.5`, `@eslint/js@^10.0`, `globals@^17.9` — plus a minimal flat
    `eslint.config.js` (recommended rulesets, non-type-aware, no `parserOptions.project`).
    Running it for real found 5 genuine `no-explicit-any` violations (2 in `client.test.ts`'s
    `(fetch as any).mockResolvedValue`, 3 in `Results.tsx`'s untyped `.map()` callbacks) — fixed
    with `vi.mocked(fetch)` and narrow inline types (`CoverageRow`/`MissingTestRow`/`ToolCallRow`)
    matching exactly the fields already rendered, not new fields. `npm audit` confirmed zero new
    findings from any of the 6 new packages.
  - **`npm test -- --coverage` had no coverage provider installed** — `@vitest/coverage-v8@^2.1.9`
    (version-locked to the installed `vitest@2.1.9`) surfaced and approved in-chat. Its one new
    `npm audit` entry traces entirely to the already-accepted `vitest` chain (`via: ['vitest']`),
    confirmed via `npm audit --json`, not a new vulnerability.
  - **Trivy scan (`severity: CRITICAL,HIGH`, `exit-code: "1"`, as plan.md's own literal snippet)
    failed all 4 images on the first real local run** — `api` 25, `worker` 25,
    `mcp-test-analysis` 53, `frontend` 35 CRITICAL+HIGH findings, all in base-image OS packages,
    not this project's code. Resolved in two rounds, both with the user's explicit direction
    rather than a default pick:
    1. First split the single scan step into two — `severity: CRITICAL` blocking
       (`exit-code: "1"`, no `continue-on-error`) and `severity: HIGH` non-blocking
       (`exit-code: "0"` + `continue-on-error: true` as a defensive second layer).
    2. Re-scanning with just that split still failed all 4 images on CRITICAL alone (`api`/
       `worker`/`mcp-test-analysis` share 4 CRITICAL CVEs from `python:3.11-slim`'s bundled Perl
       packages; `frontend` had 1, `libcrypto3`/OpenSSL, from `nginx:1.27-alpine`). **Checked
       each CVE's real `Status`/`FixedVersion` field via `trivy image --format json`, not
       recalled table output, before treating them as equivalent** — confirmed all 4 Perl CVEs
       (`CVE-2026-13221`, `CVE-2026-42496`, `CVE-2026-57433`, `CVE-2026-8376`) report
       `FixedVersion: null` (`Status: affected`/`fix_deferred` — no patch exists to install),
       while frontend's `CVE-2026-31789` reports `FixedVersion: 3.3.7-r0`, `Status: fixed` — a
       real fix exists. Added `ignore-unfixed: true` to both Trivy steps (new standing decision
       above) rather than either leaving CRITICAL fully blocking (would permanently fail on CVEs
       nobody can act on) or fully non-blocking (would hide the frontend one, which *is*
       actionable). Rebuilt all 4 images fresh and re-scanned with the exact new settings:
       `api`/`worker`/`mcp-test-analysis` **PASS** (0 findings), `frontend` **FAIL** (still
       exactly `CVE-2026-31789`, confirmed nothing else slipped through).
  - **`frontend/Dockerfile`'s `nginx:1.27-alpine` → `nginx:1.30-alpine` base image bump** —
    approved in-chat after confirming (not assumed): the current pin is genuinely the latest
    image Docker Hub publishes under that tag (force-repulled, "up to date"), because nginx's
    `1.27` line no longer receives base-image updates; `nginx:1.30-alpine` (nginx's current
    "stable" line, same `<major.minor>-alpine` floating-tag convention, still Alpine-based) was
    confirmed via a direct `trivy image` scan of the base image itself to have zero CRITICAL/HIGH
    findings and to specifically lack `CVE-2026-31789`. After the bump: rebuilt `frontend`
    fresh (`--no-cache`), re-ran the exact `pr.yml` Trivy settings against the real built image —
    **0 vulnerabilities, PASS.** Live-verified with real containers (a built `frontend` image
    plus a fake `api` upstream on a docker network) that routing/serving is unchanged on the new
    base: `Server: nginx/1.30.4` header confirms the new version is actually running; `/` → 200,
    an unknown SPA route → 200 via `try_files`, `/api/health/live` → correctly proxies stripped
    to `/health/live`, `/api/analyses` → still passes through unchanged.
  - **Independent, cross-cutting bug found and fixed: `frontend/nginx.conf` had no way to reach
    `api`'s real health-check routes at all**, discovered while cross-checking Task 37/38's
    smoke-test target (`http://$HOST/api/health/live`) against design.md §7 and the actual
    `backend/api` route table. `api`'s health routes are mounted bare (`/health/live`,
    `/health/ready` — no `/api` prefix, confirmed against `app/main.py` and design.md §7), but
    the existing `location /api/ { proxy_pass http://api:8000; }` (no trailing slash) forwards
    the request URI **unchanged** — correct for `/api/analyses` (which already includes `/api`
    in its own FastAPI route), but it means `/api/health/live` would have reached `api` as the
    literal path `/api/health/live`, which doesn't exist. Fixed with a more specific
    `location /api/health/ { proxy_pass http://api:8000/health/; }` block that strips the prefix
    just for health paths. Verified with live Docker containers before and after: `/api/analyses`
    still passes through unchanged (not broken by the fix), `/api/health/live`/`/api/health/ready`
    now correctly reach `api`'s real routes, `/` still serves the SPA. This fix benefits both
    `deploy-dev.yml` and `deploy-prod.yml`'s smoke tests, not just Task 36.
- **Task 37 (`deploy-dev.yml` + `kubernetes/dev/smoke-test.sh`) ✅ — one real, confirmed bug in
  plan.md's own literal snippet.** The per-image tag-update loop re-ran `kubectl kustomize .`
  fresh on every iteration and overwrote `/tmp/rendered.yaml` each time, so only the **last**
  image in the loop (`frontend`) ever actually got retagged in what got applied — confirmed
  empirically by running the literal loop against the real `kubernetes/dev` tree before touching
  anything (`api`/`worker`/`mcp-test-analysis` stayed on the literal `:latest` placeholder).
  Fixed by rendering once and chaining all four `sed` substitutions in a single pass; re-verified
  against the real tree that all four images now retag correctly and the two third-party images
  (`github-mcp-server`, the `nginx` sidecar) are correctly left untouched. `smoke-test.sh` itself
  matches the plan verbatim, no bugs found — it depends on the nginx health-proxy fix above to
  actually pass.
- **Task 38 (`deploy-prod.yml` + `kubernetes/prod/smoke-test.sh` + `.github/workflows/README.md`)
  ✅** — same sed-loop fix applied and re-verified against the real `kubernetes/prod` tree
  (tag-triggered variant using `github.ref_name`). No new bugs found; `smoke-test.sh` is the
  plan's literal prod-defaults copy of `dev`'s.
- **Manual infrastructure preconditions — explicitly not attempted, per the user's instruction to
  stop before anything outside Claude's control.** Documented in `.github/workflows/README.md`
  and restated as explicit Open Questions entries below (not left only in a workflow comment):
  self-hosted runner registration (`testscope-k8s` label) + the `/etc/hosts` entry on the
  control-plane node; the `github-token` Secret in `dev`/`prod` (already a known gap per Phase 7's
  health check); and a **newly-found gap, not previously flagged anywhere**: `worker`'s Deployment
  references a `worker-secrets` Secret (`anthropic-api-key` key) that has **no example file at
  all** in the repo, unlike `github-token`'s `.example` — confirmed via a repo-wide search. The
  `production` GitHub Environment + required reviewer (Task 38's own precondition) is likewise
  untouched.
- **Full regression, re-run repeatedly across this phase's several rounds of changes, stable every
  time:** `ruff check .` clean in all 4 services; 85/85 Python tests passing (12+16+38+19,
  coverage unchanged); frontend `eslint` clean, 9/9 tests, `npm run build` green; all 3 kustomize
  trees (`base`/`dev`/`prod`) still render; all 3 workflow files parse as YAML and pass
  `actionlint` clean (its only output is the expected, harmless "unknown label `testscope-k8s`"
  notice on the two deploy workflows — there's nothing to register it against yet). `actionlint`
  itself caught one real mistake mid-session (a duplicated `exit-code` key left over from an
  in-place edit) before it reached this log — fixed immediately, re-verified clean.
- **Verdict: Phase 8 is sound and ready to merge from a code-correctness standpoint.** Nothing
  about the CI/CD *code* is known to be broken; what remains is entirely the manual infrastructure
  setup above, which no amount of further workflow-file changes can substitute for. Recommend
  merging as-is and treating the two manual-precondition items as this phase's genuine, tracked
  completion gate — see Open Questions below — rather than assuming "pushed" means "runnable."

---

### Phase 9 — Observability (Prometheus/Grafana/Loki/Promtail + CloudWatch) — Tasks 39–42 ✅ complete

- Branch: `feature/phase-9-observability`, cut from `main` after confirming PR #18 (Phase 8)
  merged (local `main` was 4 commits behind — see Current State's session-start correction above).
- **Pre-work (before Task 39):** read plan.md/design.md in full, produced a Tasks 39–42 breakdown
  table, and ran an explicit open-items applicability check against every standing open item from
  prior phases. Findings: the `app`/`app` package collision (Task 18) and frontend Dockerfile
  lockfile gap (Task 26) don't apply to this phase's scope; the nginx `proxy_pass` risk (Task 34)
  is unaffected (Phase 9 never touches `frontend`); the missing mcp-github/auth-proxy probes
  matter for the first time here, since Task 40's scrape config would otherwise try to reach that
  pod too; and Task 40/42's own live-verification steps need real cluster/AWS access this dev
  machine doesn't have — flagged upfront rather than discovered mid-task.
- **Task 39 (instrument `api`/`worker`/both MCP servers with `prometheus_client`) ✅.** New
  `backend/shared/metrics.py` (7 Counter/Histogram primitives, verbatim per plan.md) and
  `mcp-server/mcp_metrics.py` (mcp-server's own local copy — it has no dependency on
  `backend/shared`). `/metrics` mounted on `api` (`app.mount` + middleware), `worker` (see
  `app/health.py` deviation below), and `mcp-server`'s health app.
  - **New dependency (`prometheus-client>=0.21`, matching plan.md's own pin) — surfaced via
    AskUserQuestion, approved.** Later corrected as a process matter, not a technical one: the
    user pointed out (after Task 39 shipped) that this project's standing rule — "architectural/
    dependency decisions must be surfaced and answered in the chat itself, not resolved via a
    tool-mediated prompt" (established Phase 7, re-broken here) — means an AskUserQuestion answer
    doesn't count as a chat exchange, and the Task 39 report was wrong to describe it as
    "confirmed with you first." The dependency itself was retroactively approved in plain text;
    the *process* gap (third occurrence, after Phase 6/Task 33 and Phase 8's Trivy gate) is now
    also saved as a standing Claude-memory entry so it doesn't recur in future sessions.
  - **Real, confirmed self-inflicted bug, found and fixed before commit:** `mcp-server`'s local
    metrics module was first named `metrics.py`, colliding with `backend/shared/metrics.py` — both
    are flat `py-modules` installed into the same shared `.venv`, so `from metrics import ...` in
    `api`/`worker` silently resolved to whichever finder won `sys.meta_path` order (mcp-server's),
    breaking every `API_REQUEST_COUNT`/`ANALYSIS_COUNT`/etc. import with a real `ImportError` —
    same class of bug as Task 18's `app`/`app` collision, except not RED-verification-transient
    this time: with both modules genuinely present, it always resolved wrong. This is exactly the
    failure mode the user asked to be sanity-checked for (though the `app`/`app` collision itself
    didn't reproduce — `app.main` already existed in both services). Renamed to `mcp_metrics.py`;
    re-verified all 4 services' suites together in one venv session afterward (the only way to
    actually prove a naming collision is gone).
  - **Deviation, plan-snippet staleness (same class as Task 11's, not verbatim):**
    `worker/app/mcp_clients.py`'s Task 39 snippet reimplements the whole transport call around
    the pre-Task-11 `result.structured_content` pattern (already established `None` for these
    servers, design.md §5.2) instead of instrumenting the real `_call_once`/`with_retry`
    structure. Instrumented the real `_call` wrapper instead — one count/latency sample per
    logical tool call (post-retry), not per individual transport attempt.
  - **Deviation, necessary refactor:** extracted `build_health_app()` from
    `worker/app/health.py`'s `start_health_server()` (mirroring `mcp-server/server.py`'s existing
    split) so `/metrics` (and the health app itself) is testable via `TestClient` without starting
    a real uvicorn thread — Task 17 had left this bundled and deliberately untested for exactly
    that reason; Task 39's own test-file requirement forced the split.
  - No literal snippet given for `mcp-server`'s per-tool instrumentation — designed a small
    `instrument_tool()` decorator (sync+async, `functools.wraps`) from the plan's textual
    description; verified against the real MCP transport (`test_mcp_integration.py`, a real
    subprocess + real `ClientSession`) that `MCPServer`'s tool-schema introspection still works
    through `__wrapped__` — not just assumed from `inspect.signature`'s documented behavior.
  - Coverage-closing tests added beyond the plan's literal `Test:` file list (matching the
    established Tasks 1/11 precedent): `backend/shared/tests/test_metrics.py`,
    `mcp-server/tests/test_metrics.py` — the latter also closed a real isolation gap (running it
    alone, not as part of the full suite, `KeyError: 'MCP_GITHUB_URL'` without its own
    independent `os.environ.setdefault(...)` guard, mirroring but not relying on `test_health.py`'s
    own collection-order-dependent version of the same fix).
  - Regression after Task 39: `shared` 13/13 (100%), `api` 17/17 (100%), `worker` 43/43 (96%),
    `mcp-server` 26/26 (95%) — all run together in one venv session. `ruff` clean, all 4 services.
- **`ANALYSIS_COUNT` follow-up fix (user-requested, before Task 40) ✅ — real bug found during
  Task 39's own review, fixed as its own commit.** Task 39's literal placement
  (`report_saver.py`, right before `return state`) meant `state["status"]` was always
  `"completed"` at that point — `report_saver` only ever runs once every upstream node has
  already succeeded (early failures route straight to `END` via their own conditional edges,
  Task 17) — so the `status="failed"` label could never fire, even though Task 41's dashboard has
  a panel keyed on exactly that distinction. **Fix:** moved the increment to `runner.py`'s
  `finally` block, the one place every terminal outcome (completed, or failed from an early node/
  graph exception/timeout) passes through — reads the same `state.get("status", "failed")` the
  `AnalysisRecord` write already uses, so the metric and the persisted record can't disagree.
  **Sanity-checked per this project's standing practice, not just asserted:** temporarily removed
  the new `runner.py` increment and reran the two new tests — both failed exactly as expected
  (`0.0 == 1.0`), confirming they actually catch the regression; restored afterward. Regression:
  `worker` 44/44 (96%, `report_saver.py` 100%), others unaffected.
- **Task 40 (deploy Prometheus with RBAC + Grafana with provisioning + Loki + Promtail) ✅.**
  `kubernetes/monitoring/{rbac,prometheus,grafana,grafana-datasources,grafana-dashboard-provider,
  loki,promtail}.yaml` per plan.md, plus a `kustomization.yaml` (not in the plan's literal file
  list) so the tree renders/validates locally via `kubectl kustomize` — same substitute for
  live-cluster dry-run Phase 7/8 already established (port 6443 is still internal-only from this
  dev machine).
  - **Real, structural bug #1, found and fixed (verifiable from the YAML alone, no live cluster
    needed):** `mcp-test-analysis` declares two container ports (8100 MCP transport, 8101 health/
    metrics); Prometheus's `kubernetes_sd_configs` (role: pod) defaults `__address__` to the
    pod's *first* declared port when no override exists, and the plan's own scrape-config snippet
    has no such override — it would have scraped the MCP transport port and never reached
    `/metrics` at all. **Fixed** with the standard Prometheus annotation-based port-override
    convention: `prometheus.io/scrape`/`prometheus.io/port` pod-template annotations added to
    `api` (8000), `worker` (8080), and `mcp-test-analysis` (8101 — the one that actually differs
    from the default), plus a `relabel_configs` rule honoring the annotation with a fallback to
    default behavior (only affects `mcp-github`, an already-flagged pre-existing gap — the
    official third-party image has no `/metrics` endpoint on any port).
  - **Real, structural bug #2, found and fixed:** `promtail.yaml`'s plan snippet passes
    `-config.file=/etc/promtail/config.yml` as a container arg but defines no ConfigMap or
    volumeMount providing that file anywhere — Promtail's `-config.file` flag is mandatory, so
    the container as originally specified would fail to start. Added a `promtail-config`
    ConfigMap (minimal `server`/`positions`/`clients`/`scrape_configs`, scraping the same
    `/var/log/pods` hostPath already mounted) and the matching volumeMount.
  - Validated: `kubectl kustomize kubernetes/monitoring` renders all 15 resources cleanly; every
    ConfigMap's embedded YAML parses as well-formed. Re-validated `base`/`dev`/`prod` after the
    annotation additions (12/14/14 resources, unchanged counts) — annotations survive the
    namespace transform and existing replica-count patches correctly.
  - **Step 3's live verification (`kubectl apply` + curl-checking Prometheus targets/Grafana
    datasources against `dev`) explicitly NOT done** — same live-cluster access gap as every
    prior phase, flagged as pending rather than skipped silently or asserted to work.
- **Task 41 (Grafana "TestScope AI — System Health" dashboard) ✅.**
  `kubernetes/monitoring/dashboard-configmap.yaml`, mounted directly into Grafana (no
  `grafana_dashboard` sidecar-label convention — Task 40 doesn't run that sidecar), all 7 panels
  per plan.md.
  - **Cross-checked every panel's metric/label references programmatically against
    `backend/shared/metrics.py`/`mcp-server/mcp_metrics.py`, not assumed** — a small script
    extracted every `testscope_*`/`kube_*` identifier from the panel queries and diffed against
    every declared `Counter`/`Histogram` name and its label set. All `testscope_*` references and
    their `by (status)`/`by (tool)`/`by (le, tool)` groupings check out exactly; the literal
    `status="error"` string in the MCP Tool Errors panel matches both instrumentation sites
    (`worker/app/mcp_clients.py` and `mcp-server/mcp_metrics.py`) exactly. The
    Analysis Success/Fail Rate panel now has real data behind both labels thanks to the
    `ANALYSIS_COUNT` fix above — before that, `status="failed"` could never have appeared.
  - **Two gaps found and flagged, not fixed (out of scope for a dashboard-authoring task):**
    "Pod Restarts" references `kube_pod_container_status_restarts_total`, a kube-state-metrics
    metric — kube-state-metrics is not deployed anywhere in this project (not in Task 40, not in
    design.md's stated stack, and Task 40's own scrape config wouldn't discover it even if
    deployed, since it only keeps pods matching the `app` label regex). "Recent Failed Analyses
    (logs)" filters on the literal substring `"status=failed"`, but grepping every
    `logger.exception`/`logger.warning` call across `backend/`/`mcp-server/` confirms no task
    through Task 41 ever implemented the structured JSON logging design.md §12 calls for — every
    log line today is a plain formatted string with no such substring. Both panels will read
    "No data" until their respective missing pieces exist; kept the plan's literal query text
    rather than unilaterally substituting something that happens to match today's output.
  - **Also noted, not actioned:** `testscope_llm_calls_total` (`LLM_CALL_COUNT`) is declared in
    `metrics.py` but never incremented anywhere — Task 39 never wired it into `llm_client.py`, and
    no Task 41 panel references it either.
  - Validated: ConfigMap YAML parses; embedded dashboard JSON parses (plan's own Task 41 Step 2
    command); full `kubernetes/monitoring` kustomization renders 16 resources with Grafana's
    `testscope-dashboard` volume reference now resolved. Live rendering in an actual Grafana
    instance not confirmed — same live-cluster gap as Tasks 40/42.
- **Task 42 (verify CloudWatch alarms end-to-end) ✅ — the first genuinely live-AWS verification
  task in the whole project, run for real, not simulated.**
  - **Pre-work found `dlq_url` missing, as anticipated, plus a real bug in the plan's own
    snippet:** plan.md's literal `output "dlq_url" { value = module.sqs.dlq_arn }` is wrong — the
    `sqs` module never exposed a `dlq_url` output at all (only `dlq_arn`), and Task 42's own Step
    1 command feeds this value into `aws sqs send-message --queue-url`, which requires an actual
    queue URL, not an ARN (different formats — confirmed structurally, not via a failed live
    call). **Fixed:** added a real `dlq_url` output to `terraform/modules/sqs/outputs.tf`
    (`aws_sqs_queue.dlq.id`, same pattern `queue_url` already uses), referenced from both
    `environments/{dev,prod}/main.tf`. `terraform validate`/`fmt -check` clean.
  - **Bigger pre-work finding, verified two independent ways rather than trusted from this log's
    own prior "validate-only" claim:** neither `dev` nor `prod` had ever been `apply`'d. No local
    `terraform.tfstate` existed for either (both use Terraform's implicit local-only backend, no
    remote state configured — confirmed via `backend.tf`'s own comment), and a live
    `aws sqs list-queues`/`aws cloudwatch describe-alarms` against the real account
    (`228281126655`, `us-east-1`) both returned completely empty. **Stopped and asked the user
    before proceeding**, per their own explicit instruction and this project's standing "hard-to-
    reverse action" discipline — creating real AWS infrastructure was well beyond what "verify
    already-provisioned resources" authorized. The user applied `dev` themselves and confirmed
    the SNS email subscription before the live verification ran.
  - **Live verification, all 4 steps, real observed results (not assumed):**
    1. Pushed a test message to the DLQ (`12:59:35Z` UTC) — confirmed 1 message visible.
    2. Alarm `testscope-dev-dlq-not-empty` transitioned `INSUFFICIENT_DATA` → `ALARM` at
       `13:02:37Z` (~3 min later), `StateReason: "Threshold Crossed: 1 datapoint [1.0] was
       greater than the threshold (0.0)"`. CloudWatch's own alarm history (not just the alarm
       state) confirmed the SNS publish action itself `"actionState":"Succeeded"`, with the full
       alarm email body embedded in the record. **User independently confirmed the email actually
       arrived in their inbox** — asked explicitly rather than assumed from the publish-succeeded
       evidence alone, since inbox delivery isn't something this session can observe directly.
    3. Purged the DLQ (`13:03:44Z`) — confirmed queue depth dropped to 0.
    4. Alarm cleared `ALARM` → `OK` at `13:10:37Z` (~7 min later, consistent with SQS's ~5min
       metric period + evaluation delay), `StateReason: "... 0.0 ... was not greater than the
       threshold"`.
  - **Noted, not a defect:** the alarm's `OKActions` is empty (confirmed in both the baseline and
    final `describe-alarms` output) — only the `ALARM` transition sends an email, not the `OK`
    transition. That's how Task 30's monitoring module was built; Task 42 didn't ask to change it.
  - Post-apply `terraform plan` for `dev` confirms zero drift ("No changes. Your infrastructure
    matches the configuration.") — the `dlq_url` output fix required no `apply`, purely computed
    from existing state, as expected for an output-only change.
- **Phase 9 close-out health check (post-Task 42, pre-push) — ✅ run, one real finding, fixed.**
  - Full regression, all 4 Python services run together in one venv session, twice for stability:
    `shared` 13/13 (100%), `api` 17/17 (100%), `worker` 44/44 (96%, `mcp_clients.py`/
    `report_saver.py` 100%), `mcp-server` 26/26 (95%, `mcp_metrics.py` 100%) — all stable across
    repeat runs. `frontend` 9/9, `npm run build` green. `ruff check` clean across all 4 Python
    services; `eslint`/frontend clean.
  - Re-rendered all 4 kustomize trees (`base` 12, `dev` 14, `prod` 14, `monitoring` 16 resources)
    — all clean, counts unchanged/expected.
  - **Real finding: `terraform/environments/dev/terraform.tfvars` (created when `dev` was applied
    for Task 42) was untracked but not covered by any `.gitignore` pattern** — confirmed via
    `git check-ignore` returning nothing for it, same class of gap as Phase 7's own
    `kubernetes/**/secret.yaml` fix. **Fixed:** added `*.tfvars` alongside the existing
    `terraform.tfstate`/`.terraform/` rules; confirmed both directions (the real file is now
    ignored, `git status` no longer lists it, no other tracked file affected).
  - Secrets/debug-marker sweep across the full branch diff (30 files, 785 insertions): clean, zero
    hits for secret-shaped strings, `console.log`/`debugger`, or `TODO`/`FIXME`/`HACK`.
  - File-state audit (`git diff --stat main...feature/phase-9-observability`): exactly the 30
    files this phase's 6 commits touched — nothing stray.
  - **Verdict: Phase 9 is sound and ready to merge.** No regressions anywhere, every fix verified
    empirically (not just asserted), and the three genuinely new open items (kube-state-metrics
    gap, structured-logging gap, dead `LLM_CALL_COUNT`) are recorded below rather than left only
    in this session's own memory.

---

### Phase 10 — Local Full-Stack Integration (Task 43) — ✅ complete

- Branch: `feature/phase-10-local-integration`, cut from `main` after confirming PR #19
  (Phase 9) merged (local `main` was 8 commits behind — same session-start correction pattern
  as every prior phase).
- **Pre-work (before implementing):** read plan.md's Task 43 (only task in Phase 10) and ran
  the standing open-items applicability check. Two real problems found and resolved in chat
  before any code was written, not silently:
  1. **GitHub-auth gap directly blocks this task, for the first time outside Kubernetes.**
     Task 43's own docker-compose snippet points `mcp-github` at the raw
     `ghcr.io/github/github-mcp-server:latest` image with no bearer-header injection — the
     exact configuration Task 8/Phase 7 already proved 401s on every request. **User decision:**
     port Task 33's nginx auth-proxy sidecar pattern into docker-compose as a second service.
  2. **Smoke-test target contradicts itself.** Task 43's Interfaces line claims "a local
     fixture repo path, not github.com," but its own Step 3 script posts
     `octocat/Hello-World`, a real public repo. Checked empirically (extracted and inspected
     the `github-mcp-server` binary directly, not just `--help`): no flag, env var, or mode
     exists to point the official image at a local git repository — only `--gh-host` for a
     real GitHub Enterprise Server instance. **User decision:** accept the scope change, use a
     real narrowly-scoped read-only PAT against real github.com. Per this project's standing
     convention of never editing `plan.md`'s historical task text (design.md gets corrected
     instead; see Task 31/Phase 6's precedent) — this correction is recorded here, not by
     editing plan.md's Task 43 Interfaces line.
     - **`octocat/Hello-World` itself turned out to be structurally unusable, found by
       actually running the smoke test against it, not assumed.** First real run failed with
       `status=failed`, `"No acceptance criteria found in issue body or comments"` —
       correct, documented Node #4 graceful-termination behavior (design.md's error-handling
       table), not a bug. Investigated why: `octocat/Hello-World#1`'s body is empty (confirmed
       via a direct `GET /repos/octocat/Hello-World/issues/1` call), and so is every other
       issue on that repo (checked the full list — `octocat/Hello-World` is GitHub's generic
       tutorial/practice repo; every issue on it is a throwaway test post, none over ~175
       characters). Also checked `microsoft/vscode#1` (used for a different purpose in Task
       8's live verification) as a possible substitute — also an empty body, comments are
       just "Looks easy enough!"/"👍", not requirements either. **Conclusion: no issue on
       `octocat/Hello-World` can ever reach `status=completed`** — inherent to what the repo
       is, not bad luck with issue #1. **User decision:** use a purpose-built fixture issue in
       `Sleeman01/testscope-ai` itself instead — fully within the user's control, guaranteed
       stable. Created via `gh issue create` (issue **#20**, "[Smoke Test Fixture] Sample
       acceptance criteria for local E2E test", 3 bulleted acceptance criteria); content
       verified read-back via `gh issue view` before wiring it into the script.
       `scripts/local-e2e-smoke-test.sh` now targets `{"repository": "Sleeman01/testscope-ai",
       "issue_number": 20}`, with the script's own header comment explaining why, so the next
       person reading it doesn't have to rediscover this.
- **Decision 1 implemented — mcp-github split into two docker-compose services**
  (`mcp-github-upstream` + `mcp-github`), not one, mirroring
  `kubernetes/base/mcp-github/{deployment.yaml,auth-proxy-configmap.yaml}` as closely as
  compose's networking model allows:
  - `mcp-github-upstream`: the real image, `http --port 8101 --listen-host 0.0.0.0`
    (`0.0.0.0` not `127.0.0.1` — compose containers don't share a network namespace the way
    pod containers do; the equivalent isolation property comes from publishing no host port
    at all, not from a loopback bind), `GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PAT}`.
  - `mcp-github`: `nginx:1.27-alpine`, template ported verbatim in spirit from
    `auth-proxy-configmap.yaml` to `docker/mcp-github-auth-proxy/default.conf.template`
    (only real difference: `proxy_pass` targets `mcp-github-upstream:8101` by compose service
    name instead of `127.0.0.1:8101`), injects `Authorization: Bearer ${GITHUB_TOKEN}` before
    proxying. `worker`/`api`/`mcp-test-analysis` all still address
    `http://mcp-github:8100/mcp` completely unchanged — that name now resolves to the proxy,
    the same way the k8s Service object always pointed at the sidecar, transparently to every
    caller. **`backend/worker/app/mcp_clients.py` untouched, stays token-free by design, per
    explicit instruction.**
  - Confirmed (not assumed) that `mcp-server/github_client.py`'s own direct
    `Authorization: Bearer <token>` header (sent with whatever `GITHUB_TOKEN` `mcp-test-analysis`
    holds — the plan's literal placeholder `local-dev-unused`) is harmless once it reaches the
    proxy: `proxy_set_header Authorization ...` unconditionally overwrites any incoming header,
    so the real PAT always reaches the upstream server regardless of what any caller sends —
    exactly the "transparent fix, zero caller changes" property the k8s sidecar already relied on.
  - Also empirically verified (before trusting the plan's `GITHUB_TOKEN=local-dev-unused`
    placeholder for `mcp-test-analysis`'s own direct git-clone step, `mcp-server/server.py`'s
    `https://x-access-token:{GITHUB_TOKEN}@github.com/...` URL): a bogus credential does **not**
    break an anonymous-eligible clone of a public GitHub repo (`git clone` with a garbage
    `x-access-token` succeeded identically to a credential-less clone, both exit 0). So the
    placeholder is safe to leave as the plan's literal text here — no deviation needed.
  - Credential handling, per explicit instruction: no PAT value ever entered this session.
    `docker-compose.yml`'s header comment documents both required env vars
    (`ANTHROPIC_API_KEY`, `GITHUB_PAT`) and that they're read from the shell/a gitignored
    `.env` (already covered by existing `.env`/`.env.*` gitignore patterns) — never
    hardcoded. The user created and populated `.env` themselves.
- **Real bugs found by actually running the stack (not discovered any other way — this is
  the first task in the whole project that starts every service via its real entrypoint at
  once), same "run it for real" pattern as every prior phase:**
  1. **`localstack-init` depends_on race.** The plan's literal `depends_on: [localstack]`
     only waits for the container to start, not for LocalStack's own services to be ready;
     confirmed via a real run (`Could not connect to the endpoint URL`). Fixed with Compose's
     native `condition: service_healthy` against `localstack/localstack:3.8`'s own built-in
     `HEALTHCHECK`, not a custom retry loop.
  2. **`localstack-init` re-run idempotency gap**, found on a later retry (after fixing an
     unrelated port conflict without an intervening `docker compose down` — `localstack` had
     no declared volume but stayed running continuously, so its in-memory state persisted):
     the `&&`-chained commands aren't safe to re-run — `ResourceInUseException` on the first
     command stopped the chain before the bucket/queue steps ran at all. Fixed with `|| true`
     per step (`;`-separated instead of `&&`) — appropriate for this local-dev convenience
     script specifically, not applied anywhere AWS-account-facing elsewhere in the repo.
  3. **`backend/worker/Dockerfile`'s `CMD` has been broken since Task 17, unrelated to Task 43
     itself — first exposed here because this is the first time anything in the project has
     started this container via its real entrypoint.** `CMD ["python", "app/main.py"]` sets
     `sys.path[0]` to the script's own directory (`/app/app`), not the `WORKDIR` (`/app`), so
     `app/main.py`'s `from app.health import ...`/`from app.runner import ...` always failed
     with `ModuleNotFoundError: No module named 'app'` in a real container run. Every earlier
     check (Task 17) verified imports via `python -c "import app.main"` instead, which has
     different `sys.path` semantics and never exercised this path; Phase 8's CI/CD never
     caught it either since the self-hosted runner precondition was never met, so no real
     `deploy-dev`/`deploy-prod` has ever actually started this container. **Fixed:**
     `CMD ["python", "-m", "app.main"]`, matching how `uvicorn app.main:app` already resolves
     the identical import in `backend/api/Dockerfile`. Confirmed fixed, not just assumed:
     rebuilt, restarted, `docker compose logs worker` clean (silent poll loop, no traceback),
     vs. the traceback before the fix.
- **Port conflicts, found and resolved one at a time (real, pre-existing, unrelated local
  processes on this dev machine — not touched, per explicit instruction each time):**
  `api` 8000→8001 (`polyaifursa-agent-1`), `frontend` 3000→3002 (`polyaifursa-frontend-1` on
  3000 *and* `polyaifursa-grafana-1` on the first-tried 3001), `worker` 8080→8081
  (`polyaifursa-yolo-1`). Each remap confirmed against the live port listing before use, not
  guessed. Container-internal ports unchanged in all three cases; only host-facing URLs moved
  (`scripts/local-e2e-smoke-test.sh` updated to `localhost:8001`; no docs reference the
  frontend's or worker's host port anywhere in the repo, so nothing else needed updating).
- **`GITHUB_TOKEN` missing from `worker`'s environment entirely — real gap in the plan's own
  Task 43 snippet, found by the first real smoke-test run.** `requirement_retriever.py`'s
  issue-body fetch bypasses MCP (design.md §5.2) and calls `os.environ["GITHUB_TOKEN"]`
  directly against real `api.github.com` — the plan's literal `worker` environment block
  never declares it. First real run failed immediately: `Could not fetch issue body:
  'GITHUB_TOKEN'` (a raw `KeyError`). **Fixed:** added `GITHUB_TOKEN=${GITHUB_PAT}` to
  `worker`'s environment in `docker-compose.yml` — same PAT already used by the auth-proxy,
  not a second secret; documented inline why this call needs it despite MCP-routed calls
  staying token-free.
- **Real, previously-undetected bug in three LLM nodes' tool schemas — first exposed because
  Task 43 is the first task in the whole project to make a real Claude API call.**
  `coverage_analyzer.py`, `test_plan_generator.py`, and `missing_test_recommender.py` all use
  `RootModel[list[...]]` as their `call_llm` response model; `RootModel[list[X]]
  .model_json_schema()` produces a top-level `{"type": "array", ...}` schema, but Anthropic's
  tool `input_schema` requires `"type": "object"` — confirmed via the real 400:
  `tools.0.custom.input_schema.type: Input should be 'object'`. **Fixed in one place**
  (`backend/worker/app/llm_client.py`, not the three node files): when the response model's
  schema is array-typed, wrap it in a single-property object (`{"entries": <array schema>}`)
  for the request and unwrap `tool_use.input["entries"]` on the way back — the three nodes'
  own `.root` usage and existing tests (which all mock `call_llm` itself) are untouched.
  Verified the wrapped schema round-trips correctly for all three models via direct,
  real-API calls against the running `worker` container (not assumed).
- **Real, intermittent-looking bug that was actually deterministic once diagnosed:**
  `test_plan_generator`'s real (non-toy) prompt against `TestPlan`'s verbose per-test-case
  schema hit `llm_client.py`'s hardcoded `max_tokens=4096` — confirmed directly
  (`stop_reason: "max_tokens"`, `usage.output_tokens: 4096`, `tool_use.input` truncated to an
  empty dict). Three isolated single-node repro attempts with toy prompts all succeeded
  first, which briefly looked like the array-wrapping fix was still broken (an incorrect
  "items is a reserved JSON Schema keyword" collision theory was tried and documented, then
  found wrong and removed once the real cause was confirmed) — the actual trigger only
  reproduces with a real multi-criterion prompt. **Fixed:** raised to `max_tokens=16000`,
  matching the claude-api skill's documented safe ceiling for a non-streaming request.
- **Real, pre-existing bug since Task 11: `requirement_retriever.py`'s `issue_read`/
  `get_comments` result-shape assumption was wrong, and its own unit test encoded the same
  wrong assumption.** design.md §5.2 already recorded, from Task 8's live verification, that
  `get_comments` "returns a list of comments" directly — but Task 11's implementation (and
  `test_requirement_retriever.py`'s mock) assumed `{"comments": [...]}` anyway. Confirmed via
  a real traceback (`AttributeError: 'list' object has no attribute 'get'`) — caught
  non-fatally by the existing try/except (design's documented "fall back to issue body only"
  behavior), so it never surfaced as a failure, just silently discarded every real comment.
  **Fixed:** `[c.get("body", "") for c in comments]` (bare list), plus updated
  `test_requirement_retriever.py`'s mock and `test_runner_e2e.py`'s `fake_issue_read_comments`
  stub to match (both encoded the same wrong shape).
- **Real, pre-existing bug since Task 17, the most significant of this task's findings:
  `s3_report_key` has never been persisted for any analysis this project has ever completed.**
  `report_saver.py` called `save_coverage_report` (which returns `{s3_report_key,
  dynamodb_status}`) but discarded the return value outright; `runner.py`'s final
  `AnalysisRecord` write never included `s3_report_key` as a field at all. Confirmed via a
  real trace: `GET /api/analyses/{id}/report` 500'd with a bare `botocore.ParamValidationError`
  (`Invalid type for parameter Key, value: None`) despite `storage_status: "saved"` on the
  same record — the report genuinely saved to S3, the pointer to it just never reached
  DynamoDB. **Fixed in three places, matching this file's own state.py precedent for
  `storage_status`:** `report_saver.py` now captures `result["s3_report_key"]` into state;
  `app/state.py`'s `AgentState` TypedDict now declares it (LangGraph silently drops any state
  key a node returns that isn't declared there — the exact trap `storage_status`'s own
  comment already documents, now caught before shipping instead of after); `runner.py`'s
  final `AnalysisRecord(...)` now passes it through. Added `assert result["s3_report_key"]
  == "k"` to `test_report_saver.py`'s success case to close the gap that let this ship
  undetected.
- **Local E2E smoke test: PASSED for real, `status: "completed"`, verified by reading the
  actual output — not inferred from exit code.** Full pipeline reached `status=completed`
  against `Sleeman01/testscope-ai#20` with a genuine LLM-produced requirement summary,
  3-criterion coverage matrix (1 Covered via evidence from this repo's own real test files,
  2 Not covered), a 26-item test plan, 2 missing-test recommendations, and a working presigned
  S3 download URL. Took ~170s end-to-end (5 real sequential Claude calls at up to 16000
  `max_tokens` each). `docker compose down` (teardown) clean.
- **Post-fix full repo regression, all 4 Python services + frontend, run together:**
  `backend/shared` 13/13, `backend/api` 17/17, `backend/worker` 44/44, `mcp-server` 26/26,
  `frontend` 9/9 — all green, `ruff check .` clean across all 4 Python services. Secrets/
  debug-marker sweep across the full diff: clean (no `sk-ant-`/`ghp_`/AKIA-shaped strings,
  no `console.log`/`debugger`, no `TODO`/`FIXME`/`HACK`). `.env` (created by the user,
  holding the real `GITHUB_PAT`/`ANTHROPIC_API_KEY`) confirmed untracked throughout — never
  read or displayed by this session, per the user's explicit instruction.
- **Verdict: Task 43 complete, the local full-stack integration genuinely works end-to-end.**
  Five real, previously-undetected production bugs (`GITHUB_TOKEN` gap, array-schema tool
  definitions, `max_tokens` truncation, `issue_read`/`get_comments` shape, `s3_report_key`
  never persisted) surfaced and fixed only because this was the first task in the whole
  project to run every service via its real entrypoint and make real Claude/GitHub API calls
  at once — none were reachable by any earlier phase's mocked-boundary tests.

---

### CI fix — ghcr.io image tag lowercasing (`deploy-dev.yml`/`deploy-prod.yml`) — ✅ complete

- Branch: `fix/ghcr-lowercase-image-tag`, cut from `main` after confirming PR #21 (Phase 10)
  merged (local `main` was 2 commits behind — same session-start correction pattern as every
  prior phase).
- **Real CI failure, reported by the user, not found during a health check:** `docker build -t
  ghcr.io/${{ github.repository_owner }}/testscope-...` fails outright — ghcr.io (like every
  OCI registry) requires an all-lowercase repository name, and `github.repository_owner`
  preserves the GitHub username's actual casing (`Sleeman01`). Confirmed via a direct dry-run
  of the exact extracted bash logic with the real value (`Sleeman01` → `ghcr.io/Sleeman01/...`,
  invalid), not just inspected by eye.
- **Grepped every workflow for `ghcr.io`/`github.repository`/`github.repository_owner`
  first, rather than assuming which files were affected:** `pr.yml`'s image builds never
  reach `ghcr.io` at all (bare `testscope-<image>:<sha>`, no push) — unaffected. Both
  `deploy-dev.yml` and `deploy-prod.yml` construct `ghcr.io/${{ github.repository_owner }}/...`
  in two places each: the `build-and-push` job's `docker build`/`docker push` pair, and the
  `deploy` job's `sed` substitution loop that retags the rendered kustomize manifests
  (`deploy-dev.yml` uses `${{ github.sha }}`, `deploy-prod.yml` uses `${{ github.ref_name }}`
  — the only difference between the two).
- **Fixed in both files, both jobs (4 sites total):** `OWNER_LC=$(echo "${{
  github.repository_owner }}" | tr '[:upper:]' '[:lower:]')` computed once per `run:` block
  (GitHub Actions' `${{ }}` expression language has no built-in `lower()`; `GITHUB_ENV` doesn't
  persist across jobs, so it's recomputed once in `build-and-push` and once in `deploy`, not
  hoisted to a single shared value), then referenced as `${OWNER_LC}` everywhere the tag is
  built. Deliberately not hardcoded as a literal `sleeman01` string — derived from the existing
  `github.repository_owner` expression so it keeps working if the repo is ever renamed or
  forked under a different owner.
- **Verified two ways, not just eyeballed:** (1) `python3 -c "import yaml; yaml.safe_load(...)"`
  on both edited files — valid YAML, no structural breakage from the edit. (2) Extracted the
  actual bash logic (the `OWNER_LC=...` line plus every downstream construction — build tag,
  push tag, and the `sed` substitution against a sample manifest line) and ran it for real
  with `github.repository_owner` set to the literal value `"Sleeman01"`: produced
  `ghcr.io/sleeman01/testscope-api:abc1234` (build/push) and correctly rewrote
  `ghcr.io/testscope-ai/api:latest` → `ghcr.io/sleeman01/testscope-api:abc1234` via the sed
  substitution, for both the `github.sha` (dev) and `github.ref_name` (prod) cases.
- **Repo-wide sweep for any other `ghcr.io` tag construction site, not just the two files
  already found:** the only other `ghcr.io/testscope-ai/*:latest` references are the
  **static placeholder tags** in `kubernetes/base/*/deployment.yaml` — per plan.md's own
  documented design, these are fixed literals overwritten by this exact CI `sed` step, not
  derived from `github.repository_owner`, so they were never affected.
  `ghcr.io/github/github-mcp-server:latest` (the official third-party image) is likewise
  unrelated — not owner-derived at all.
- **`docs/2026-07-30-testscope-ai-plan.md` contains the same original (unfixed) snippet —
  left as-is, per this project's standing convention of never editing `plan.md`'s historical
  task text** (see Task 31/Phase 6's precedent, and Task 43's Interfaces-line correction
  above); this entry is the authoritative record of the deviation instead.
- No credential/secret handling — `${{ secrets.GITHUB_TOKEN }}` usage untouched by this fix.

## Open Questions / Things to Revisit

- **NEW (Phase 9), OPEN: the Grafana dashboard's "Pod Restarts" panel has no data source.**
  It queries `kube_pod_container_status_restarts_total`, a kube-state-metrics metric.
  kube-state-metrics is not deployed anywhere in this project — not in Task 40's manifests, not
  listed in design.md §12's stated stack ("Prometheus + Grafana + Loki/Promtail"), and Task 40's
  own scrape config wouldn't discover a kube-state-metrics pod even if one existed (it only keeps
  pods whose `app` label matches `api|worker|mcp-test-analysis|mcp-github`). This panel will read
  "No data" until kube-state-metrics is deployed as its own, separately-scoped piece of work —
  explicitly unscheduled, same pattern as the GitHub-auth gap once was.
- **NEW (Phase 9), OPEN: the Grafana dashboard's "Recent Failed Analyses (logs)" panel has no
  data source either.** It filters Loki logs on the literal substring `"status=failed"`, but no
  task through Task 41 ever implemented the structured JSON logging design.md §12 calls for
  ("Logs: structured JSON (`analysis_id`, `request_id`, ... final status)") — confirmed via a
  repo-wide grep of every `logger.exception`/`logger.warning` call across `backend/` and
  `mcp-server/`: every one is a plain formatted string, none contain that substring or any
  structured field at all. This panel will also read "No data" until structured logging exists.
  Whoever builds it should also decide whether the log-search convention should be a literal
  `status=failed` field match or something else — not decided here, since that's a logging-format
  choice, not a dashboard-authoring one.
- **NEW (Phase 9), OPEN, low-priority: `testscope_llm_calls_total` (`LLM_CALL_COUNT`,
  `backend/shared/metrics.py`) is declared but never incremented anywhere.** Task 39 declared it
  (per plan.md's own primitive list) but never wired it into `backend/worker/app/llm_client.py`'s
  `call_llm`, and no Task 41 dashboard panel references it either — so it's simply inert today,
  not broken. Worth wiring up if LLM call latency/failure visibility becomes a real need; not
  blocking anything today.

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

- **KNOWN FOLLOW-UP TASK, explicitly unscheduled to any phase: `POST /api/analyses/{id}/github-issue`
  is not functional against the real `mcp-github` server as currently deployed** — confirmed by
  live-testing the real `github-mcp-server` container (HTTP mode), which returns `401
  Unauthorized` without a per-request `Authorization: Bearer <token>` header. `backend/api`
  cannot supply that header without holding the GitHub token itself, which would violate
  design.md §9's explicit secrets boundary ("GitHub token mounted only in
  `mcp-github`/`mcp-test-analysis`... Neither reaches `api` or `frontend`"). Full detail,
  reasoning, and options in the Phase 4 Task 22 entry above. **The same gap independently
  affects `backend/worker`'s already-merged `call_github_tool` (Task 11, Phase 3)** —
  `request_validator`'s `search_repositories` call and `requirement_retriever`'s
  `issue_read`/`get_comments` call have the identical missing-Authorization-header problem, never
  caught because every existing test (worker's and `backend/api`'s) mocks the MCP transport
  boundary rather than hitting a real server.
  - **Phase 6 pre-work (before Task 27) checked this explicitly, rather than assuming the prior
    phrasing below was still accurate, and re-verified it empirically instead of just re-reading
    the old finding:** Phase 6 (Tasks 27–31 — Terraform `networking`/`ec2`/`iam`/`s3`/`dynamodb`/
    `sqs`/`monitoring` modules) has **no GitHub/MCP scope at all** — grepped the full Phase 6 plan
    text for github/token/bearer/sidecar/gateway; the only hits are unrelated (AWS "internet
    gateway", the kubeadm bootstrap token). The previous wording here ("squarely a Phase 6/Phase 7
    concern... recommend scheduling it explicitly when those phases start") was itself
    speculative and is corrected now: Phase 6 does not touch this at all, and Phase 7's Task 33
    (`mcp-github` Kubernetes manifests) as currently written does **not** close it either — it
    only sets `GITHUB_PERSONAL_ACCESS_TOKEN` as a container-level env var on the `mcp-github`
    Deployment, which is a different thing from a per-request inbound `Authorization` header.
  - **Re-verified live against the same image/version this finding originally used**
    (`ghcr.io/github/github-mcp-server:latest`, `v1.8.0`, digest
    `sha256:d5a18c04b92714c309eb46a2305087e91a4dbd80420f6e462656699f95093520`): started the
    container in HTTP mode (`http --port 8100 --listen-host 0.0.0.0`) with
    `GITHUB_PERSONAL_ACCESS_TOKEN` set in the container's own environment (never printed/logged/
    committed — sourced from `gh auth token`, referenced by env var name only). A request with no
    `Authorization` header still returns `401 Unauthorized`
    (`WWW-Authenticate: Bearer resource_metadata="http://.../.well-known/oauth-protected-resource/mcp"`);
    the identical request with a valid `Authorization: Bearer <token>` header succeeds
    (`initialize` + `tools/list` returns 44 tools). Corroborated by `--help` on both subcommands:
    `http`'s only auth-related flags are OAuth-resource-metadata flags (`--base-url`,
    `--base-path`, `--scope-challenge`) — no token/PAT flag exists for HTTP mode at all — while
    `stdio`'s flags (`--app-id`, `--app-private-key-path`, `--oauth-client-id`) are for local
    single-process auth instead. Per the server's own OAuth-protected-resource design, HTTP mode's
    env var supplies no inbound-auth exemption; since the unauthenticated call never got past the
    handshake, no further "does the env var's identity actually work outbound" call was needed to
    settle the question.
  - **Conclusion: the env var is not sufficient — a per-request bearer header is still required.**
    A token-injecting sidecar/gateway in front of `mcp-github` (or a deliberate revision of
    design.md §9's "Neither reaches `api` or `frontend`" boundary if token custody is to be
    extended) is genuinely needed to close this gap. **Explicitly unscheduled** — not assigned to
    Phase 6, Phase 7, or any other phase; whoever picks this up should schedule it deliberately
    when it's actually designed, not assume an existing phase's plan text already covers it.
  - Until fixed: `POST /api/analyses/{id}/github-issue` (Task 22), `request_validator`
    (Task 11), and `requirement_retriever`'s comments fetch (Task 11) will all 401 against a real
    `mcp-github` deployment, though none of this is visible from any current test suite, all of
    which pass cleanly by design (mocked transport boundary).
  - **ADDRESSED (design-level) in Phase 7, Task 33 — not yet empirically re-verified against a
    live cluster.** The user made an explicit architectural decision (sidecar, not gateway or
    oauth2-proxy — see the Phase 7 entry above for the full rationale) and it's now implemented
    and committed: an `nginx` sidecar in the `mcp-github` pod injects `Authorization: Bearer
    <token>` on every request reaching the Service's port, from the same `github-token` Secret,
    before proxying to the real `github-mcp-server` container. Since this sits in front of the
    Service endpoint itself, it should transparently fix `POST /github-issue`, `request_validator`,
    and `requirement_retriever` all at once, with zero changes needed to any of their own code —
    none of them hold or send a token today, and none of them need to. **This is a design/code
    claim, not a live-verified one**: Task 33's own validation was `kubectl kustomize` render +
    YAML-parse only (the same live-cluster-access gap noted in every Phase 7 task — this dev
    machine can't reach the cluster's intentionally internal-only port 6443). Closing this for
    real requires an actual `apply` + a live `curl`/tool-call test against the deployed sidecar,
    the same kind of empirical check Task 8 originally used to *find* this gap.
  - **Phase 8 built the mechanism that will finally perform this live check, but has not run it
    yet.** `deploy-dev.yml`/`deploy-prod.yml` (Tasks 37/38) are the first place in this project
    where a real `kubectl apply` reaches the live cluster from a self-hosted runner — until that
    runner is registered and the `github-token` Secret exists in `dev`/`prod` (see the two new
    Open Questions entries below), neither workflow can run at all, so this remains exactly as
    unverified as it was at the end of Phase 7. Not re-deferred to a future phase — it's now
    blocked on the manual infrastructure preconditions below, not on any more code.

- **RESOLVED: `@types/react`/`@types/react-dom` added, user-approved, see the Phase 5 entry
  above for full detail.** Was: `frontend/package.json` had no `@types/react`/`@types/react-dom`
  in `devDependencies`, found during Task 23 — the first task to write real `.tsx`/JSX. Fix:
  installed both at `^18` (matching the confirmed-installed `react@18.3.1`/`react-dom@18.3.1`),
  `devDependencies` only, no other package version changed. `tsc -b` now passes cleanly.

- **RESOLVED, user decided to add it now: `frontend/index.html` was missing (no task in the plan
  ever created it).** Full verification steps and detail in the Phase 5 entry above (grepped the
  whole plan for `index.html` and for `setupFiles`/`jest-dom`, confirmed the real entry
  module/mount target from the repo, verified both `npm run build` and `npm run dev` boot clean
  after adding a minimal file). `npm run build` is now fully green end-to-end.
- **RESOLVED: `@testing-library/jest-dom` was a `devDependency` since Task 1 but never wired up
  (no `setupFiles`, no import for its `expect.extend` side effect) — found via Task 25's
  RED-verification (`toBeInTheDocument` → `Invalid Chai property`).** Fixed by adding
  `frontend/src/setupTests.ts` (imports the already-installed `@testing-library/jest-dom/vitest`
  subpath — no new dependency) and wiring it into `vitest.config.ts`'s `test.setupFiles`. Full
  detail in the Task 25 entry above.

- **OPEN, explicit Phase 8 completion precondition, not vague backlog: `deploy-dev.yml` cannot
  reach a Running pod in `dev` (and `deploy-prod.yml` cannot in `prod`) until someone manually
  creates two Secrets per namespace.** Neither workflow will even get past `ContainerCreating` for
  the affected pods without these — this isn't a nice-to-have follow-up, it's the literal
  difference between "the workflow file exists" and "the workflow runs."
  1. **`github-token`** (`mcp-test-analysis`, `mcp-github`, and the `auth-proxy` sidecar all
     reference it by name) — known since Phase 7's health check
     (`kubernetes/base/mcp-test-analysis/secret.yaml.example`'s own comment already documents the
     copy-and-fill-in workflow); still not created anywhere as of Phase 8's end.
  2. **`worker-secrets`** (`anthropic-api-key` key, referenced by `kubernetes/base/worker/
     deployment.yaml`) — **newly found during Phase 8, not previously flagged anywhere in this
     log.** Confirmed via a repo-wide search that, unlike `github-token`, there is no
     `.example` file for this one at all — whoever creates it has to know the exact key name from
     reading the Deployment manifest directly, with no template to copy.
  Both need to exist in `dev` and separately in `prod` (Secrets are namespace-scoped). Documented
  in `.github/workflows/README.md` alongside the runner-registration step below, so the
  instructions live next to the workflows that need them, not only in this log.

- **OPEN, explicit Phase 8 completion precondition, not vague backlog: neither deploy workflow can
  run at all yet — the self-hosted runner and `production` Environment don't exist.**
  1. **Self-hosted runner**, label `testscope-k8s`, registered on the control-plane EC2 node
     (repo Settings → Actions → Runners → New self-hosted runner; run the provided
     `config.sh`/`run.sh` as a systemd service). Both `deploy-dev.yml` and `deploy-prod.yml`'s
     `deploy` jobs specify `runs-on: [self-hosted, testscope-k8s]` — `actionlint` already confirms
     this label doesn't exist yet (its only finding on either workflow). While registering it,
     also add the `/etc/hosts` entry from Task 31 (`worker_private_ip dev.testscope.local
     testscope.local`) on that same host — both smoke tests curl those hostnames from the
     control-plane and can't resolve them otherwise.
  2. **`production` GitHub Environment** with at least one required reviewer (repo Settings →
     Environments → New environment) — `deploy-prod.yml`'s `deploy` job specifies
     `environment: production`; without it, either the job has nothing to gate on or (depending
     on repo settings) fails outright referencing an undefined environment.
  Until both exist, `git push`ing to `main` or tagging a `v*.*.*` release will trigger
  `build-and-push` successfully (GitHub-hosted runner, no dependency on any of this) but the
  `deploy` job will simply never start — not fail loudly, just never pick up a runner. Worth
  knowing before assuming a quiet deploy run means success.

### Post-Phase-10 housekeeping — source-level gap fix for live-patched `dev` config/secrets

- **Branch:** `docs/k8s-config-secrets-gap`, cut fresh from `main` after confirming (via
  `gh pr list`) that PR #23 (`fix/ghcr-packages-write-permission`) had merged upstream —
  local `main` was 2 commits behind `origin/main`, same recurring session-start pattern as
  every earlier phase. Fast-forwarded before branching.
- **Trigger:** during live Phase-10-adjacent debugging, the `dev` namespace's `testscope-config`
  ConfigMap and two Secrets (`github-token`, `worker-secrets`) were manually patched directly on
  the cluster to get things running — none of that was reflected back into the checked-in
  manifests/docs, so recreating `dev` from git alone would resurface the same gaps. This entry
  documents the source-level (not live-cluster) fix, applied without touching the live cluster.
- **`SQS_QUEUE_URL` placeholder + missing region — confirmed and fixed in both `dev` and `prod`:**
  the literal `PASTE_FROM_TERRAFORM_OUTPUT_queue_url` placeholder actually lives in
  `kubernetes/dev/configmap-patch.yaml` and `kubernetes/prod/configmap-patch.yaml` (the
  per-namespace kustomize overlay patches), not `kubernetes/base/configmap.yaml` itself — base
  only has the overlay-agnostic `SQS_QUEUE_URL: "REPLACED_BY_OVERLAY"` sentinel, which was already
  correct. Reworded the placeholder to `REPLACE_WITH_TERRAFORM_OUTPUT_queue_url` with a comment
  above it in both overlay files explaining the `terraform output queue_url` step, since kustomize
  can't read a live Terraform output automatically. Left it as a placeholder (not the real live
  value) per the task's own instruction — this fix was not given cluster access and didn't need it.
  Confirmed `AWS_DEFAULT_REGION` was genuinely absent (not just under a different key — grepped
  for `AWS_REGION` too, no hits anywhere in `kubernetes/`). Added `AWS_DEFAULT_REGION: "us-east-1"`
  to `kubernetes/base/configmap.yaml` (not duplicated per-overlay) after confirming it's a safe,
  non-environment-specific constant: `terraform/environments/{dev,prod,shared}/variables.tf` all
  default `aws_region` to `"us-east-1"`, and the one checked-in `.tfvars` file
  (`environments/dev/terraform.tfvars`) only sets `alert_email`, not `aws_region` — also
  cross-checked against `environments/dev/terraform.tfstate`, which shows every deployed resource
  actually landed in `us-east-1`. `backend/shared`'s `s3.py`/`sqs.py`/`dynamodb.py` all construct
  boto3 clients/resources with no explicit region kwarg, so this env var is what they were silently
  missing. Validated with `kubectl kustomize kubernetes/dev` and `kubernetes/prod` — both overlays
  render `AWS_DEFAULT_REGION: us-east-1` merged in from base correctly.
- **`.github/workflows/README.md`: the task's own premise was inverted, caught by checking before
  assuming (per its explicit instruction to do so).** The task described `worker-secrets` as
  already documented with an exact `kubectl create secret generic ... --from-literal=...` command,
  and asked for an equivalent `github-token` entry to be added to match. Reading the file (and
  cross-checking the Phase 8 log entry above, which already recorded this) showed the opposite:
  `github-token` was already documented (copy `secret.yaml.example` → fill in → `kubectl apply`),
  while `worker-secrets` was the one **without** a concrete command (explicitly noted as "not
  shipped as an example file here"). Since no exact-command pattern for `worker-secrets` actually
  existed to match, added one instead: `kubectl create secret generic worker-secrets
  --from-literal=anthropic-api-key=<ANTHROPIC_API_KEY> -n <namespace>`. Did not duplicate or change
  `github-token`'s existing (already-working) documented method. Flagged this inversion to the user
  in the session's report rather than silently fixing the "wrong" file.
- **Not done, out of scope for this fix:** no live-cluster interaction of any kind (no `kubectl get`
  against the real `dev` namespace, no reading of the values that were live-patched tonight) — the
  fix is purely to the checked-in source so a from-scratch `dev` recreation no longer regresses;
  actually re-syncing live `dev` state (if it still differs from these files) is a separate,
  not-yet-requested step.

### Prod `api-hpa` `minReplicas` fix (PR #25) — ✅ complete

- **Branch:** `fix/prod-api-hpa-min-replicas`, cut from `main` after confirming PR #24
  (`docs/k8s-config-secrets-gap`) merged upstream — same recurring session-start pattern as
  every earlier phase.
- **Real gap, not caught by any earlier task:** `kubernetes/prod/kustomization.yaml`'s
  `replicas:` block sets `api` to `count: 2`, but `kubernetes/prod/hpa.yaml`'s `api-hpa` still
  had `minReplicas: 1` — once the HPA's controller reconciles (which happens automatically,
  not on a delay), it takes over the Deployment's replica count from whatever the manifest set
  it to, so a low-CPU window right after a prod deploy could silently scale `api` back down to
  1, undercutting the intended prod baseline of 2. `worker-hpa` is unaffected — `worker` is
  pinned to 1 replica in both `dev` and `prod` by design, no HPA/manifest mismatch there.
- **Fix:** `kubernetes/prod/hpa.yaml`'s `api-hpa.spec.minReplicas` → `2`, with an inline
  comment explaining why (matches `kustomization.yaml`'s `replicas: 2` so the HPA's first
  reconcile doesn't fight it). One-line change, `maxReplicas: 3` and the CPU-utilization
  target untouched.
- Validated via `kubectl kustomize kubernetes/prod` (renders `minReplicas: 2` correctly). No
  live-cluster access from this environment — takes effect on the next `deploy-prod.yml` run.

### Prod CPU-request reduction + SQS_QUEUE_URL durability fix (PR #26) — ✅ complete

- **Branch:** `fix/prod-cpu-requests-and-sqs-durability`, cut from `main` after PR #25 merged.
  Two independent real-infra findings, bundled into one PR since both surfaced from the same
  round of live-cluster debugging.
- **Finding 1 — prod's full stack doesn't fit on the shared worker node's CPU at the original
  request levels, confirmed against real cluster data, not estimated:** `kubectl describe node`
  on the single worker (§9's shared-cluster design — `dev`, `prod`, and `monitoring` all
  schedule onto the same one worker node) showed `Allocated resources: cpu 2/2 (100%)`, zero
  headroom, once both `dev`'s and `prod`'s stacks were live simultaneously. **Fixed by lowering
  CPU *requests* only** (limits and all memory values untouched — this narrows the scheduling
  floor, not the burst ceiling) for prod's `worker` (`250m→100m`), `mcp-github`
  (`200m→120m`), and its `auth-proxy` sidecar (`50m→20m`). Implemented as
  `kubernetes/prod/resources-patch.yaml` (a new two-document strategic-merge patch, one document
  per Deployment), registered in `kustomization.yaml`'s `patches:` list, following the same
  pattern already established by `configmap-patch.yaml`/`ingress-patch.yaml`. Validated via
  `kubectl kustomize kubernetes/prod`. **This file was superseded three commits later by PR #27
  below — see that entry; the two-document version never actually reached a real deploy
  cleanly.**
- **Finding 2 — `SQS_QUEUE_URL` reverted itself on every deploy, confirmed happening for real
  twice in `dev`, not a theoretical risk:** the checked-in `SQS_QUEUE_URL` is a placeholder by
  design (documented in the "Post-Phase-10 housekeeping" entry above — kustomize can't read a
  live Terraform output at render time). What hadn't been accounted for: every push to `main`
  (or a version tag) re-triggers `kubectl apply` with that same checked-in placeholder, silently
  reverting any live `kubectl patch`/manual fix of the real queue URL back to the placeholder —
  crash-looping `worker` with `QueueDoesNotExist` on its next poll. Happened for real twice in
  `dev` before being root-caused as a durability gap rather than a one-off. **Fixed:** one more
  `sed` substitution added to `deploy-dev.yml`/`deploy-prod.yml`'s existing single-pass render
  step (same mechanism already used for the image-tag substitutions), sourced from a **repo
  variable** (`vars.SQS_QUEUE_URL_DEV` / `vars.SQS_QUEUE_URL_PROD` — a variable, not a secret,
  since the queue URL isn't sensitive on its own), populated once per environment from
  `terraform output queue_url`. A guard clause (`if [ -z "${{ vars.SQS_QUEUE_URL_* }}" ]`) fails
  the deploy loudly with `::error::` if the variable isn't set yet, instead of silently applying
  an empty string into the rendered manifest.
- Validated both workflow files parse as YAML (`yaml.safe_load`) and the embedded bash passes
  `bash -n` with representative values substituted for the GitHub Actions expressions. No live
  deploy run exercised this at PR time — first real exercise came via PR #27's tag-`v1.0.1`
  deploy attempt below.
- **Not part of any numbered task** — same as the two entries below, this is post-Phase-10
  infra hardening surfaced by actually running the CI/CD pipeline against the live cluster, not
  planned work from `plan.md`.

### Prod kustomize multi-document patch split (PR #27) — ✅ complete

- **Branch:** `fix/prod-resources-patch-split`, cut from `main` after PR #26 merged.
- **Real CI failure, not found by any local check beforehand:** `deploy-prod.yml`'s `deploy` job
  (triggered by tag `v1.0.1`) failed at the `kubectl kustomize kubernetes/prod` step with
  `unable to parse SM or JSON patch` on `resources-patch.yaml` — the two-document file PR #26
  added (`worker` + `mcp-github`, `---`-separated) registered as a single `patches:` entry.
  **Root-caused by reproduction, not just inspection, and it's a version mismatch, not a
  generic "kustomize doesn't support multi-doc patches" rule:** kustomize's `patches:` field
  requires exactly one patch target per entry — but that two-document file had already validated
  cleanly against this dev machine's local `kubectl kustomize` before merging PR #26, because
  this machine runs kubectl v1.36.3 (bundled kustomize v5.8.1), which tolerates it. The
  control-plane's actual pinned version does not: `terraform/modules/ec2/cloud-init-control-plane.yaml.tpl`
  pins the `pkgs.k8s.io` **v1.30** apt channel, which bundles kustomize **v5.0.4** — a stricter
  parser that rejects the combined file outright. Confirmed by downloading a real kubectl
  v1.30.0 binary and reproducing the exact CI error locally *before* writing the fix, then
  re-running the same binary against the fix to confirm it now succeeds.
- **Fix:** split `kubernetes/prod/resources-patch.yaml` into `worker-resources-patch.yaml` and
  `mcp-github-resources-patch.yaml`, each a single-document strategic-merge patch, registered as
  two separate `kustomization.yaml` `patches:` entries instead of one. Same CPU-request values
  as PR #26 (`worker` 100m, `mcp-github` 120m, `auth-proxy` 20m; limits/memory unchanged) — this
  is a structural fix, not a value change. Each new file's header comment records the
  version-mismatch root cause inline, so the next person editing a multi-Deployment patch in
  this repo doesn't have to rediscover it.
- **Validated with both kubectl versions, not just the one that had been missing the bug:**
  kubectl v1.30.0 (matches the control-plane) and this machine's own v1.36.3 — both now exit 0,
  and their rendered output is identical (confirmed via `diff`, not just "both succeeded").
- **Standing lesson for this project's testing strategy, worth carrying into Task 44:** local
  `kubectl kustomize`/`kubectl apply --dry-run` validation against whatever kubectl happens to
  be installed on the dev machine is **not sufficient** to catch every real deploy-time failure
  — the authoritative version is whatever the control-plane actually has pinned
  (`cloud-init-control-plane.yaml.tpl`'s apt channel), and the two can silently diverge. No
  earlier phase's Terraform/K8s validation step (Tasks 27–35) checked for or matched kubectl
  versions between the dev machine and the deployed control-plane.
- **Not part of any numbered task** — like PR #25/#26 above, this is infra hardening that only
  surfaced from actually running `deploy-prod.yml` against the live cluster and a real version
  tag, not from any planned Task 1–44 step.

### `kubernetes/prod/smoke-test.sh` timeout bump (Task 44 pre-work) — ✅ complete, diagnosed before fixing

- **Branch:** `docs/task-44-test-plan` (this branch — Task 44 pre-work uncovered this, it isn't
  its own PR).
- **Trigger:** tag `v1.0.2`'s `deploy-prod.yml` run (triggered while re-confirming this file's
  own "Infrastructure verification" citations for Task 44) failed at the `Smoke test` step:
  `kubectl -n prod wait --for=condition=available --timeout=120s deployment/api deployment/worker
  deployment/frontend deployment/mcp-test-analysis deployment/mcp-github` reported
  `deployment.apps/api condition met` followed by `timed out waiting for the condition` on the
  other four. The preceding `kubectl apply` step itself succeeded cleanly (every resource
  `configured`/`unchanged`, confirming PR #27's kustomize fix genuinely holds) — the failure was
  isolated to the post-apply wait, not the apply itself.
- **Diagnosed before touching anything, not assumed:** four hypotheses were checked in parallel
  (missing/stale `github-token`/`worker-secrets` Secrets, an image-pull failure specific to a
  non-`api` service, a probe-config difference explaining why only `api` passed, and whether PR
  #26's CPU-request cuts were simply still too small) against the real `v1.0.2` build-and-push
  logs (all 4 images pushed real `v1.0.2` digests — ruled out image push) and the manifests
  (`api`/`frontend` reference no Secret at all, ruling Secrets in as at most a partial
  explanation). **User then confirmed live cluster state directly** (`kubectl -n prod get
  pods`/`get deployments`): every Deployment Running/Ready — `api` 2/2, `worker`/`frontend`/
  `mcp-github`/`mcp-test-analysis` all 1/1 Available. **Verdict: transient, not a real defect.**
  All 5 Deployments picked up a new pod-template hash simultaneously in this apply (the
  version-tag `sed` substitution touches `api`/`worker`/`mcp-test-analysis`/`frontend`'s image on
  every tagged deploy; `mcp-github` picked up PR #27's own resource-patch split) — triggering a
  simultaneous 5-Deployment rolling-update surge (Kubernetes' default `RollingUpdate` strategy
  creates a new pod before removing the old one, even for single-replica Deployments) under the
  thinner-than-before CPU-request headroom PR #26 deliberately left. `api` (applied first,
  untouched by the CPU cuts) cleared the 120s wait; the other four needed longer than 120s for a
  cold multi-image pull plus the scheduling squeeze, not because anything was actually broken.
- **Fix:** `kubernetes/prod/smoke-test.sh`'s `kubectl wait --timeout` raised `120s → 300s`, with
  an inline comment recording the mechanism above so the next person doesn't have to re-diagnose
  it. `kubernetes/dev/smoke-test.sh` left at `120s` — `dev` doesn't carry PR #26's CPU-request
  cuts, so it doesn't face the same squeeze.
- **Not part of any numbered task**, same as PRs #25–27 above — surfaced only by actually
  re-running the live deploy pipeline while gathering citations for Task 44, not from any planned
  step.

### Prod smoke-test fix confirmed: first genuine green `deploy-prod.yml` run (PR #28, tag `v1.0.3`) — ✅ complete

- **Branch:** `docs/task-44-test-plan` (PR #28, merged), tag `v1.0.3` pushed afterward
  specifically to get a real, not-asserted, passing prod deploy as proof the timeout fix above
  actually works — not just that it looks right by inspection.
- **`production`'s GitHub Environment `required_reviewers` protection rule held as expected:**
  pushing the tag queued the `deploy` job but did not touch the live cluster until the user
  approved it manually in the Actions UI, consistent with design.md §11's "prod on manual
  approval via a GitHub Environment protection rule."
- **Run [31473796895](https://github.com/Sleeman01/testscope-ai/actions/runs/31473796895),
  tag `v1.0.3`: genuinely green, all jobs `success`** (`build-and-push` ×4, `deploy`). The
  `Smoke test` step's `kubectl wait` log shows all 5 Deployments reporting `condition met`
  within ~0.6s of each other (`api`, `worker`, `frontend`, `mcp-test-analysis`, `mcp-github`,
  ending `Smoke test passed.`) — comfortably inside the new 300s window, not a close call; the
  cluster was already at steady state (warm images, no capacity squeeze) since the prior
  `v1.0.2` run's pods were already confirmed Running/Ready before this deploy, so this run
  didn't repeat the earlier cold-pull-plus-surge condition, it just confirmed nothing regressed.
- **Verdict: this is the first genuinely green `deploy-prod.yml` run since the post-Phase-10
  CI/infra saga began (PRs #22–28)** — every earlier prod deploy attempt (`v1.0.0`, `v1.0.1`,
  `v1.0.2`) failed for a real, distinct reason (GHCR permissions/tag-casing, the kustomize
  multi-document patch, the smoke-test timeout). `dev`'s deploy pipeline has been green since
  PR #24; `prod`'s now is too, for the first time. Both environments are confirmed live and
  passing their own post-deploy smoke test, not just "the manifests look right."
- **Not part of any numbered task**, like the entries above — this is the closing confirmation
  of the post-Phase-10 CI/infra saga, not new work; Task 44 (`docs/test-plan.md`) can now cite
  a real, verified green run for both `dev` and `prod` instead of describing the pipeline only
  in aspirational/design terms.