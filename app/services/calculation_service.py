from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.batch import TbBatch
from app.models.batch_data import TbSampling
from app.models.calc_full import TbCalcFull
from app.models.calc_summary import TbCalcSummary
from app.models.experiment import TbExpPlan

CALC_VERSION = "v2"
ZERO = Decimal("0")
ONE = Decimal("1")
HOURS_PER_YEAR = Decimal("8760")
ONE_THOUSAND = Decimal("1000")
DISPLAY_QUANT = Decimal("0.001")


def save_calc_sample(db: Session, batch_id: str, sample_id: int, member_id: str) -> dict:
    batch = _get_batch_or_404(db, batch_id)
    sample = db.get(TbSampling, sample_id)
    if sample is None or sample.batch_id != batch_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="산출확인 기준 샘플링 데이터가 올바르지 않습니다.",
        )
    batch.calc_sample_id = sample_id
    batch.upd_id = member_id
    batch.upd_dt = datetime.now()
    db.commit()
    return {
        "message": "산출확인 기준 샘플링 데이터가 저장되었습니다.",
        "batch_id": batch_id,
        "calc_sample_id": sample_id,
    }


def get_calculation_status(db: Session, batch_id: str) -> dict:
    batch = db.get(TbBatch, batch_id)
    messages: list[str] = []
    if batch is None:
        return {
            "batch_id": batch_id,
            "has_batch": False,
            "saved_sampling_count": 0,
            "has_saved_sampling": False,
            "calc_sample_id": None,
            "has_calc_sample": False,
            "compare_batch_id": None,
            "has_compare_batch": False,
            "can_calculate": False,
            "messages": ["배치 정보를 찾을 수 없습니다."],
        }

    samplings = _get_samplings(db, batch_id)
    calc_sample = _get_calc_sample(db, batch, samplings)
    compare_batch_id = _compare_batch_id(db, batch)
    if not samplings:
        messages.append("샘플링 데이터를 먼저 저장해주세요.")
    if batch.calc_sample_id is None:
        messages.append("산출확인 기준 데이터를 선택해주세요.")
    elif calc_sample is None:
        messages.append("산출확인 기준 샘플링 데이터가 올바르지 않습니다.")
    if _missing_constants(batch):
        messages.append("산출 계산에 필요한 배치 정보가 누락되었습니다.")

    return {
        "batch_id": batch_id,
        "has_batch": True,
        "saved_sampling_count": len(samplings),
        "has_saved_sampling": bool(samplings),
        "calc_sample_id": batch.calc_sample_id,
        "has_calc_sample": calc_sample is not None,
        "compare_batch_id": compare_batch_id,
        "has_compare_batch": compare_batch_id is not None,
        "can_calculate": not messages,
        "messages": messages,
    }


def run_calculation(db: Session, batch_id: str, recalculate: bool = True) -> dict:
    batch = _get_batch_or_404(db, batch_id)
    if not recalculate and _has_calculation(db, batch_id):
        data = get_calculation(db, batch_id)
        data["message"] = "저장된 산출 계산 결과를 반환했습니다."
        return data

    status_data = get_calculation_status(db, batch_id)
    if not status_data["can_calculate"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=status_data["messages"])

    samplings = _get_samplings(db, batch_id)
    compare_rows = _calculate_compare_rows(db, batch)

    calculated_at = datetime.now()
    full_rows = _calculate_full_rows(batch, samplings)
    _apply_compare(full_rows, compare_rows)
    summary_row = _calculate_summary(batch, samplings, full_rows)
    _save_calculation(db, batch_id, full_rows, summary_row, calculated_at)
    db.commit()

    return {
        "message": "산출 계산이 완료되었습니다.",
        "batch_id": batch_id,
        "compare_batch_id": _compare_batch_id(db, batch),
        "calc_sample_id": batch.calc_sample_id,
        "calculated_at": calculated_at.isoformat(),
        "full": [_full_response(row) for row in full_rows],
        "summary": _summary_response(summary_row, batch.calc_sample_id),
    }


def get_calculation(
    db: Session,
    batch_id: str,
    include_full: bool = True,
    include_summary: bool = True,
) -> dict:
    batch = _get_batch_or_404(db, batch_id)
    full_records = []
    summary_record = None
    compare_meta_by_calc_id: dict[int, dict[str, Any]] = {}
    needs_full_records = include_full or include_summary
    if needs_full_records:
        full_records = db.scalars(
            select(TbCalcFull)
            .where(TbCalcFull.batch_id == batch_id)
            .order_by(TbCalcFull.age.asc(), TbCalcFull.sample_id.asc())
        ).all()
        compare_meta_by_calc_id = build_compare_meta_for_full_records(db, batch_id, full_records)
        sampling_time_by_sample_id = _sampling_time_by_sample_id(
            db,
            [record.sample_id for record in full_records if record.sample_id is not None],
        )
    else:
        sampling_time_by_sample_id = {}
    if include_summary:
        summary_record = db.get(TbCalcSummary, batch_id)
    summary_has_compare = any(
        record.sample_id == batch.calc_sample_id and record.calc_id in compare_meta_by_calc_id
        for record in full_records
    )

    has_result = bool(full_records) or summary_record is not None
    response = {
        "batch_id": batch_id,
        "compare_batch_id": _compare_batch_id(db, batch),
        "calc_sample_id": batch.calc_sample_id,
        "calculated_at": _calculated_at(full_records, summary_record),
        "full": [
            _full_model_response(
                row,
                compare_meta_by_calc_id.get(row.calc_id, {}),
                sampling_time_by_sample_id.get(row.sample_id),
                row.calc_id in compare_meta_by_calc_id,
            )
            for row in full_records
        ] if include_full else [],
        "summary": _summary_model_response(
            summary_record,
            batch.calc_sample_id,
            summary_has_compare,
            next(
                (
                    compare_meta_by_calc_id[record.calc_id]
                    for record in full_records
                    if record.sample_id == batch.calc_sample_id and record.calc_id in compare_meta_by_calc_id
                ),
                {},
            ),
        ) if include_summary and summary_record else None,
    }
    if not has_result:
        response["message"] = "저장된 산출 계산 결과가 없습니다."
    return response


def _get_batch_or_404(db: Session, batch_id: str) -> TbBatch:
    batch = db.get(TbBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return batch


def _get_samplings(db: Session, batch_id: str) -> list[TbSampling]:
    return db.scalars(
        select(TbSampling)
        .where(TbSampling.batch_id == batch_id)
        .order_by(TbSampling.sampling_time, TbSampling.sample_id)
    ).all()


def _get_calc_sample(db: Session, batch: TbBatch, samplings: list[TbSampling]) -> TbSampling | None:
    if batch.calc_sample_id is None:
        return None
    for sample in samplings:
        if sample.sample_id == batch.calc_sample_id:
            return sample
    return None


def resolve_compare_batch_id(db: Session, batch: TbBatch) -> str | None:
    compare_batch_ids = [batch.cmp_batch_id] if batch.cmp_batch_id else []
    if (batch.cmp_type or "").upper() == "ALL":
        plan = db.get(TbExpPlan, batch.exp_id)
        if plan and plan.cmp_batch_id:
            compare_batch_ids.append(plan.cmp_batch_id)

    for compare_batch_id in compare_batch_ids:
        if compare_batch_id == batch.batch_id:
            continue
        if db.get(TbBatch, compare_batch_id) is not None:
            return compare_batch_id
    return None


def _compare_batch_id(db: Session, batch: TbBatch) -> str | None:
    return resolve_compare_batch_id(db, batch)


def _missing_constants(batch: TbBatch) -> bool:
    required = [
        batch.prep_time,
        batch.equip_vol,
        batch.purify_yield,
        batch.dcw_od_factor,
        batch.feed_glucose_conc,
        batch.feed_density,
    ]
    return any(value is None for value in required) or batch.feed_density == ZERO or batch.equip_vol == ZERO


def _has_calculation(db: Session, batch_id: str) -> bool:
    return db.get(TbCalcSummary, batch_id) is not None or bool(
        db.scalar(select(TbCalcFull.calc_id).where(TbCalcFull.batch_id == batch_id).limit(1))
    )


def _calculate_full_rows(batch: TbBatch, samplings: list[TbSampling]) -> list[dict[str, Any]]:
    feed_weight_0 = samplings[0].feed_weight if samplings else None
    r = _divide(batch.feed_glucose_conc, batch.feed_density * ONE_THOUSAND if batch.feed_density else None)
    rows: list[dict[str, Any]] = []
    running_max_lutein: Decimal | None = None
    running_max_od: Decimal | None = None
    dcw_values: list[Decimal | None] = []
    consumed_values: list[Decimal | None] = []

    for sample in samplings:
        consumed = None
        if feed_weight_0 is not None and sample.feed_weight is not None and r is not None:
            consumed = (feed_weight_0 - sample.feed_weight) * r
        consumed_values.append(consumed)

        dcw = sample.od * batch.dcw_od_factor if sample.od is not None and batch.dcw_od_factor is not None else None
        dcw_values.append(dcw)

        production = _multiply(sample.target_prod_conc, sample.broth_volume)
        yield_pct = _multiply(_divide(production, consumed), Decimal("100"))
        runtime = sample.sampling_time + batch.prep_time if sample.sampling_time is not None and batch.prep_time is not None else None
        productivity = _divide(production, runtime)
        productivity = _multiply(productivity, HOURS_PER_YEAR)
        productivity = _divide(productivity, batch.equip_vol)
        productivity = _multiply(productivity, batch.purify_yield)
        productivity = _divide(productivity, ONE_THOUSAND)
        ts = _divide(_divide(consumed, sample.broth_volume), Decimal("10"))
        scr = _divide(_divide(consumed, sample.sampling_time), sample.broth_volume)

        previous_dcw = dcw_values[-2] if len(dcw_values) > 1 else None
        average_dcw = _divide(_add(previous_dcw, dcw), Decimal("2")) if previous_dcw is not None and dcw is not None else None
        sscr = _divide(_divide(consumed, sample.sampling_time), average_dcw)

        if sample.target_prod_conc is not None:
            running_max_lutein = sample.target_prod_conc if running_max_lutein is None else max(running_max_lutein, sample.target_prod_conc)
        if sample.od is not None:
            running_max_od = sample.od if running_max_od is None else max(running_max_od, sample.od)

        rows.append(
            {
                "sample_id": sample.sample_id,
                "_batch_id": batch.batch_id,
                "base_batch_id": batch.batch_id,
                "base_sample_id": sample.sample_id,
                "base_sampling_time": sample.sampling_time,
                "sampling_time": sample.sampling_time,
                "age": sample.sampling_time,
                "lutein": sample.target_prod_conc,
                "max_lutein": running_max_lutein,
                "production": production,
                "yield_pct": yield_pct,
                "productivity": productivity,
                "ts": ts,
                "o_i": Decimal("100"),
                "scr": scr,
                "sscr": sscr,
                "yx_s": None,
                "abs_yield_up": None,
                "prod_up": None,
                "current_od": sample.od,
                "max_od": running_max_od,
                "delta_od": _subtract(running_max_od, sample.od),
                "lycopene": sample.lycopene,
                "a_carotene": sample.a_carotene,
                "b_carotene": sample.b_carotene,
                "citric_acid": sample.citric_acid,
                "pyruvic_acid": sample.pyruvic_acid,
                "succinic_acid": sample.succinic_acid,
                "lactic_acid": sample.lactic_acid,
                "acetic_acid": sample.acetic_acid,
                "compare_batch_id": None,
                "compare_sample_id": None,
                "compare_age": None,
                "compare_sampling_time": None,
                "compare_time_diff": None,
                "matched_batch_id": None,
                "matched_sample_id": None,
                "matched_sampling_time": None,
            }
        )

    for index, row in enumerate(rows):
        next_consumed = consumed_values[index + 1] if index + 1 < len(consumed_values) else None
        row["yx_s"] = _divide(dcw_values[index], next_consumed)
    return rows


def _apply_compare(current_rows: list[dict[str, Any]], compare_rows: list[dict[str, Any]]) -> None:
    if not current_rows or not compare_rows:
        return
    last_current_row = current_rows[-1]
    last_compare_row = compare_rows[-1]
    for row in current_rows:
        compare = last_compare_row if row is last_current_row else _matched_compare_row(
            row.get("_batch_id"),
            row["age"],
            compare_rows,
        )
        if compare is None:
            continue
        _set_compare_meta(row, compare)


def build_compare_meta_for_full_records(
    db: Session,
    current_batch_id: str,
    full_records: list[Any],
) -> dict[int, dict[str, Any]]:
    current_batch = db.get(TbBatch, current_batch_id)
    if current_batch is None:
        return {}
    compare_rows = _calculate_compare_rows(db, current_batch)
    compare_meta_by_calc_id: dict[int, dict[str, Any]] = {}
    if not full_records or not compare_rows:
        return compare_meta_by_calc_id
    last_record = _last_full_record(full_records)
    last_compare_row = compare_rows[-1]
    for record in full_records:
        compare = last_compare_row if record is last_record else _matched_compare_row(current_batch_id, record.age, compare_rows)
        if compare is None:
            continue
        compare_meta_by_calc_id[record.calc_id] = {
            "compare_batch_id": compare["_batch_id"],
            "compare_sample_id": compare["sample_id"],
            "compare_age": compare["age"],
            "compare_sampling_time": compare["sampling_time"],
            "compare_time_diff": _abs_time_diff(record.age, compare["age"]),
            "matched_batch_id": compare["_batch_id"],
            "matched_sample_id": compare["sample_id"],
            "matched_sampling_time": compare["sampling_time"],
            "abs_yield_up": _divide(record.yield_pct, compare["yield_pct"]),
            "prod_up": _divide(record.productivity, compare["productivity"]),
        }
    return compare_meta_by_calc_id


def _last_full_record(full_records: list[Any]) -> Any:
    return sorted(
        full_records,
        key=lambda record: (
            record.age is not None,
            record.age or ZERO,
            record.sample_id or 0,
        ),
    )[-1]


def _matched_compare_row(
    current_batch_id: str | None,
    age: Decimal | None,
    compare_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if age is None:
        return None
    candidates = [
        compare
        for compare in compare_rows
        if compare["age"] is not None
        and compare["age"] >= age - ONE
        and compare["age"] <= age + ONE
        and compare.get("_batch_id") != current_batch_id
    ]
    return sorted(candidates, key=lambda item: (abs(item["sampling_time"] - age), item["sampling_time"], item["sample_id"] or 0))[0] if candidates else None


def _calculate_compare_rows(db: Session, current_batch: TbBatch) -> list[dict[str, Any]]:
    compare_batch_id = _compare_batch_id(db, current_batch)
    if compare_batch_id is None:
        return []
    compare_batch = db.get(TbBatch, compare_batch_id)
    if compare_batch is None:
        return []
    return _calculate_full_rows(compare_batch, _get_samplings(db, compare_batch.batch_id))


def _set_compare_meta(row: dict[str, Any], compare: dict[str, Any]) -> None:
    row["compare_batch_id"] = compare["_batch_id"]
    row["compare_sample_id"] = compare["sample_id"]
    row["compare_age"] = compare["age"]
    row["compare_sampling_time"] = compare["sampling_time"]
    row["compare_time_diff"] = _abs_time_diff(row["age"], compare["age"])
    row["matched_batch_id"] = compare["_batch_id"]
    row["matched_sample_id"] = compare["sample_id"]
    row["matched_sampling_time"] = compare["sampling_time"]
    row["abs_yield_up"] = _divide(row["yield_pct"], compare["yield_pct"])
    row["prod_up"] = _divide(row["productivity"], compare["productivity"])


def _calculate_summary(batch: TbBatch, samplings: list[TbSampling], full_rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected_full = next(row for row in full_rows if row["sample_id"] == batch.calc_sample_id)
    selected_sample = next(sample for sample in samplings if sample.sample_id == batch.calc_sample_id)
    max_lutein = _max_decimal([sample.target_prod_conc for sample in samplings])
    max_od = _max_decimal([sample.od for sample in samplings])
    return {
        "sample_id": batch.calc_sample_id,
        "age": selected_full["age"],
        "final_lutein": selected_sample.target_prod_conc,
        "max_lutein": max_lutein,
        "yield_pct": selected_full["yield_pct"],
        "productivity": selected_full["productivity"],
        "production": selected_full["production"],
        "abs_yield_up": selected_full["abs_yield_up"],
        "prod_up": selected_full["prod_up"],
        "ts": selected_full["ts"],
        "o_i": selected_full["o_i"],
        "scr": selected_full["scr"],
        "sscr": selected_full["sscr"],
        "yx_s": selected_full["yx_s"],
        "max_od": max_od,
        "fn": selected_sample.od,
        "delta_od": _subtract(max_od, selected_sample.od),
        "final_lycopene": selected_sample.lycopene,
        "final_a_carotene": selected_sample.a_carotene,
        "final_b_carotene": selected_sample.b_carotene,
        "final_citric_acid": selected_sample.citric_acid,
        "final_pyruvic_acid": selected_sample.pyruvic_acid,
        "final_succinic_acid": selected_sample.succinic_acid,
        "final_lactic_acid": selected_sample.lactic_acid,
        "final_acetic_acid": selected_sample.acetic_acid,
    }


def _save_calculation(
    db: Session,
    batch_id: str,
    full_rows: list[dict[str, Any]],
    summary_row: dict[str, Any],
    calculated_at: datetime,
) -> None:
    db.execute(delete(TbCalcFull).where(TbCalcFull.batch_id == batch_id))
    db.execute(delete(TbCalcSummary).where(TbCalcSummary.batch_id == batch_id))
    has_compare_columns = _has_calc_full_compare_columns(db)
    for row in full_rows:
        record = TbCalcFull(
            batch_id=batch_id,
            sample_id=row["sample_id"],
            age=row["age"],
            lutein=row["lutein"],
            max_lutein=row["max_lutein"],
            yield_pct=row["yield_pct"],
            productivity=row["productivity"],
            production=row["production"],
            abs_yield_up=row["abs_yield_up"],
            prod_up=row["prod_up"],
            ts=row["ts"],
            o_i=row["o_i"],
            scr=row["scr"],
            sscr=row["sscr"],
            yx_s=row["yx_s"],
            current_od=row["current_od"],
            max_od=row["max_od"],
            delta_od=row["delta_od"],
            lycopene=row["lycopene"],
            a_carotene=row["a_carotene"],
            b_carotene=row["b_carotene"],
            citric_acid=row["citric_acid"],
            pyruvic_acid=row["pyruvic_acid"],
            succinic_acid=row["succinic_acid"],
            lactic_acid=row["lactic_acid"],
            acetic_acid=row["acetic_acid"],
            calc_version=CALC_VERSION,
            calc_dt=calculated_at,
        )
        db.add(record)
        if has_compare_columns:
            db.flush()
            _update_compare_meta(db, record.calc_id, row)
    db.add(
        TbCalcSummary(
            batch_id=batch_id,
            age=summary_row["age"],
            final_lutein=summary_row["final_lutein"],
            max_lutein=summary_row["max_lutein"],
            yield_pct=summary_row["yield_pct"],
            productivity=summary_row["productivity"],
            production=summary_row["production"],
            abs_yield_up=summary_row["abs_yield_up"],
            prod_up=summary_row["prod_up"],
            ts=summary_row["ts"],
            o_i=summary_row["o_i"],
            scr=summary_row["scr"],
            sscr=summary_row["sscr"],
            yx_s=summary_row["yx_s"],
            max_od=summary_row["max_od"],
            fn=summary_row["fn"],
            delta_od=summary_row["delta_od"],
            final_lycopene=summary_row["final_lycopene"],
            final_a_carotene=summary_row["final_a_carotene"],
            final_b_carotene=summary_row["final_b_carotene"],
            final_citric=summary_row["final_citric_acid"],
            final_pyruvic=summary_row["final_pyruvic_acid"],
            final_succinic=summary_row["final_succinic_acid"],
            final_lactic=summary_row["final_lactic_acid"],
            final_acetic=summary_row["final_acetic_acid"],
            calc_version=CALC_VERSION,
            calc_dt=calculated_at,
        )
    )


def _update_compare_meta(db: Session, calc_id: int, row: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            UPDATE tb_calc_full
            SET compare_sample_id = :compare_sample_id,
                compare_age = :compare_age,
                compare_time_diff = :compare_time_diff
            WHERE calc_id = :calc_id
            """
        ),
        {
            "calc_id": calc_id,
            "compare_sample_id": row["compare_sample_id"],
            "compare_age": _sql_value(row["compare_age"]),
            "compare_time_diff": _sql_value(row["compare_time_diff"]),
        },
    )


def _sampling_time_by_sample_id(db: Session, sample_ids: list[int]) -> dict[int, Decimal]:
    if not sample_ids:
        return {}
    stmt = select(TbSampling.sample_id, TbSampling.sampling_time).where(TbSampling.sample_id.in_(sample_ids))
    return {sample_id: sampling_time for sample_id, sampling_time in db.execute(stmt).all()}


def _has_calc_full_compare_columns(db: Session) -> bool:
    try:
        dialect = db.get_bind().dialect.name
        if dialect == "sqlite":
            rows = db.execute(text("PRAGMA table_info(tb_calc_full)")).mappings().all()
            columns = {row["name"] for row in rows}
        else:
            columns = set(
                db.scalars(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'tb_calc_full'
                          AND column_name IN ('compare_sample_id', 'compare_age', 'compare_time_diff')
                        """
                    )
                ).all()
            )
        return {"compare_sample_id", "compare_age", "compare_time_diff"}.issubset(columns)
    except SQLAlchemyError:
        return False


def _full_response(row: dict[str, Any]) -> dict:
    return {key: _serialize(value) for key, value in row.items() if not key.startswith("_")}


def _summary_response(row: dict[str, Any], sample_id: int | None) -> dict:
    data = {key: _serialize(value) for key, value in row.items()}
    data["sample_id"] = sample_id
    return data


def _full_model_response(
    row: TbCalcFull,
    compare_meta: dict[str, Any],
    sampling_time: Decimal | None = None,
    include_compare: bool = True,
) -> dict:
    return {
        "sample_id": row.sample_id,
        "base_sample_id": row.sample_id,
        "sampling_time": _display_number(sampling_time),
        "base_sampling_time": _display_number(sampling_time),
        "age": _display_number(row.age),
        "lutein": _display_number(row.lutein),
        "max_lutein": _display_number(row.max_lutein),
        "production": _display_number(row.production),
        "yield_pct": _display_number(row.yield_pct),
        "productivity": _display_number(row.productivity),
        "ts": _display_number(row.ts),
        "o_i": _display_number(row.o_i),
        "scr": _display_number(row.scr),
        "sscr": _display_number(row.sscr),
        "yx_s": _display_number(row.yx_s),
        "abs_yield_up": _display_number(compare_meta.get("abs_yield_up")) if include_compare else None,
        "prod_up": _display_number(compare_meta.get("prod_up")) if include_compare else None,
        "current_od": _display_number(row.current_od),
        "max_od": _display_number(row.max_od),
        "delta_od": _display_number(row.delta_od),
        "lycopene": _display_number(row.lycopene),
        "a_carotene": _display_number(row.a_carotene),
        "b_carotene": _display_number(row.b_carotene),
        "citric_acid": _display_number(row.citric_acid),
        "pyruvic_acid": _display_number(row.pyruvic_acid),
        "succinic_acid": _display_number(row.succinic_acid),
        "lactic_acid": _display_number(row.lactic_acid),
        "acetic_acid": _display_number(row.acetic_acid),
        "compare_batch_id": compare_meta.get("compare_batch_id") if include_compare else None,
        "compare_sample_id": compare_meta.get("compare_sample_id") if include_compare else None,
        "compare_age": _display_number(compare_meta.get("compare_age")) if include_compare else None,
        "compare_sampling_time": _display_number(compare_meta.get("compare_sampling_time")) if include_compare else None,
        "compare_time_diff": _display_number(compare_meta.get("compare_time_diff")) if include_compare else None,
        "matched_batch_id": compare_meta.get("matched_batch_id") if include_compare else None,
        "matched_sample_id": compare_meta.get("matched_sample_id") if include_compare else None,
        "matched_sampling_time": _display_number(compare_meta.get("matched_sampling_time")) if include_compare else None,
    }


def _summary_model_response(
    row: TbCalcSummary,
    sample_id: int | None,
    include_compare: bool = True,
    compare_meta: dict[str, Any] | None = None,
) -> dict:
    compare_meta = compare_meta or {}
    return {
        "sample_id": sample_id,
        "age": _display_number(row.age),
        "final_lutein": _display_number(row.final_lutein),
        "max_lutein": _display_number(row.max_lutein),
        "yield_pct": _display_number(row.yield_pct),
        "productivity": _display_number(row.productivity),
        "production": _display_number(row.production),
        "ts": _display_number(row.ts),
        "o_i": _display_number(row.o_i),
        "scr": _display_number(row.scr),
        "sscr": _display_number(row.sscr),
        "yx_s": _display_number(row.yx_s),
        "abs_yield_up": _display_number(compare_meta.get("abs_yield_up")) if include_compare else None,
        "prod_up": _display_number(compare_meta.get("prod_up")) if include_compare else None,
        "max_od": _display_number(row.max_od),
        "fn": _display_number(row.fn),
        "delta_od": _display_number(row.delta_od),
        "final_lycopene": _display_number(row.final_lycopene),
        "final_a_carotene": _display_number(row.final_a_carotene),
        "final_b_carotene": _display_number(row.final_b_carotene),
        "final_citric_acid": _display_number(row.final_citric),
        "final_pyruvic_acid": _display_number(row.final_pyruvic),
        "final_succinic_acid": _display_number(row.final_succinic),
        "final_lactic_acid": _display_number(row.final_lactic),
        "final_acetic_acid": _display_number(row.final_acetic),
    }


def _calculated_at(full_records: list[TbCalcFull], summary_record: TbCalcSummary | None) -> str | None:
    if summary_record is not None and summary_record.calc_dt:
        return summary_record.calc_dt.isoformat()
    if full_records:
        return full_records[0].calc_dt.isoformat() if full_records[0].calc_dt else None
    return None


def _serialize(value):
    if value is None:
        return None
    if isinstance(value, Decimal | float):
        return _display_number(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _display_number(value: Decimal | float | int | None):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value.quantize(DISPLAY_QUANT, rounding=ROUND_HALF_UP))
    if isinstance(value, float):
        return float(Decimal(str(value)).quantize(DISPLAY_QUANT, rounding=ROUND_HALF_UP))
    return value


def _sql_value(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def _abs_time_diff(left: Decimal | None, right: Decimal | None) -> Decimal | None:
    if left is None or right is None:
        return None
    return abs(left - right)


def _multiply(left: Decimal | None, right: Decimal | None) -> Decimal | None:
    if left is None or right is None:
        return None
    return left * right


def _divide(left: Decimal | None, right: Decimal | None) -> Decimal | None:
    if left is None or right is None:
        return None
    if right == ZERO:
        return ZERO
    return left / right


def _add(left: Decimal | None, right: Decimal | None) -> Decimal | None:
    if left is None or right is None:
        return None
    return left + right


def _subtract(left: Decimal | None, right: Decimal | None) -> Decimal | None:
    if left is None or right is None:
        return None
    return left - right


def _max_decimal(values: list[Decimal | None]) -> Decimal | None:
    real_values = [value for value in values if value is not None]
    return max(real_values) if real_values else None
