from __future__ import annotations

import os
import tempfile
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
REPORT_TEMPLATE = "calculation_report_template_minimal.html"
CALC_VIEW_TEMPLATE = "calc_view_template.html"
CACHE_DIR = Path(tempfile.gettempdir()) / "sillicobio-font-cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))
PDF_NUMBER_QUANT = Decimal("0.001")


def create_result_pdf(view: dict) -> bytes:
    html = _render_result_html(view)
    return _write_pdf(html)


def create_calc_view_pdf(view: dict) -> bytes:
    html = _render_calc_view_html(view)
    return _write_pdf(html)


def _write_pdf(html: str) -> bytes:
    try:
        from weasyprint import HTML
    except Exception as exc:
        raise RuntimeError(
            "PDF 렌더링 의존성이 설치되지 않았거나 서버 OS 라이브러리가 부족합니다. "
            "`pip install -r requirements.txt` 적용 후 WeasyPrint 시스템 의존성을 확인하세요."
        ) from exc
    return HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()


def _render_result_html(view: dict) -> str:
    return _render_html(view, REPORT_TEMPLATE)


def _render_calc_view_html(view: dict) -> str:
    return _render_html(view, CALC_VIEW_TEMPLATE)


def _render_html(view: dict, template_name: str) -> str:
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except Exception as exc:
        raise RuntimeError(
            "PDF 템플릿 렌더링 의존성 Jinja2가 설치되지 않았습니다. "
            "`pip install -r requirements.txt`를 적용하세요."
        ) from exc

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(("html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)
    return template.render(**_template_context(view))


def _template_context(view: dict) -> dict[str, Any]:
    batch = view.get("batch") or {}
    comparison = batch.get("comparison") or {}
    compare_batch_id = view.get("compareBatchId") or comparison.get("targetBatchId")
    return {
        "batch_id": batch.get("batchId") or view.get("batchId"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "batch_info": _batch_info_context(view),
        "cmp_label": "비교 배치 ID" if compare_batch_id else "비교 배치",
        "cmp_value": compare_batch_id or "선택 없음",
        "cmp_batch_id": compare_batch_id,
        "cmp_sampling_items": [_sampling_context(row) for row in view.get("compareSampling") or []],
        "researchers": [_researcher_context(row) for row in view.get("researchers") or []],
        "files": _files_context(view.get("files") or batch.get("files") or {}),
        "sampling_items": [_sampling_context(row) for row in view.get("sampling") or []],
        "calc_full": [_calc_full_context(row) for row in view.get("calcFull") or []],
        "calc_summary": _calc_summary_context(view.get("calcSummary") or {}),
    }


def _batch_info_context(view: dict) -> dict[str, Any]:
    batch = view.get("batch") or {}
    plan = view.get("plan") or {}
    params = batch.get("params") or {}
    return {
        "start_dt": batch.get("startDt"),
        "purpose": plan.get("purpose") or batch.get("purpose"),
        "strain": plan.get("strain"),
        "prep_time": _pdf_value(params.get("prepTime")),
        "equip_vol": _pdf_value(params.get("equipVol")),
        "purify_yield": _pdf_value(params.get("purifyYield")),
        "dcw_od_factor": _pdf_value(params.get("dcwOdFactor")),
        "feed_glucose_conc": _pdf_value(params.get("feedGlucoseConc")),
        "feed_density": _pdf_value(params.get("feedDensity")),
        "feed_ggf": _pdf_value(params.get("feedGlucosePerFeed")),
    }


def _files_context(files: dict) -> dict[str, Any]:
    def file_name(key: str) -> str | None:
        value = files.get(key)
        if isinstance(value, dict):
            return value.get("fileName")
        return value

    return {
        "do_ph": file_name("doPh"),
        "co2o2": file_name("co2O2"),
        "ref": file_name("ref"),
        "trend_csv": file_name("trendCsv"),
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
        "sampling_time": _pdf_value(row.get("samplingTime") if "samplingTime" in row else row.get("sampling_time")),
        "od": _pdf_value(row.get("od")),
        "feed_weight": _pdf_value(row.get("feedWeight") if "feedWeight" in row else row.get("feed_weight")),
        "broth_volume": _pdf_value(row.get("brothVolume") if "brothVolume" in row else row.get("broth_volume")),
        "target_prod_conc": _pdf_value(row.get("targetProdConc") if "targetProdConc" in row else row.get("target_prod_conc")),
        "glucose_conc": _pdf_value(row.get("glucoseConc") if "glucoseConc" in row else row.get("glucose_conc")),
        "lycopene": _pdf_value(row.get("lycopene")),
        "a_carotene": _pdf_value(row.get("aCarotene") if "aCarotene" in row else row.get("a_carotene")),
        "b_carotene": _pdf_value(row.get("bCarotene") if "bCarotene" in row else row.get("b_carotene")),
        "citric_acid": _pdf_value(row.get("citricAcid") if "citricAcid" in row else row.get("citric_acid")),
        "pyruvic_acid": _pdf_value(row.get("pyruvicAcid") if "pyruvicAcid" in row else row.get("pyruvic_acid")),
        "succinic_acid": _pdf_value(row.get("succinicAcid") if "succinicAcid" in row else row.get("succinic_acid")),
        "lactic_acid": _pdf_value(row.get("lacticAcid") if "lacticAcid" in row else row.get("lactic_acid")),
        "acetic_acid": _pdf_value(row.get("aceticAcid") if "aceticAcid" in row else row.get("acetic_acid")),
    }


def _calc_full_context(row: dict) -> dict[str, Any]:
    data = {key: _pdf_value(value) for key, value in row.items()}
    data["age"] = row.get("sampling_time") if row.get("sampling_time") is not None else row.get("age")
    data["sampling_time"] = row.get("sampling_time") if row.get("sampling_time") is not None else row.get("age")
    data["compare_age"] = (
        row.get("compare_sampling_time")
        if row.get("compare_sampling_time") is not None
        else row.get("compare_age")
    )
    return {key: _pdf_value(value) for key, value in data.items()}


def _calc_summary_context(row: dict) -> dict[str, Any]:
    if not row:
        return {}
    data = {key: _pdf_value(value) for key, value in row.items()}
    data["compare_age"] = (
        row.get("compare_sampling_time")
        if row.get("compare_sampling_time") is not None
        else row.get("compare_age")
    )
    data["sampling_time"] = row.get("sampling_time") if row.get("sampling_time") is not None else row.get("age")
    data["compare_sampling_time"] = (
        row.get("compare_sampling_time")
        if row.get("compare_sampling_time") is not None
        else row.get("compare_age")
    )
    data["lutein"] = row.get("final_lutein") if row.get("final_lutein") is not None else row.get("lutein")
    data["current_od"] = row.get("fn") if row.get("fn") is not None else row.get("current_od")
    data["lycopene"] = row.get("final_lycopene") if row.get("final_lycopene") is not None else row.get("lycopene")
    data["a_carotene"] = (
        row.get("final_a_carotene") if row.get("final_a_carotene") is not None else row.get("a_carotene")
    )
    data["b_carotene"] = (
        row.get("final_b_carotene") if row.get("final_b_carotene") is not None else row.get("b_carotene")
    )
    data["citric_acid"] = (
        row.get("final_citric_acid") if row.get("final_citric_acid") is not None else row.get("citric_acid")
    )
    data["pyruvic_acid"] = (
        row.get("final_pyruvic_acid") if row.get("final_pyruvic_acid") is not None else row.get("pyruvic_acid")
    )
    data["succinic_acid"] = (
        row.get("final_succinic_acid") if row.get("final_succinic_acid") is not None else row.get("succinic_acid")
    )
    data["lactic_acid"] = (
        row.get("final_lactic_acid") if row.get("final_lactic_acid") is not None else row.get("lactic_acid")
    )
    data["acetic_acid"] = (
        row.get("final_acetic_acid") if row.get("final_acetic_acid") is not None else row.get("acetic_acid")
    )
    return {key: _pdf_value(value) for key, value in data.items()}


def _pdf_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int | float | Decimal):
        try:
            rounded = Decimal(str(value)).quantize(PDF_NUMBER_QUANT, rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            return value
        return f"{rounded:.3f}"
    return value


def _safe_filename(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)
    return safe or "batch"
