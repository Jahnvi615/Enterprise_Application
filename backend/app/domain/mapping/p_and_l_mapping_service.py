import re
import json
from pathlib import Path
import structlog

logger = structlog.get_logger()

CONFIG_DIR = Path(__file__).parent / "config"

NOT_REQUIRED_EXACT = {
    "basic eps available to fluor common stockholders",
    "diluted eps available to fluor common stockholders",
    "less: net earnings (loss) attributable to nci",
}

NOT_REQUIRED_PATTERNS = [
    re.compile(r"^basic\s+eps\b"),
    re.compile(r"^diluted\s+eps\b"),
    re.compile(r"^less:\s+net\s+earnings?(\s+\(loss\))?\s+attributable\s+to\s+nci\b"),
]


def _normalize_p_and_l(label: str) -> str:
    text = label.lower().strip()
    text = text.replace("\x00", "t")
    text = re.sub(r"\s+", " ", text)
    return text


class PAndLMappingService:
    def __init__(self):
        self._mapping = self._load_mapping("p_and_l_mapping.json")
        self._variations: dict[str, str] = {}
        for category, variants in self._mapping.items():
            for v in variants:
                self._variations[v] = category

    def apply(self, extraction_data: dict) -> dict:
        rows = extraction_data.get("rows", [])
        mapped_rows = []

        for row in rows:
            mapped_row = dict(row)

            if row.get("is_non_mappable"):
                mapped_row["mapped_category"] = ""
                mapped_rows.append(mapped_row)
                continue

            label = row.get("source_label", "")
            normalized = _normalize_p_and_l(label)
            category = self._find_match(normalized)
            if category:
                mapped_row["mapped_category"] = category
            elif self._is_not_required(normalized):
                mapped_row["mapped_category"] = "UNMAPPED (not required)"
            else:
                mapped_row["mapped_category"] = "UNMAPPED"
            mapped_rows.append(mapped_row)

        mapped = sum(1 for r in mapped_rows if r.get("mapped_category") not in ("", "UNMAPPED", "UNMAPPED (not required)"))
        unmapped = sum(1 for r in mapped_rows if r.get("mapped_category") == "UNMAPPED")
        not_required = sum(1 for r in mapped_rows if r.get("mapped_category") == "UNMAPPED (not required)")
        logger.info("p_and_l_mapping_applied", mapped=mapped, unmapped=unmapped, not_required=not_required)

        return {**extraction_data, "rows": mapped_rows}

    def _is_not_required(self, normalized: str) -> bool:
        if normalized in NOT_REQUIRED_EXACT:
            return True
        return any(p.search(normalized) for p in NOT_REQUIRED_PATTERNS)

    def _find_match(self, normalized: str) -> str | None:
        if normalized in self._variations:
            return self._variations[normalized]
        for variation, category in self._variations.items():
            if normalized.startswith(variation):
                return category
        return None

    def _load_mapping(self, filename: str) -> dict:
        path = CONFIG_DIR / filename
        if not path.exists():
            logger.error("p_and_l_mapping_config_not_found", path=str(path))
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        total_variations = sum(len(v) for v in data.values())
        logger.info(
            "p_and_l_mapping_config_loaded",
            categories=len(data),
            total_variations=total_variations,
        )
        return data
