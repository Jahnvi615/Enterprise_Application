import re
import json
from pathlib import Path
import structlog

logger = structlog.get_logger()

CONFIG_DIR = Path(__file__).parent / "config"


def _normalize(label: str) -> str:
    text = label.lower().strip()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"—.*$", "", text)
    text = re.sub(r"–.*$", "", text)
    text = re.sub(r"[,;:'\"—–'""\.']", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def _normalize_cash_flow(label: str) -> str:
    text = label.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


SECTION_ALIASES = {
    "Current Assets": "Current Assets",
    "Noncurrent Assets": "Noncurrent Assets",
    "Non Current Assets": "Noncurrent Assets",
    "Non-Current Assets": "Noncurrent Assets",
    "Total Assets": None,
    "Liabilities and Equity": None,
    "Current Liabilities": "Current Liabilities",
    "Noncurrent Liabilities": "Noncurrent Liabilities",
    "Non Current Liabilities": "Noncurrent Liabilities",
    "Non-Current Liabilities": "Noncurrent Liabilities",
    "Commitments and Contingencies": None,
    "Equity": "Equity",
    "Shareholders Equity": "Equity",
}


class MappingService:
    def __init__(self):
        self._mapping = self._load_mapping("balance_sheet_mapping.json")

    def apply(self, extraction_data: dict) -> dict:
        rows = extraction_data.get("rows", [])
        mapped_rows = []

        for row in rows:
            mapped_row = dict(row)

            if row["is_non_mappable"]:
                mapped_row["mapped_category"] = ""
                mapped_row["normalized_label"] = ""
                mapped_rows.append(mapped_row)
                continue

            section = row["section"]
            source_label = row["source_label"]

            normalized = _normalize(source_label)
            mapping_section = SECTION_ALIASES.get(section)

            if mapping_section and mapping_section in self._mapping:
                category = self._find_match(normalized, mapping_section)
            else:
                category = "UNMAPPED"

            mapped_row["mapped_category"] = category
            mapped_row["normalized_label"] = normalized
            mapped_rows.append(mapped_row)

        mapped_count = sum(1 for r in mapped_rows if r.get("mapped_category") and r["mapped_category"] not in ("", "UNMAPPED"))
        unmapped_count = sum(1 for r in mapped_rows if r.get("mapped_category") == "UNMAPPED")
        logger.info("mapping_applied", mapped=mapped_count, unmapped=unmapped_count)

        return {**extraction_data, "rows": mapped_rows}

    def _find_match(self, normalized_label: str, section: str) -> str:
        categories = self._mapping.get(section, {})

        for category, variations in categories.items():
            if normalized_label in variations:
                return category

        for category, variations in categories.items():
            for variation in variations:
                if variation in normalized_label or normalized_label in variation:
                    return category

        return "UNMAPPED"

    def _load_mapping(self, filename: str) -> dict:
        path = CONFIG_DIR / filename
        if not path.exists():
            logger.error("mapping_config_not_found", path=str(path))
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        total_variations = sum(
            len(v) for cats in data.values() for v in cats.values()
        )
        logger.info(
            "mapping_config_loaded",
            sections=len(data),
            total_variations=total_variations,
        )
        return data


class CashFlowMappingService:
    def __init__(self):
        self._mapping = self._load_mapping("cash_flow_mapping.json")
        self._reverse: dict[tuple, str] = {}
        for section, categories in self._mapping.items():
            for category, variants in categories.items():
                for v in variants:
                    key = (section.lower(), _normalize_cash_flow(v))
                    self._reverse[key] = category

    def apply(self, extraction_data: dict) -> dict:
        rows = extraction_data.get("rows", [])
        mapped_rows = []

        for row in rows:
            mapped_row = dict(row)

            if row.get("is_non_mappable"):
                mapped_row["mapped_category"] = ""
                mapped_rows.append(mapped_row)
                continue

            section = row["section"]
            label = row["source_label"]
            normalized = _normalize_cash_flow(label)

            key = (section.lower(), normalized)
            category = self._reverse.get(key) or self._partial_match(section, normalized)
            mapped_row["mapped_category"] = category or "UNMAPPED"
            mapped_rows.append(mapped_row)

        mapped = sum(1 for r in mapped_rows if r.get("mapped_category") not in ("", "UNMAPPED"))
        unmapped = sum(1 for r in mapped_rows if r.get("mapped_category") == "UNMAPPED")
        logger.info("cf_mapping_applied", mapped=mapped, unmapped=unmapped)

        return {**extraction_data, "rows": mapped_rows}

    def _partial_match(self, section: str, normalized: str) -> str | None:
        section_lower = section.lower()
        for (sec, var), category in self._reverse.items():
            if sec == section_lower and (var in normalized or normalized in var):
                return category
        return None

    def _load_mapping(self, filename: str) -> dict:
        path = CONFIG_DIR / filename
        if not path.exists():
            logger.error("cf_mapping_config_not_found", path=str(path))
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        total_variations = sum(len(v) for cats in data.values() for v in cats.values())
        logger.info("cf_mapping_config_loaded", sections=len(data), total_variations=total_variations)
        return data
