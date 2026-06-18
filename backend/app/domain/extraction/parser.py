import re
import structlog

logger = structlog.get_logger()

SECTION_KEYWORDS_BS = [
    ("Noncurrent assets", "Noncurrent Assets"),
    ("Non-current assets", "Noncurrent Assets"),
    ("Current assets", "Current Assets"),
    ("Total assets", "Total Assets"),
    ("LIABILITIES AND EQUITY", "Liabilities and Equity"),
    ("Other noncurrent liabilit", "Noncurrent Liabilities"),
    ("Current liabilities", "Current Liabilities"),
    ("Current liabilit", "Current Liabilities"),
    ("Long-term debt", "Noncurrent Liabilities"),
    ("Commitments and contin", "Commitments and Contingencies"),
    ("Equity", "Equity"),
]

SECTION_KEYWORDS_CF = [
    ("OPERATING CASH FLOW", "Operating Activities"),
    ("Operating cash flow", "Operating Activities"),
    ("Net earnings", "Operating Activities"),
    ("Adjustments to reconcile", "Operating Activities"),
    ("INVESTING CASH FLOW", "Investing Activities"),
    ("Investing cash flow", "Investing Activities"),
    ("FINANCING CASH FLOW", "Financing Activities"),
    ("Financing cash flow", "Financing Activities"),
    ("SUPPLEMENTAL INFORMATION", "Supplemental Information"),
    ("Effect of exchange rate", "Other"),
    ("Increase (decrease) in cash", "Other"),
    ("Cash and cash equivalents at", "Other"),
]

TOTAL_KEYWORDS_CONTAINS = [
    "total current assets", "total noncurrent assets", "total assets",
    "total current liabilities", "total shareholders", "total equity",
    "total liabilities and equity",
]

TOTAL_KEYWORDS_STARTSWITH = [
    "operating cash flow",
    "investing cash flow",
    "financing cash flow",
]

SHORT_FINANCIAL_LABELS = {"apic", "aoci", "nci"}

OCR_WORD_FIXES = {
    "securites": "securities",
    "securiies": "securities",
    "liabilites": "liabilities",
    "liabiliies": "liabilities",
    "maturites": "maturities",
    "maturiies": "maturities",
    "contingences": "contingencies",
    "contngencies": "contingencies",
    "contngences": "contingencies",
    "operatng": "operating",
    "investng": "investing",
    "depreciaton": "depreciation",
    "amortzaton": "amortization",
    "compensaton": "compensation",
    "distributons": "distributions",
    "contributons": "contributions",
    "retrement": "retirement",
    "respectvely": "respectively",
}



def extract_table(page, page_index: int, statement_type: str) -> dict:
    tables = page.extract_tables()

    if not tables:
        return {"periods": [], "rows": []}

    header_table = tables[0]
    data_table = tables[1] if len(tables) > 1 else tables[0]

    periods = _extract_periods(header_table)
    section_map = SECTION_KEYWORDS_BS if statement_type == "balance_sheet" else SECTION_KEYWORDS_CF
    rows = _parse_rows(data_table, periods, section_map)

    logger.info(
        "table_extracted",
        statement=statement_type,
        page=page_index + 1,
        periods=periods,
        row_count=len(rows),
    )

    return {"periods": periods, "rows": rows}


def _extract_periods(header_table: list) -> list[str]:
    periods = []

    all_text = ""
    for row in header_table:
        for cell in row:
            if cell:
                all_text += " " + cell.replace("\n", " ")

    found = _parse_period_from_cell(all_text)
    for p in found:
        if p not in periods:
            periods.append(p)

    if not periods:
        periods = _infer_periods_from_header(header_table)

    if not periods:
        periods = ["Period 1", "Period 2"]

    return periods


def _infer_periods_from_header(header_table: list) -> list[str]:
    all_text = ""
    for row in header_table:
        for cell in row:
            if cell:
                all_text += " " + cell.replace("\n", " ")

    month_match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)",
        all_text, re.IGNORECASE,
    )
    day_match = re.search(r"\b(\d{1,2}),?\b", all_text)

    years = []
    for row in header_table:
        for cell in row:
            if cell:
                cell_clean = cell.replace("\n", " ").strip()
                year_matches = re.findall(r"\b(20\d{2})\b", cell_clean)
                for y in year_matches:
                    if y not in years:
                        years.append(y)

    if month_match and years:
        month = month_match.group(1)
        day = day_match.group(1) if day_match else "30"
        return [f"{month} {day}, {y}" for y in years]

    return []


def _parse_period_from_cell(cell: str) -> list[str]:
    cell = cell.replace("\n", " ").strip()
    patterns = [
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})",
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})",
    ]
    results = []
    for pattern in patterns:
        matches = re.findall(pattern, cell, re.IGNORECASE)
        results.extend(matches)

    return results


def _parse_rows(table: list, periods: list[str], section_map: list) -> list[dict]:
    rows = []
    current_section = "Unknown"

    for raw_row in table:
        label = _clean_label(raw_row[0]) if raw_row and raw_row[0] else ""

        if not label or label.strip() == "":
            continue

        new_section = _detect_section(label, section_map)
        if new_section:
            current_section = new_section

        is_section_header = _is_section_header(label, raw_row)
        is_total = _is_total_row(label)

        if is_section_header:
            row_type = "section_header"
        elif is_total:
            row_type = "total"
        else:
            row_type = "line_item"

        values = _extract_values(raw_row)
        value_dict = {}
        for i, period in enumerate(periods):
            value_dict[period] = values[i] if i < len(values) else None

        section = _to_title_case(label) if is_total else current_section

        rows.append({
            "source_label": label,
            "section": section,
            "row_type": row_type,
            "is_non_mappable": is_section_header or is_total,
            "values": value_dict,
        })

    return rows


def _clean_label(raw: str) -> str:
    if not raw:
        return ""
    label = raw.replace("\x00", "t").replace("\n", " ").strip()
    label = re.sub(r"\s{2,}", " ", label)
    label = _fix_ocr_artifacts(label)
    label = label.strip()
    return label


def _fix_ocr_artifacts(label: str) -> str:
    for wrong, correct in OCR_WORD_FIXES.items():
        label = _case_preserving_replace(label, wrong, correct)
    label = label.replace("�", "’")
    label = label.replace("â", "’")
    label = label.replace("’", "’")
    return label


def _case_preserving_replace(text: str, wrong: str, correct: str) -> str:
    pattern = re.compile(re.escape(wrong), re.IGNORECASE)

    def _match_case(match: re.Match) -> str:
        original = match.group(0)
        if original[0].isupper():
            return correct[0].upper() + correct[1:]
        return correct

    return pattern.sub(_match_case, text)


def _to_title_case(label: str) -> str:
    return label.strip().title()


def _detect_section(label: str, section_map: list[tuple[str, str]]) -> str | None:
    for keyword, section_name in section_map:
        if keyword.lower() in label.lower():
            return section_name
    return None


def _is_section_header(label: str, raw_row: list) -> bool:
    if label.lower().strip() in SHORT_FINANCIAL_LABELS:
        return False

    values = _extract_values(raw_row)
    has_no_values = all(v is None for v in values)

    if has_no_values and label.isupper() and len(label) > 5:
        return True

    if _is_total_row(label):
        return False

    if has_no_values:
        return True
    label_lower = label.lower().strip()
    header_exact = {"assets", "liabilities and equity", "equity", "shareholders equity"}
    if label_lower in header_exact:
        return True
    return False


def _is_total_row(label: str) -> bool:
    label_lower = label.lower().strip()
    for keyword in TOTAL_KEYWORDS_CONTAINS:
        if keyword in label_lower:
            return True
    for keyword in TOTAL_KEYWORDS_STARTSWITH:
        if label_lower.startswith(keyword) or label_lower == keyword:
            return True
    return False


def _extract_values(raw_row: list) -> list[float | None]:
    values = []
    for cell in raw_row[1:]:
        if cell is None or cell == "" or cell == "$":
            continue
        cleaned = str(cell).replace(",", "").replace("$", "").replace("\x00", "").strip()
        if cleaned in ("", "—", "–", "-", "�", "—", "—", "–", "�"):
            values.append(None)
            continue
        match = re.match(r"^\(?([\d.]+)\)?$", cleaned)
        if match:
            num = float(match.group(1))
            if cleaned.startswith("("):
                num = -num
            values.append(num)
    return values
