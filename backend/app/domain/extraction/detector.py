import re
import structlog

logger = structlog.get_logger()

BALANCE_SHEET_PATTERNS = [
    r"balance\s+sheet",
    r"condensed\s+consolidated\s+balance\s+sheet",
    r"consolidated\s+balance\s+sheet",
    r"statements?\s+of\s+financial\s+position",
]

CASH_FLOW_PATTERNS = [
    r"cash\s+flow",
    r"condensed\s+consolidated\s+statement\s+of\s+cash\s+flows",
    r"consolidated\s+statement\s+of\s+cash\s+flows",
    r"statements?\s+of\s+cash\s+flows",
]

P_AND_L_PATTERNS = [
    r"condensed\s+consolidated\s+statement\s+of\s+operations",
    r"consolidated\s+statement\s+of\s+operations",
    r"statements?\s+of\s+operations",
    r"statement\s+of\s+income",
    r"income\s+statement",
]


def detect_pages(pages: list) -> dict[str, int | None]:
    results = {"balance_sheet": None, "cash_flow": None, "p_and_l": None}

    for i, page in enumerate(pages):
        text = (page.extract_text() or "").lower()

        if results["balance_sheet"] is None:
            for pattern in BALANCE_SHEET_PATTERNS:
                if re.search(pattern, text):
                    if _has_financial_data(page):
                        results["balance_sheet"] = i
                        logger.info("detected_balance_sheet", page=i + 1)
                        break

        if results["cash_flow"] is None:
            for pattern in CASH_FLOW_PATTERNS:
                if re.search(pattern, text):
                    if _has_financial_data(page):
                        results["cash_flow"] = i
                        logger.info("detected_cash_flow", page=i + 1)
                        break

        if results["p_and_l"] is None:
            for pattern in P_AND_L_PATTERNS:
                if re.search(pattern, text):
                    if _has_financial_data(page):
                        results["p_and_l"] = i
                        logger.info("detected_p_and_l", page=i + 1)
                        break

        if all(v is not None for v in results.values()):
            break

    return results


def _has_financial_data(page) -> bool:
    tables = page.extract_tables()
    if not tables:
        return False
    for table in tables:
        if len(table) >= 5:
            return True
    return False
