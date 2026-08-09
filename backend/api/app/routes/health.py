from fastapi import APIRouter
from config import get_settings

router = APIRouter()

@router.get("/health/live")
def live():
    return {"status": "ok"}

@router.get("/health/ready")
def ready():
    get_settings()  # raises if required env vars are missing
    return {"status": "ok"}
