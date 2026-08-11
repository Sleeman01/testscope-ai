import threading

import uvicorn
from config import get_settings
from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app
from sqs import JobQueue


def build_health_app() -> FastAPI:
    # Split out from start_health_server (Task 39) so the app itself is testable via
    # TestClient without also starting a real uvicorn thread — matching the pattern
    # mcp-server/server.py's own build_health_app() already established (Task 33). Task
    # 17 originally left this bundled and explicitly deferred testing it for exactly this
    # reason; Task 39's own test-file requirement (backend/worker/tests/test_metrics.py)
    # is what finally forces the split.
    app = FastAPI()

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        # No literal snippet given in plan.md for this — only the textual instruction to
        # attempt JobQueue(...)._client.get_queue_attributes(...) and return 503 on failure,
        # "same pattern as Task 19's API readiness check" (that pattern actually lives in
        # Task 18's backend/api/app/routes/health.py, a minor plan cross-reference slip;
        # Task 18's own check is just get_settings(), no SQS call, so not directly copyable).
        try:
            queue = JobQueue(get_settings().sqs_queue_url)
            queue._client.get_queue_attributes(QueueUrl=queue._queue_url, AttributeNames=["QueueArn"])
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"SQS unreachable: {exc}") from exc
        return {"status": "ok"}

    app.mount("/metrics", make_asgi_app())
    return app

def start_health_server(port: int = 8080) -> threading.Thread:
    app = build_health_app()
    thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning"),
        daemon=True, name="worker-health",
    )
    thread.start()
    return thread
