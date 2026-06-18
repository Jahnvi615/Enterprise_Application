from pydantic import BaseModel


class ExtractionSummary(BaseModel):
    periods: list[str]
    row_count: int
    line_items: int


class ExtractionResponse(BaseModel):
    job_id: str
    detected_pages: dict[str, int | None]
    statements_extracted: list[str]
    output_filename: str
    summary: dict[str, ExtractionSummary]
