from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
REPORT_TEMPLATE = "calculation_report_template_minimal.html"
CACHE_DIR = Path(tempfile.gettempdir()) / "sillicobio-font-cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))

from weasyprint import HTML  # noqa: E402


def create_result_pdf(view: dict) -> bytes:
    html = _render_result_html(view)
    return HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()


def _render_result_html(view: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(("html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(REPORT_TEMPLATE)
    return template.render(**_template_context(view))


def _template_context(view: dict) -> dict[str, Any]:
    batch = view.get("batch") or {}
    return {
        "batch_id": batch.get("batchId") or view.get("batchId"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "researchers": [_researcher_context(row) for row in view.get("researchers") or []],
        "sampling_items": [_sampling_context(row) for row in view.get("sampling") or []],
        "calc_full": [_calc_full_context(row) for row in view.get("calcFull") or []],
        "calc_summary": _calc_summary_context(view.get("calcSummary") or {}),
    }


def _researcher_context(row: dict) -> dict[str, Any]:
    return {
        "name": row.get("name"),
        "researcher_id": row.get("researcher_id") or row.get("id"),
        "role": row.get("role"),
    }


def _sampling_context(row: dict) -> dict[str, Any]:
    return {
        "is_calc_sample": row.get("isCalcSample") if "isCalcSample" in row else row.get("is_calc_sample"),
        "sampling_time": row.get("samplingTime") if "samplingTime" in row else row.get("sampling_time"),
        "od": row.get("od"),
        "feed_weight": row.get("feedWeight") if "feedWeight" in row else row.get("feed_weight"),
        "broth_volume": row.get("brothVolume") if "brothVolume" in row else row.get("broth_volume"),
        "target_prod_conc": row.get("targetProdConc") if "targetProdConc" in row else row.get("target_prod_conc"),
        "glucose_conc": row.get("glucoseConc") if "glucoseConc" in row else row.get("glucose_conc"),
        "lycopene": row.get("lycopene"),
        "a_carotene": row.get("aCarotene") if "aCarotene" in row else row.get("a_carotene"),
        "b_carotene": row.get("bCarotene") if "bCarotene" in row else row.get("b_carotene"),
        "citric_acid": row.get("citricAcid") if "citricAcid" in row else row.get("citric_acid"),
        "pyruvic_acid": row.get("pyruvicAcid") if "pyruvicAcid" in row else row.get("pyruvic_acid"),
        "succinic_acid": row.get("succinicAcid") if "succinicAcid" in row else row.get("succinic_acid"),
        "lactic_acid": row.get("lacticAcid") if "lacticAcid" in row else row.get("lactic_acid"),
        "acetic_acid": row.get("aceticAcid") if "aceticAcid" in row else row.get("acetic_acid"),
    }


def _calc_full_context(row: dict) -> dict[str, Any]:
    data = dict(row)
    data["age"] = row.get("sampling_time") if row.get("sampling_time") is not None else row.get("age")
    data["compare_age"] = (
        row.get("compare_sampling_time")
        if row.get("compare_sampling_time") is not None
        else row.get("compare_age")
    )
    return data


def _calc_summary_context(row: dict) -> dict[str, Any]:
    if not row:
        return {}
    data = dict(row)
    data["compare_age"] = (
        row.get("compare_sampling_time")
        if row.get("compare_sampling_time") is not None
        else row.get("compare_age")
    )
    return data


def _safe_filename(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)
    return safe or "batch"
