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
CMD ["python", "app/main.py"]
