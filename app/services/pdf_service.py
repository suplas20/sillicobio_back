from __future__ import annotations

from datetime import datetime
from io import BytesIO


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 42
MARGIN_TOP = 42
MARGIN_BOTTOM = 42
DEFAULT_SIZE = 9
TITLE_SIZE = 15
SECTION_SIZE = 12
LINE_GAP = 4


def create_result_pdf(view: dict) -> bytes:
    lines = _result_lines(view)
    pages = _paginate(lines)
    objects: list[bytes] = []

    def add(obj: str | bytes) -> int:
        objects.append(obj.encode("latin-1") if isinstance(obj, str) else obj)
        return len(objects)

    catalog_id = add("<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add(b"")
    font_id = add(
        "<< /Type /Font /Subtype /Type0 /BaseFont /HYGoThic-Medium "
        "/Encoding /UniKS-UCS2-H /DescendantFonts [4 0 R] >>"
    )
    cid_font_id = add(
        "<< /Type /Font /Subtype /CIDFontType0 /BaseFont /HYGoThic-Medium "
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (Korea1) /Supplement 2 >> >>"
    )
    assert catalog_id == 1
    assert pages_id == 2
    assert font_id == 3
    assert cid_font_id == 4

    page_ids: list[int] = []
    for page_lines in pages:
        content = _page_content(page_lines)
        content_id = add(f"<< /Length {len(content)} >>\nstream\n".encode("latin-1") + content + b"\nendstream")
        page_id = add(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("latin-1")

    output = BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{idx} 0 obj\n".encode("latin-1"))
        output.write(obj)
        output.write(b"\nendobj\n")
    xref_offset = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
    output.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
    )
    return output.getvalue()


def _result_lines(view: dict) -> list[tuple[str, int]]:
    batch = view.get("batch") or {}
    plan = view.get("plan") or {}
    researchers = view.get("researchers") or []
    sampling = view.get("sampling") or []
    calc_full = view.get("calcFull") or []
    calc_summary = view.get("calcSummary") or {}
    batch_id = batch.get("batchId") or "-"

    lines: list[tuple[str, int]] = [
        (f"Batch Result Report - {batch_id}", TITLE_SIZE),
        (f"Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", DEFAULT_SIZE),
        ("", DEFAULT_SIZE),
        ("Batch Information", SECTION_SIZE),
        (_kv("Batch ID", batch.get("batchId")), DEFAULT_SIZE),
        (_kv("Plan ID", batch.get("planId") or plan.get("id")), DEFAULT_SIZE),
        (_kv("Purpose", batch.get("purpose") or plan.get("purpose")), DEFAULT_SIZE),
        (_kv("Start Date", batch.get("startDt")), DEFAULT_SIZE),
        (_kv("Calc Sample ID", batch.get("calcSampleId")), DEFAULT_SIZE),
        ("", DEFAULT_SIZE),
        ("Researchers", SECTION_SIZE),
    ]
    if researchers:
        lines.extend(_table(["Role", "ID", "Name"], [[r.get("role"), r.get("id"), r.get("name")] for r in researchers]))
    else:
        lines.append(("No researchers", DEFAULT_SIZE))

    lines.extend(
        [
            ("", DEFAULT_SIZE),
            ("Sampling Data", SECTION_SIZE),
        ]
    )
    sampling_headers = ["Time", "OD", "Feed Wt", "Broth Vol", "Prod Conc", "Glucose", "Lycopene"]
    sampling_rows = [
        [
            row.get("samplingTime"),
            row.get("od"),
            row.get("feedWeight"),
            row.get("brothVolume"),
            row.get("targetProdConc"),
            row.get("glucoseConc"),
            row.get("lycopene"),
        ]
        for row in sampling
    ]
    lines.extend(_table(sampling_headers, sampling_rows) if sampling_rows else [("No sampling data", DEFAULT_SIZE)])

    lines.extend(
        [
            ("", DEFAULT_SIZE),
            ("Extraction Full", SECTION_SIZE),
        ]
    )
    full_headers = ["Time", "Cmp Time", "Lutein", "Max Lut", "Yield", "Prod.", "TS", "O/I", "SCR", "SSCR", "Yx/s"]
    full_rows = [
        [
            row.get("sampling_time") if "sampling_time" in row else row.get("age"),
            row.get("compare_sampling_time"),
            row.get("lutein"),
            row.get("max_lutein"),
            row.get("yield_pct"),
            row.get("productivity"),
            row.get("ts"),
            row.get("o_i"),
            row.get("scr"),
            row.get("sscr"),
            row.get("yx_s"),
        ]
        for row in calc_full
    ]
    lines.extend(_table(full_headers, full_rows) if full_rows else [("No extraction full data", DEFAULT_SIZE)])

    lines.extend(
        [
            ("", DEFAULT_SIZE),
            ("Extraction Summary", SECTION_SIZE),
        ]
    )
    summary_items = [
        ("Age", calc_summary.get("age")),
        ("Final Lutein", calc_summary.get("final_lutein")),
        ("Max Lutein", calc_summary.get("max_lutein")),
        ("Yield", calc_summary.get("yield_pct")),
        ("Productivity", calc_summary.get("productivity")),
        ("Production", calc_summary.get("production")),
        ("TS", calc_summary.get("ts")),
        ("O/I", calc_summary.get("o_i")),
        ("SCR", calc_summary.get("scr")),
        ("SSCR", calc_summary.get("sscr")),
        ("Yx/s", calc_summary.get("yx_s")),
        ("Max OD", calc_summary.get("max_od")),
        ("FN", calc_summary.get("fn")),
        ("Delta OD", calc_summary.get("delta_od")),
        ("Final Lycopene", calc_summary.get("final_lycopene")),
    ]
    lines.extend(_table(["Metric", "Value"], summary_items) if calc_summary else [("No extraction summary data", DEFAULT_SIZE)])
    return lines


def _table(headers: list[str], rows: list[list | tuple]) -> list[tuple[str, int]]:
    output = [(" | ".join(headers), DEFAULT_SIZE), ("-" * min(110, len(" | ".join(headers)) + 8), DEFAULT_SIZE)]
    for row in rows:
        text = " | ".join(_fmt(value) for value in row)
        output.extend((line, DEFAULT_SIZE) for line in _wrap(text, 112))
    return output


def _paginate(lines: list[tuple[str, int]]) -> list[list[tuple[str, int]]]:
    pages: list[list[tuple[str, int]]] = []
    page: list[tuple[str, int]] = []
    y = PAGE_HEIGHT - MARGIN_TOP
    for text, size in lines:
        height = size + LINE_GAP
        if y - height < MARGIN_BOTTOM and page:
            pages.append(page)
            page = []
            y = PAGE_HEIGHT - MARGIN_TOP
        page.append((text, size))
        y -= height
    if page:
        pages.append(page)
    return pages or [[("No data", DEFAULT_SIZE)]]


def _page_content(lines: list[tuple[str, int]]) -> bytes:
    content: list[str] = ["BT", f"{MARGIN_X} {PAGE_HEIGHT - MARGIN_TOP} Td"]
    current_size = None
    first = True
    for text, size in lines:
        if current_size != size:
            content.append(f"/F1 {size} Tf")
            current_size = size
        if not first:
            content.append(f"0 -{size + LINE_GAP} Td")
        content.append(f"<{_hex_text(text)}> Tj")
        first = False
    content.append("ET")
    return "\n".join(content).encode("latin-1")


def _hex_text(text: str) -> str:
    return text.encode("utf-16-be", errors="replace").hex().upper()


def _kv(label: str, value) -> str:
    return f"{label}: {_fmt(value)}"


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _wrap(text: str, width: int) -> list[str]:
    if len(text) <= width:
        return [text]
    return [text[index : index + width] for index in range(0, len(text), width)]


def _safe_filename(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)
    return safe or "batch"
