from fastapi import APIRouter
from app.api.v1 import health, auth, extraction

api_v1_router = APIRouter()

api_v1_router.include_router(health.router, tags=["Health"])
api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(extraction.router, prefix="/extraction", tags=["Extraction"])

# Domain routers — uncomment as modules are implemented:
# api_v1_router.include_router(mapping.router, prefix="/mapping", tags=["Mapping"])
# api_v1_router.include_router(workbook.router, prefix="/workbook", tags=["Workbook"])
# api_v1_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
# api_v1_router.include_router(diagnostics.router, prefix="/diagnostics", tags=["Diagnostics"])
# api_v1_router.include_router(reporting.router, prefix="/reporting", tags=["Reporting"])
