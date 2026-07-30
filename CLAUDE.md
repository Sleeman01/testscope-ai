# Project Instructions for Claude Code

## Before starting any work
- Read docs/2026-07-30-testscope-ai-plan.md and docs/2026-07-30-testscope-ai-design.md in full.
- Read docs/project-log.md for current phase status, standing decisions, and past deviations.
- Check `git log` and the current branch to confirm what's actually been implemented — 
  don't rely solely on the log's claims if they seem out of sync with the repo.

## Working rules
- Never commit or push directly to main. Always work on a feature branch.
- Any deviation from the plan's literal text must be flagged to the user and explained 
  before proceeding, not made silently.
- Dependency version changes (e.g. security fixes) require explicit user approval first.
- Python dependencies always go into the project's .venv — confirm `which python` resolves 
  inside .venv before any pip install.

## Before ending a session
- Update docs/project-log.md: mark the current phase's status, note any deviations or 
  decisions made, and update the "Current State" section so the next session (or the user, 
  in a new Claude Desktop chat) can pick up context immediately.