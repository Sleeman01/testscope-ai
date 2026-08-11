# backend/api/Dockerfile — same repo-root build context as backend/worker/Dockerfile
# (Task 17); see that Dockerfile's header comment for why the paths are root-relative.
FROM python:3.11-slim
WORKDIR /app
COPY backend/shared /shared
RUN pip install --no-cache-dir -e /shared
COPY backend/api/pyproject.toml .
RUN pip install --no-cache-dir .
COPY backend/api/ .
EXPOSE 8000
CMD ["uvicorn", "api_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
