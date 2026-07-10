import re
import structlog

logger = structlog.get_logger()

PERIOD_TYPE_PRIORITY = {"9ME": 0, "6ME": 1, "3ME": 2}

P_AND_L_TOTAL_KEYWORDS = [
    "gross profit",
    "opera",
    "earnings before",
    "earnings (loss) before",
    "net earnings",
    "net earnings (loss)",
    "net earnings available",
    "net earnings (loss) available",
]

OCR_WORD_FIXES = {
    "securites": "securities",
    "securiies": "securities",
    "liabilites": "liabilities",
    "liabiliies": "liabilities",
    "compensaton": "compensation",
    "distributons": "distributions",
    "contributons": "contributions",
    "respectvely": "respectively",
    "atributable": "attributable",
    "a\x00ributable": "attributable",
}


def extract_p_and_l(page, page_index: int) -> dict:
    tables = page.extract_tables()
    raw_text = page.extract_text() or ""

    if not tables or len(tables) < 1:
        logger.warning("p_and_l_no_tables_found", page=page_index + 1)
        return {"periods": [], "rows": []}

    header_table = tables[0]
    data_table = tables[1] if len(tables) > 1 else tables[0]

    periods_original = _parse_p_and_l_periods(header_table)
    if not periods_original:
        logger.warning("p_and_l_no_periods_detected", page=page_index + 1)
        return {"periods": [], "rows": []}

    # Build rows using ORIGINAL column order so values zip correctly with periods
    rows = _parse_p_and_l_rows(data_table, periods_original)

    revenue_values = _extract_revenue_from_text(raw_text, periods_original)
    if revenue_values:
        rows.insert(0, {
            "source_label": "Revenue",
            "section": "P&L",
            "row_type": "line_item",
            "is_non_mappable": False,
            "values": revenue_values,
        })

    # Sort periods so periods[0] = best (9ME > 6ME > 3ME, most recent year)
    periods_sorted = _sort_periods_by_priority(periods_original)

    logger.info(
        "p_and_l_extracted",
        page=page_index + 1,
        periods=periods_sorted,
        row_count=len(rows),
    )

    return {"periods": periods_sorted, "rows": rows}


def _parse_p_and_l_periods(header_table: list) -> list[str]:
    if len(header_table) < 2:
        return []

    row0 = header_table[0]
    row1 = header_table[1]

    col_to_type: dict[int, tuple[str, str]] = {}
    current_type = None
    current_month_day = None

    for col_idx, cell in enumerate(row0):
        if cell and str(cell).strip():
            cell_text = str(cell).replace("\n", " ").strip()
            type_match = re.search(r"\b(3ME|6ME|9ME)\b", cell_text)
            date_match = re.search(
                r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?",
                cell_text,
                re.IGNORECASE,
            )
            if type_match:
                current_type = type_match.group(1)
            if date_match:
                current_month_day = f"{date_match.group(1).capitalize()} {date_match.group(2)},"

        if current_type and current_month_day:
            col_to_type[col_idx] = (current_type, current_month_day)

    periods = []
    for col_idx, cell in enumerate(row1):
        if cell and str(cell).strip():
            year_match = re.match(r"(20\d{2})", str(cell).strip())
            if year_match and col_idx in col_to_type:
                period_type, month_day = col_to_type[col_idx]
                period_str = f"{period_type} {month_day} {year_match.group(1)}"
                if period_str not in periods:
                    periods.append(period_str)

    return periods


def _sort_periods_by_priority(periods: list[str]) -> list[str]:
    def sort_key(p: str):
        type_match = re.match(r"(3ME|6ME|9ME)", p)
        year_match = re.search(r"(\d{4})$", p)
        ptype = type_match.group(1) if type_match else "3ME"
        year = int(year_match.group(1)) if year_match else 0
        return (PERIOD_TYPE_PRIORITY.get(ptype, 99), -year)

    return sorted(periods, key=sort_key)


def _extract_revenue_from_text(raw_text: str, periods_original: list[str]) -> dict | None:
    """Extract Revenue from raw text (pdfplumber omits it from the data table).

    periods_original must be in the same left-to-right column order as the PDF header,
    so that the N-th dollar amount maps to the N-th period.
    """
    match = re.search(
        r"\bRevenue\s+\$\s*([\d,]+)(?:\s+\$\s*([\d,]+))?(?:\s+\$\s*([\d,]+))?(?:\s+\$\s*([\d,]+))?",
        raw_text,
    )
    if not match:
        return None

    raw_values = [float(g.replace(",", "")) if g else None for g in match.groups()]
    return {
        period: (raw_values[i] if i < len(raw_values) else None)
        for i, period in enumerate(periods_original)
    }


def _parse_p_and_l_rows(data_table: list, periods: list[str]) -> list[dict]:
    rows = []
    for raw_row in data_table:
        label = _clean_label(raw_row[0]) if raw_row and raw_row[0] else ""
        if not label or label.strip() == "":
            continue

        values = _extract_p_and_l_values(raw_row)
        value_dict = {period: (values[i] if i < len(values) else None) for i, period in enumerate(periods)}

        is_total = _is_p_and_l_total(label)
        row_type = "total" if is_total else "line_item"

        rows.append({
            "source_label": label,
            "section": "P&L",
            "row_type": row_type,
            "is_non_mappable": is_total,
            "values": value_dict,
        })

    return rows


def _is_p_and_l_total(label: str) -> bool:
    label_lower = label.lower().strip().replace("\x00", "t")
    for keyword in P_AND_L_TOTAL_KEYWORDS:
        if label_lower.startswith(keyword) or label_lower == keyword:
            return True
    return False


def _clean_label(raw: str) -> str:
    if not raw:
        return ""
    label = raw.replace("\x00", "t").replace("\n", " ").strip()
    label = re.sub(r"\s{2,}", " ", label)
    for wrong, correct in OCR_WORD_FIXES.items():
        label = label.replace(wrong, correct)
    label = label.replace("â€™", "'").replace("â€˜", "'").replace("â€œ", '"').replace("â€", '"')
    return label.strip()


def _extract_p_and_l_values(raw_row: list) -> list[float | None]:
    values = []
    for cell in raw_row[1:]:
        if cell is None or cell == "" or cell == "$":
            continue
        cleaned = str(cell).replace(",", "").replace("$", "").replace("\x00", "").strip()
        if cleaned in ("", "—", "–", "-", "�"):
            values.append(None)
            continue
        match = re.match(r"^\(?([\d.]+)\)?$", cleaned)
        if match:
            num = float(match.group(1))
            if cleaned.startswith("("):
                num = -num
            values.append(num)
    return values
