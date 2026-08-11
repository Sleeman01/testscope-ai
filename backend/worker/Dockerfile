# backend/worker/Dockerfile — built with repo-root build context (`docker build -f
# backend/worker/Dockerfile .`, see Task 36/37/38's build commands and docker-compose.yml's
# `context: ., dockerfile: backend/worker/Dockerfile`), so every COPY is root-relative.
# `../shared` is NOT reachable from here: Docker forbids COPY paths outside the build
# context, and the context is the repo root, not this directory.
FROM python:3.11-slim
WORKDIR /app
COPY backend/shared /shared
RUN pip install --no-cache-dir -e /shared
COPY backend/worker/pyproject.toml .
RUN pip install --no-cache-dir .
COPY backend/worker/ .
EXPOSE 8080
# Real bug, pre-existing since Task 17, first exposed by Task 43 actually starting this
# container via its real CMD (every earlier check used `python -c "import worker_app.main"`,
# a different sys.path setup): `python worker_app/main.py` sets sys.path[0] to the script's
# own directory (/app/worker_app), not the cwd (/app) — worker_app/main.py's
# `from worker_app.health import ...`/`from worker_app.runner import ...` then fail with
# `ModuleNotFoundError: No module named 'worker_app'`, since there's no `worker_app` package
# reachable from inside /app/worker_app itself. `python -m worker_app.main` adds the cwd
# (/app, this Dockerfile's WORKDIR) to sys.path instead, matching how uvicorn already
# resolves `api_app.main:app` in backend/api/Dockerfile and how pytest resolves
# `worker_app.*` imports in this service's own test suite. (Package renamed from `app` to
# `worker_app` post-Phase-11 — see item 2 of the hardening pass; the mechanism this comment
# describes is unchanged.)
CMD ["python", "-m", "worker_app.main"]
