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

- **Phase 0's "process fix" entry above may overstate the venv issue.** Re-checked during
  this update (per CLAUDE.md's "don't trust the log's claims if out of sync with the repo"
  rule): at the time, every actual `pip install`/`pytest` invocation had `.venv` activated
  in the same shell call, and `testscope-*` packages were confirmed present only in
  `.venv/lib/.../site-packages`, never in system site-packages. The `fix/venv-isolation` PR
  (adding the README/plan.md setup step and the standing "check `which python`" habit) was
  still worth doing, but "packages were installed into system Python" as a factual claim
  didn't hold up — leaving the original wording in the Phase 0 entry as the contemporaneous
  record, flagging the correction here instead of rewriting history.