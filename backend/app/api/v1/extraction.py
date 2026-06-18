from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import FileResponse
from app.dependencies import get_storage
from app.core.interfaces import StorageInterface
from app.domain.extraction.service import ExtractionService
from app.domain.extraction.schemas import ExtractionResponse

router = APIRouter()


def get_extraction_service(
    storage: StorageInterface = Depends(get_storage),
) -> ExtractionService:
    return ExtractionService(storage)


@router.post("/upload", response_model=ExtractionResponse)
async def upload_and_extract(
    pdf: UploadFile = File(..., description="Financial PDF (10-K, 10-Q, etc.)"),
    template: UploadFile = File(None, description="Template XLSM file (optional)"),
    service: ExtractionService = Depends(get_extraction_service),
):
    pdf_bytes = await pdf.read()
    template_bytes = await template.read() if template else None

    result = service.process(pdf_bytes, pdf.filename, template_bytes)

    return ExtractionResponse(**result)


@router.get("/download/{filename}")
async def download_output(
    filename: str,
    service: ExtractionService = Depends(get_extraction_service),
):
    file_path = service.get_output_path(f"outputs/{filename}")
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
