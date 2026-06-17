from fastapi import APIRouter, Depends
from app.config import settings
from app.dependencies import get_storage
from app.core.interfaces import StorageInterface

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "0.1.0",
        "environment": settings.app_env,
    }


@router.get("/health/detailed")
def detailed_health(storage: StorageInterface = Depends(get_storage)):
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "0.1.0",
        "environment": settings.app_env,
        "storage": settings.storage_provider.value,
        "job_runner": settings.job_runner.value,
        "database": "connected",
    }
