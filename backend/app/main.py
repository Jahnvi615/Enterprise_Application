from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.logging_config import setup_logging
from app.exceptions import register_exception_handlers
from app.api.v1.router import api_v1_router
from app.infrastructure.database import init_db
import structlog

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings.ensure_directories()
    init_db()
    logger.info(
        "app_started",
        app=settings.app_name,
        env=settings.app_env,
        storage=settings.storage_provider.value,
        job_runner=settings.job_runner.value,
    )
    yield
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Enterprise Financial Data Extraction Platform",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
