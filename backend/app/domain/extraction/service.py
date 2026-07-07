import os
import uuid
from pathlib import Path
import pdfplumber
from app.core.interfaces import StorageInterface
from app.domain.extraction.detector import detect_pages
from app.domain.extraction.parser import extract_table
from app.domain.mapping.service import MappingService, CashFlowMappingService
from app.domain.business_rules.service import SpreadingRulesService
from app.domain.workbook_generation.sample_output import generate_sample_workbook
from app.domain.workbook_generation.template_population import TemplatePopulationService
from app.exceptions import AppException
import structlog

logger = structlog.get_logger()


class ExtractionService:
    def __init__(self, storage: StorageInterface):
        self.storage = storage

    def process(self, pdf_bytes: bytes, pdf_filename: str, template_bytes: bytes | None = None) -> dict:
        job_id = str(uuid.uuid4())[:8]
        safe_name = Path(pdf_filename).stem

        pdf_path = self._save_temp_file(pdf_bytes, f"uploads/{job_id}_{safe_name}.pdf")

        template_path = None
        if template_bytes:
            template_path = self._save_temp_file(template_bytes, f"uploads/{job_id}_template.xlsm")

        logger.info("extraction_started", job_id=job_id, pdf=pdf_filename)

        with pdfplumber.open(pdf_path) as pdf:
            pages = detect_pages(pdf.pages)

            if pages["balance_sheet"] is None and pages["cash_flow"] is None:
                raise AppException("Could not detect Balance Sheet or Cash Flow pages in the PDF")

            extraction_results = {}

            if pages["balance_sheet"] is not None:
                extraction_results["balance_sheet"] = extract_table(
                    pdf.pages[pages["balance_sheet"]],
                    pages["balance_sheet"],
                    "balance_sheet",
                )

            if pages["cash_flow"] is not None:
                extraction_results["cash_flow"] = extract_table(
                    pdf.pages[pages["cash_flow"]],
                    pages["cash_flow"],
                    "cash_flow",
                )

        if "balance_sheet" in extraction_results:
            mapping_service = MappingService()
            extraction_results["balance_sheet"] = mapping_service.apply(
                extraction_results["balance_sheet"]
            )

            spreading_service = SpreadingRulesService()
            extraction_results["balance_sheet"] = spreading_service.enrich_extraction(
                extraction_results["balance_sheet"]
            )

        if "cash_flow" in extraction_results:
            cf_mapping_service = CashFlowMappingService()
            extraction_results["cash_flow"] = cf_mapping_service.apply(
                extraction_results["cash_flow"]
            )

        output_filename = f"{safe_name}_extracted_{job_id}.xlsx"
        output_rel_path = f"outputs/{output_filename}"
        output_abs_path = self._get_abs_path(output_rel_path)

        os.makedirs(os.path.dirname(output_abs_path), exist_ok=True)
        generate_sample_workbook(extraction_results, output_abs_path)

        template_output_filename = None
        if template_path and "balance_sheet" in extraction_results:
            template_output_filename = f"{safe_name}_populated_{job_id}.xlsm"
            template_output_path = self._get_abs_path(f"outputs/{template_output_filename}")

            template_service = TemplatePopulationService()
            template_service.process(
                template_path=template_path,
                extraction_data=extraction_results["balance_sheet"],
                output_path=template_output_path,
                cash_flow_data=extraction_results.get("cash_flow"),
            )

        logger.info("extraction_completed", job_id=job_id, output=output_filename)

        result = {
            "job_id": job_id,
            "detected_pages": {
                k: v + 1 if v is not None else None
                for k, v in pages.items()
            },
            "statements_extracted": list(extraction_results.keys()),
            "output_file": output_rel_path,
            "output_filename": output_filename,
            "summary": {
                statement: {
                    "periods": data["periods"],
                    "row_count": len(data["rows"]),
                    "line_items": sum(
                        1 for r in data["rows"] if r["row_type"] == "line_item"
                    ),
                }
                for statement, data in extraction_results.items()
            },
        }

        if template_output_filename:
            result["template_output_filename"] = template_output_filename

        return result

    def get_output_path(self, rel_path: str) -> str:
        return self._get_abs_path(rel_path)

    def _save_temp_file(self, data: bytes, rel_path: str) -> str:
        abs_path = self._get_abs_path(rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(data)
        return abs_path

    def _get_abs_path(self, rel_path: str) -> str:
        from app.config import settings
        return str(settings.data_dir / rel_path)
