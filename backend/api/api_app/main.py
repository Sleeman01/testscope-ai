import time

from fastapi import FastAPI, Request
from metrics import API_REQUEST_COUNT, API_REQUEST_LATENCY
from prometheus_client import make_asgi_app

from api_app.routes import analyses, health


def create_app() -> FastAPI:
    app = FastAPI(title="TestScope AI API")

    @app.middleware("http")
    async def track_metrics(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        API_REQUEST_LATENCY.labels(path=request.url.path).observe(time.time() - start)
        API_REQUEST_COUNT.labels(method=request.method, path=request.url.path, status=response.status_code).inc()
        return response

    app.include_router(health.router)
    app.include_router(analyses.router)
    app.mount("/metrics", make_asgi_app())
    return app

app = create_app()
