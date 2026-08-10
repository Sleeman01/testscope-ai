import threading

import uvicorn
from config import get_settings
from fastapi import FastAPI, HTTPException
from sqs import JobQueue


def start_health_server(port: int = 8080) -> threading.Thread:
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

    thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning"),
        daemon=True, name="worker-health",
    )
    thread.start()
    return thread
