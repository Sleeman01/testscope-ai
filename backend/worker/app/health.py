import threading
from fastapi import FastAPI
import uvicorn

def start_health_server(port: int = 8080) -> threading.Thread:
    app = FastAPI()

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        return {"status": "ok"}  # extended in Task 17 to check SQS reachability

    thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning"),
        daemon=True, name="worker-health",
    )
    thread.start()
    return thread
