import logging
import re
from datetime import datetime
import structlog

logger = structlog.get_logger()

# pdfminer emits verbose DEBUG lines (nexttoken, exec, etc.) during text extraction.
# Suppress them to avoid log spam and reduce I/O overhead during page scanning.
logging.getLogger("pdfminer").setLevel(logging.WARNING)

_DATE_FORMATS = ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"]

# Matches the JV A/R sentence in the "Partnerships and Joint Ventures" notes section.
# [\s\S]{0,400}? handles pdfplumber line-break variations between the opening phrase
# and the dollar amounts without allowing runaway backtracking.
_JV_AR_PATTERN = re.compile(
    r"Accounts\s+receivable\s+related\s+to\s+work\s+performed\s+for\s+unconsolidated"
    r"[\s\S]{0,400}?"
    r"was\s+\$\s*(\d+(?:\.\d+)?)\s+million\s+and\s+\$\s*(\d+(?:\.\d+)?)\s+million"
    r"\s+as\s+of\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})"
    r"\s+and\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE | re.DOTALL,
)

# Matches the Contract Assets table header and Unbilled receivables data line.
# The primary period date is split across two lines in pdfplumber output, e.g.:
#   "September 30,\n(in millions) 2025  December 31, 2024"
# Groups: (1) month+day, (2) first col year, (3) second col full date,
#         (4) first amount, (5) second amount (optional)
_UNBILLED_REC_PATTERN = re.compile(
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},)\s*\n"
    r"\(in millions\)\s+"
    r"(\d{4})\s+"
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4})"
    r"[\s\S]{0,300}?"
    r"Unbilled\s+receivables\s*-\s*reimbursable\s+contracts"
    r"\s*\$\s*([\d,]+)"
    r"(?:\s*\$\s*([\d,]+))?",
    re.IGNORECASE | re.DOTALL,
)

# Safety cap: prevents scanning an entire very large annual report if the pattern
# is never found. Notes sections in standard reports appear well within 80 pages.
_NOTES_SCAN_MAX_PAGES = 80


def extract_balance_sheet_notes(pdf, period: str) -> dict:
    """Entry point. Returns a dict of note values needed for Balance Sheet custom rules."""
    return {
        "jv_ar_amount": _search_jv_ar_amount(pdf, period),
        "unbilled_receivables": _search_unbilled_receivables(pdf, period),
    }


def _search_jv_ar_amount(pdf, period: str) -> int | None:
    """
    Scans PDF pages for the JV A/R sentence and returns the amount matching
    the insertion period. Stops as soon as the pattern is found.
    """
    pages_to_scan = pdf.pages[:_NOTES_SCAN_MAX_PAGES]
    accumulated = ""
    for page in pages_to_scan:
        try:
            text = page.extract_text()
        except Exception:
            continue
        if not text:
            continue
        accumulated += "\n" + text
        if _JV_AR_PATTERN.search(accumulated):
            break

    return _extract_jv_ar_amount(accumulated, period)


def _extract_jv_ar_amount(text: str, period: str) -> int | None:
    match = _JV_AR_PATTERN.search(text)
    if not match:
        logger.debug("bs_notes_jv_ar_pattern_not_found")
        return None

    amount1_raw, amount2_raw = match.group(1), match.group(2)
    date1_str, date2_str = match.group(3).strip(), match.group(4).strip()

    period_dt = _parse_date(period)
    if period_dt is None:
        logger.warning("bs_notes_period_parse_failed", period=period)
        return None

    date1_dt = _parse_date(date1_str)
    date2_dt = _parse_date(date2_str)

    if date1_dt and date1_dt == period_dt:
        amount_in_thousands = round(float(amount1_raw) * 1000)
    elif date2_dt and date2_dt == period_dt:
        amount_in_thousands = round(float(amount2_raw) * 1000)
    else:
        logger.debug(
            "bs_notes_jv_ar_period_not_matched",
            period=period,
            found_dates=[date1_str, date2_str],
        )
        return None

    logger.info("bs_notes_jv_ar_extracted", period=period, amount_thousands=amount_in_thousands)
    return amount_in_thousands


def _search_unbilled_receivables(pdf, period: str) -> int | None:
    pages_to_scan = pdf.pages[:_NOTES_SCAN_MAX_PAGES]
    accumulated = ""
    for page in pages_to_scan:
        try:
            text = page.extract_text()
        except Exception:
            continue
        if not text:
            continue
        accumulated += "\n" + text
        if _UNBILLED_REC_PATTERN.search(accumulated):
            break
    return _extract_unbilled_receivables(accumulated, period)


def _extract_unbilled_receivables(text: str, period: str) -> int | None:
    match = _UNBILLED_REC_PATTERN.search(text)
    if not match:
        logger.debug("bs_notes_unbilled_rec_not_found")
        return None

    month_day = match.group(1).strip()     # e.g. "September 30,"
    year1 = match.group(2).strip()         # e.g. "2025"
    date2_str = match.group(3).strip()     # e.g. "December 31, 2024"
    amount1_raw = match.group(4)           # e.g. "1,348"
    amount2_raw = match.group(5)           # e.g. "1,050" — may be None

    date1_str = f"{month_day} {year1}"    # "September 30, 2025"

    period_dt = _parse_date(period)
    if period_dt is None:
        logger.warning("bs_notes_period_parse_failed", period=period)
        return None

    date1_dt = _parse_date(date1_str)
    date2_dt = _parse_date(date2_str)

    if date1_dt and date1_dt == period_dt:
        amount_raw = amount1_raw
    elif date2_dt and date2_dt == period_dt:
        if not amount2_raw:
            logger.debug("bs_notes_unbilled_rec_second_amount_missing", period=period)
            return None
        amount_raw = amount2_raw
    else:
        logger.debug(
            "bs_notes_unbilled_rec_period_not_matched",
            period=period,
            found_dates=[date1_str, date2_str],
        )
        return None

    amount_in_thousands = round(float(amount_raw.replace(",", "")) * 1000)
    logger.info("bs_notes_unbilled_rec_extracted", period=period, amount_thousands=amount_in_thousands)
    return amount_in_thousands


def _parse_date(date_str: str) -> datetime | None:
    cleaned = re.sub(r"\s+", " ", date_str.strip().rstrip(","))
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None
