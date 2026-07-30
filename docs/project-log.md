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

**Phase:** 0 (complete, merged) → about to start Phase 1 (no Phase 1 code written yet)
**Branch pattern in use:** `feature/phase-<N>-<short-description>`, one PR per phase (docs-only
housekeeping like this entry uses `docs/<short-description>` instead)
**Current branch:** `docs/project-log-update` (fresh off `main`, this update only)
**Last merged:** `docs/claude-md` → `main` (PR #8)

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

### Phase 1 — Custom MCP Server (`mcp-test-analysis`) — not started
- Tasks: 2–8 (`extract_test_metadata` → `find_test_files`/`WorkspaceManager` →
  `read_test_file` → `cleanup_workspace`/sweeper → `save_coverage_report` →
  `get_previous_analysis` → server wiring/`FastMCP`/MCP integration test)
- Branch: not yet created (will be `feature/phase-1-mcp-test-analysis` or similar per
  the branch pattern above)

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