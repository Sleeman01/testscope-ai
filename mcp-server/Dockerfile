# mcp-server/Dockerfile — built with repo-root build context (see Task 36's build command),
# so every COPY is root-relative, not relative to this Dockerfile's own directory.
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY mcp-server/pyproject.toml .
COPY mcp-server/ .
RUN pip install --no-cache-dir .
RUN mkdir -p /workspace
EXPOSE 8100
CMD ["python", "server.py"]
