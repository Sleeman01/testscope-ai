from fastapi import FastAPI
from app.routes import health

def create_app() -> FastAPI:
    app = FastAPI(title="TestScope AI API")
    app.include_router(health.router)
    return app

app = create_app()
