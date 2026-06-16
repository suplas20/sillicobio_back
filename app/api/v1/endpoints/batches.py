from datetime import datetime
from pathlib import Path
from shutil import copyfileobj

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import bindparam, case, delete, func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import CurrentMember, DbSession
from app.core.config import settings
from app.models.batch import TbBatch
from app.models.batch_data import TbSampling
from app.models.batch_file import TbBatchFile
from app.models.batch_researcher import TbBatchResearcher
from app.models.best_batch import TbBestBatch
from app.models.calc_full import TbCalcFull
from app.models.calc_summary import TbCalcSummary
from app.models.experiment import TbExpPlan
from app.models.researcher import TbResearcher
from app.schemas.api_schema import (
    BatchDetailSaveRequest,
    CalcSampleSaveRequest,
    CalculationRunRequest,
    CompareBatchSaveRequest,
    SamplingSaveRequest,
)
from app.services.calculation_service import (
    build_compare_meta_for_full_records,
    get_calculation,
    get_calculation_status,
    run_calculation,
    save_calc_sample,
)
from app.utils.formatters import number, yyyymmdd


router = APIRouter()


@router.get("")
def list_batches(
    db: DbSession,
    _: CurrentMember,
    planId: str | None = None,
    batchId: str | None = None,
    purpose: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
) -> dict:
    stmt = select(TbBatch, TbExpPlan).join(TbExpPlan, TbExpPlan.exp_id == TbBatch.exp_id)
    count_stmt = select(func.count()).select_from(TbBatch).join(TbExpPlan, TbExpPlan.exp_id == TbBatch.exp_id)
    if planId:
        stmt = stmt.where(TbBatch.exp_id.ilike(f"%{planId}%"))
        count_stmt = count_stmt.where(TbBatch.exp_id.ilike(f"%{planId}%"))
    if batchId:
        stmt = stmt.where(TbBatch.batch_id.ilike(f"%{batchId}%"))
        count_stmt = count_stmt.where(TbBatch.batch_id.ilike(f"%{batchId}%"))
    if purpose:
        stmt = stmt.where(TbExpPlan.purpose.ilike(f"%{purpose}%"))
        count_stmt = count_stmt.where(TbExpPlan.purpose.ilike(f"%{purpose}%"))
    total = db.scalar(count_stmt) or 0
    rows = db.execute(stmt.order_by(TbBatch.batch_id).offset((page - 1) * size).limit(size)).all()
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "planId": batch.exp_id,
                "purpose": plan.purpose,
                "batchId": batch.batch_id,
                "created": yyyymmdd(batch.reg_dt),
            }
            for batch, plan in rows
        ],
    }


@router.get("/options")
def batch_options(
    db: DbSession,
    _: CurrentMember,
    excludeBatchId: str | None = None,
    keyword: str | None = None,
) -> dict:
    stmt = select(TbBatch, TbExpPlan).join(TbExpPlan, TbExpPlan.exp_id == TbBatch.exp_id)
    if excludeBatchId:
        stmt = stmt.where(TbBatch.batch_id != excludeBatchId)
    if keyword:
        stmt = stmt.where((TbBatch.batch_id.ilike(f"%{keyword}%")) | (TbExpPlan.purpose.ilike(f"%{keyword}%")))
    rows = db.execute(stmt.order_by(TbBatch.batch_id)).all()

    batch_ids = [b.batch_id for b, _ in rows]
    sampling_map: dict[str, TbSampling] = {}
    if batch_ids:
        max_st_sub = (
            select(TbSampling.batch_id, func.max(TbSampling.sampling_time).label("max_st"))
            .where(TbSampling.batch_id.in_(batch_ids))
            .group_by(TbSampling.batch_id)
            .subquery()
        )
        max_sid_sub = (
            select(TbSampling.batch_id, func.max(TbSampling.sample_id).label("max_sid"))
            .join(
                max_st_sub,
                (TbSampling.batch_id == max_st_sub.c.batch_id)
                & (TbSampling.sampling_time == max_st_sub.c.max_st),
            )
            .group_by(TbSampling.batch_id)
            .subquery()
        )
        s_rows = db.scalars(
            select(TbSampling).join(max_sid_sub, TbSampling.sample_id == max_sid_sub.c.max_sid)
        ).all()
        for s in s_rows:
            sampling_map[s.batch_id] = s

    def to_item(batch: TbBatch, plan: TbExpPlan) -> dict:
        s = sampling_map.get(batch.batch_id)
        return {
            "batchId": batch.batch_id,
            "planId": batch.exp_id,
            "purpose": plan.purpose,
            "lastSampledAt": s.reg_dt.strftime("%Y-%m-%d %H:%M") if s and s.reg_dt else None,
            "samplingTime": number(s.sampling_time) if s else None,
            "od": number(s.od) if s else None,
            "feedWeight": number(s.feed_weight) if s else None,
            "brothVolume": number(s.broth_volume) if s else None,
            "targetProdConc": number(s.target_prod_conc) if s else None,
            "glucoseConc": number(s.glucose_conc) if s else None,
            "lycopene": number(s.lycopene) if s else None,
            "aCarotene": number(s.a_carotene) if s else None,
            "bCarotene": number(s.b_carotene) if s else None,
            "citricAcid": number(s.citric_acid) if s else None,
            "pyruvicAcid": number(s.pyruvic_acid) if s else None,
            "succinicAcid": number(s.succinic_acid) if s else None,
            "lacticAcid": number(s.lactic_acid) if s else None,
            "aceticAcid": number(s.acetic_acid) if s else None,
        }

    return {"items": [to_item(b, p) for b, p in rows]}


@router.get("/search")
def search_batches(
    db: DbSession,
    _: CurrentMember,
    keyword: str | None = None,
    sort_field: str = "sampling_time",
    sort_order: str = "desc",
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
) -> dict:
    last_sampling = (
        select(
            TbSampling.batch_id.label("batch_id"),
            TbSampling.reg_dt.label("last_sampled_at"),
            TbSampling.sampling_time.label("sampling_time"),
            TbSampling.od.label("od"),
            TbSampling.feed_weight.label("feed_weight"),
            TbSampling.broth_volume.label("broth_volume"),
            TbSampling.target_prod_conc.label("target_prod_conc"),
            TbSampling.glucose_conc.label("glucose_conc"),
            TbSampling.lycopene.label("lycopene"),
            TbSampling.a_carotene.label("a_carotene"),
            TbSampling.b_carotene.label("b_carotene"),
            TbSampling.citric_acid.label("citric_acid"),
            TbSampling.pyruvic_acid.label("pyruvic_acid"),
            TbSampling.succinic_acid.label("succinic_acid"),
            TbSampling.lactic_acid.label("lactic_acid"),
            TbSampling.acetic_acid.label("acetic_acid"),
            func.row_number()
            .over(
                partition_by=TbSampling.batch_id,
                order_by=(TbSampling.sampling_time.desc(), TbSampling.sample_id.desc()),
            )
            .label("rn"),
        )
        .subquery()
    )
    best_batch = (
        select(
            TbBestBatch.batch_id.label("batch_id"),
            func.min(TbBestBatch.sort_ord).label("sort_ord"),
            func.min(TbBestBatch.reg_dt).label("best_reg_dt"),
        )
        .group_by(TbBestBatch.batch_id)
        .subquery()
    )

    sort_columns = {
        "batch_id": TbBatch.batch_id,
        "last_sampled_at": last_sampling.c.last_sampled_at,
        "sampling_time": last_sampling.c.sampling_time,
        "od": last_sampling.c.od,
        "feed_weight": last_sampling.c.feed_weight,
        "broth_volume": last_sampling.c.broth_volume,
        "target_prod_conc": last_sampling.c.target_prod_conc,
        "glucose_conc": last_sampling.c.glucose_conc,
        "lycopene": last_sampling.c.lycopene,
        "a_carotene": last_sampling.c.a_carotene,
        "b_carotene": last_sampling.c.b_carotene,
        "citric_acid": last_sampling.c.citric_acid,
        "pyruvic_acid": last_sampling.c.pyruvic_acid,
        "succinic_acid": last_sampling.c.succinic_acid,
        "lactic_acid": last_sampling.c.lactic_acid,
        "acetic_acid": last_sampling.c.acetic_acid,
    }
    if sort_field not in sort_columns:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid sort_field")
    sort_order = sort_order.lower()
    if sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid sort_order")

    filters = []
    if keyword:
        filters.append(TbBatch.batch_id.ilike(f"%{keyword}%"))

    count_stmt = select(func.count()).select_from(TbBatch)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total_count = db.scalar(count_stmt) or 0

    sort_column = sort_columns[sort_field]
    sort_expr = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    stmt = (
        select(
            TbBatch.batch_id.label("batch_id"),
            TbBatch.exp_id.label("exp_id"),
            TbBatch.batch_no.label("batch_no"),
            last_sampling.c.last_sampled_at,
            last_sampling.c.sampling_time,
            last_sampling.c.od,
            last_sampling.c.feed_weight,
            last_sampling.c.broth_volume,
            last_sampling.c.target_prod_conc,
            last_sampling.c.glucose_conc,
            last_sampling.c.lycopene,
            last_sampling.c.a_carotene,
            last_sampling.c.b_carotene,
            last_sampling.c.citric_acid,
            last_sampling.c.pyruvic_acid,
            last_sampling.c.succinic_acid,
            last_sampling.c.lactic_acid,
            last_sampling.c.acetic_acid,
            case((best_batch.c.batch_id.is_not(None), True), else_=False).label("is_best"),
        )
        .outerjoin(last_sampling, (TbBatch.batch_id == last_sampling.c.batch_id) & (last_sampling.c.rn == 1))
        .outerjoin(best_batch, TbBatch.batch_id == best_batch.c.batch_id)
        .order_by(
            case((best_batch.c.batch_id.is_not(None), 0), else_=1),
            best_batch.c.sort_ord.asc().nullslast(),
            best_batch.c.best_reg_dt.desc().nullslast(),
            sort_expr.nullslast(),
            TbBatch.batch_id.asc(),
        )
        .offset((page - 1) * limit)
        .limit(limit)
    )
    if filters:
        stmt = stmt.where(*filters)

    rows = db.execute(stmt).mappings().all()
    return {
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "items": [_batch_search_response(row) for row in rows],
    }


@router.put("/{batch_id}/compare-batch")
def save_compare_batch(
    batch_id: str,
    payload: CompareBatchSaveRequest,
    db: DbSession,
    member: CurrentMember,
) -> dict:
    batch = db.get(TbBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if db.get(TbBatch, payload.cmp_batch_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if payload.cmp_batch_id == batch_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="자기 배치는 비교배치로 선택할 수 없습니다.")

    batch.cmp_type = "BATCH"
    batch.cmp_batch_id = payload.cmp_batch_id
    batch.upd_id = member.member_id
    batch.upd_dt = datetime.now()
    db.commit()
    return {
        "message": "비교배치가 저장되었습니다.",
        "batch": {
            "batch_id": batch.batch_id,
            "cmp_type": batch.cmp_type,
            "cmp_batch_id": batch.cmp_batch_id,
        },
    }


@router.get("/{batch_id}/compare-batch")
def get_compare_batch(batch_id: str, db: DbSession, _: CurrentMember) -> dict:
    batch = db.get(TbBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    cmp_batch_id = _batch_compare_batch_id(db, batch)
    cmp_batch = db.get(TbBatch, cmp_batch_id) if cmp_batch_id else None
    return {
        "batch_id": batch.batch_id,
        "cmp_type": batch.cmp_type,
        "cmp_batch_id": cmp_batch_id,
        "cmp_batch_name": cmp_batch.batch_id if cmp_batch else None,
    }


@router.put("/{batch_id}/calc-sample")
def update_calc_sample(
    batch_id: str,
    payload: CalcSampleSaveRequest,
    db: DbSession,
    member: CurrentMember,
) -> dict:
    response = save_calc_sample(db, batch_id, payload.sample_id, member.member_id)
    sample = db.get(TbSampling, payload.sample_id)
    response["calcSample"] = _sampling_response(sample, payload.sample_id) if sample else None
    return response


@router.get("/{batch_id}/calc-sample")
def get_calc_sample(batch_id: str, db: DbSession, _: CurrentMember) -> dict:
    batch = db.get(TbBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    sample = db.get(TbSampling, batch.calc_sample_id) if batch.calc_sample_id else None
    if sample is not None and sample.batch_id != batch_id:
        sample = None
    return {
        "batchId": batch.batch_id,
        "calcSampleId": batch.calc_sample_id if sample else None,
        "hasCalcSample": sample is not None,
        "calcSample": _sampling_response(sample, batch.calc_sample_id) if sample else None,
    }


@router.post("/{batch_id}/calculation/run")
def run_batch_calculation(
    batch_id: str,
    payload: CalculationRunRequest,
    db: DbSession,
    _: CurrentMember,
) -> dict:
    return run_calculation(db, batch_id, payload.recalculate)


@router.get("/{batch_id}/calculation")
def get_batch_calculation(
    batch_id: str,
    db: DbSession,
    _: CurrentMember,
    include_full: bool = True,
    include_summary: bool = True,
) -> dict:
    return get_calculation(db, batch_id, include_full, include_summary)


@router.get("/{batch_id}/calculation/status")
def get_batch_calculation_status(batch_id: str, db: DbSession, _: CurrentMember) -> dict:
    return get_calculation_status(db, batch_id)


@router.get("/{batch_id}")
def get_batch(batch_id: str, db: DbSession, _: CurrentMember) -> dict:
    batch = db.get(TbBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _batch_detail_response(db, batch)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_batch() -> None:
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)


@router.put("/{batch_id}")
def update_batch(batch_id: str) -> None:
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)


@router.put("/{batch_id}/detail")
def update_batch_detail(
    batch_id: str,
    payload: BatchDetailSaveRequest,
    db: DbSession,
    member: CurrentMember,
) -> dict:
    batch = db.get(TbBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if payload.comparison.targetBatchId and payload.comparison.targetBatchId == batch_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="자기 배치는 비교배치로 선택할 수 없습니다.")
    if payload.startDt:
        batch.start_dt = _parse_date(payload.startDt, "startDt").date()
    batch.prep_time = payload.params.prepTime
    batch.equip_vol = payload.params.equipVol
    batch.purify_yield = payload.params.purifyYield
    batch.dcw_od_factor = payload.params.dcwOdFactor
    batch.feed_glucose_conc = payload.params.feedGlucoseConc
    batch.feed_density = payload.params.feedDensity
    batch.cmp_type = payload.comparison.type
    batch.cmp_batch_id = payload.comparison.targetBatchId
    batch.upd_dt = datetime.now()
    batch.upd_id = member.member_id

    db.execute(delete(TbBatchResearcher).where(TbBatchResearcher.batch_id == batch_id))
    for row in payload.researchers:
        db.add(
            TbBatchResearcher(
                batch_id=batch_id,
                researcher_id=row.id,
                researcher_role=row.role,
                reg_dt=datetime.now(),
                reg_id=member.member_id,
            )
        )
    if payload.samplingRows:
        _replace_sampling(db, batch_id, payload.samplingRows, member.member_id)
    db.commit()
    return {"batchId": batch_id, "message": "배치정보가 저장되었습니다."}


@router.get("/{batch_id}/sampling")
def get_sampling(batch_id: str, db: DbSession, _: CurrentMember) -> dict:
    batch = db.get(TbBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    rows = db.scalars(
        select(TbSampling).where(TbSampling.batch_id == batch_id).order_by(TbSampling.sampling_time)
    ).all()
    return {
        "batchId": batch_id,
        "calcSampleId": batch.calc_sample_id,
        "columns": SAMPLING_COLUMNS,
        "rows": [_sampling_response(row, batch.calc_sample_id) for row in rows],
    }


@router.put("/{batch_id}/sampling")
def save_sampling(batch_id: str, payload: SamplingSaveRequest, db: DbSession, member: CurrentMember) -> dict:
    if db.get(TbBatch, batch_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    _replace_sampling(db, batch_id, payload.rows, member.member_id)
    db.commit()
    return {"batchId": batch_id, "message": "샘플링 데이터가 저장되었습니다.", "recalculated": True}


@router.delete("/{batch_id}/sampling", status_code=status.HTTP_204_NO_CONTENT)
def delete_sampling(batch_id: str, db: DbSession, _: CurrentMember) -> None:
    batch = db.get(TbBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    batch.calc_sample_id = None
    sample_ids = db.scalars(select(TbSampling.sample_id).where(TbSampling.batch_id == batch_id)).all()
    _clear_compare_sampling_refs(db, sample_ids)
    db.execute(delete(TbCalcFull).where(TbCalcFull.batch_id == batch_id))
    db.execute(delete(TbCalcSummary).where(TbCalcSummary.batch_id == batch_id))
    db.execute(delete(TbSampling).where(TbSampling.batch_id == batch_id))
    db.commit()


@router.delete("/{batch_id}/sampling/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sampling_row(batch_id: str, sample_id: int, db: DbSession, _: CurrentMember) -> None:
    row = db.get(TbSampling, sample_id)
    if row is None or row.batch_id != batch_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    batch = db.get(TbBatch, batch_id)
    if batch and batch.calc_sample_id == sample_id:
        batch.calc_sample_id = None
    _clear_compare_sampling_refs(db, [sample_id])
    db.execute(delete(TbCalcFull).where(TbCalcFull.sample_id == sample_id))
    db.execute(delete(TbCalcSummary).where(TbCalcSummary.batch_id == batch_id))
    db.delete(row)
    db.commit()


@router.get("/{batch_id}/calc")
def get_calc(batch_id: str, db: DbSession, _: CurrentMember) -> dict:
    batch = db.get(TbBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    full = db.scalars(select(TbCalcFull).where(TbCalcFull.batch_id == batch_id).order_by(TbCalcFull.age)).all()
    compare_meta_by_calc_id = build_compare_meta_for_full_records(
        db,
        batch_id,
        full,
    )
    sampling_time_by_sample_id = _calc_sampling_time_by_sample_id(
        db,
        [row.sample_id for row in full if row.sample_id is not None],
    )
    summary = db.get(TbCalcSummary, batch_id)
    summary_has_compare = any(
        row.sample_id == batch.calc_sample_id and row.calc_id in compare_meta_by_calc_id
        for row in full
    )
    return {
        "batchId": batch_id,
        "full": [
            _calc_full_response(
                row,
                compare_meta_by_calc_id.get(row.calc_id, {}),
                sampling_time_by_sample_id.get(row.sample_id),
                row.calc_id in compare_meta_by_calc_id,
            )
            for row in full
        ],
        "summary": _calc_summary_response(
            summary,
            summary_has_compare,
            next(
                (
                    compare_meta_by_calc_id[row.calc_id]
                    for row in full
                    if row.sample_id == batch.calc_sample_id and row.calc_id in compare_meta_by_calc_id
                ),
                {},
            ),
        ) if summary else {},
    }


@router.get("/{batch_id}/calc-view")
def get_calc_view(batch_id: str, db: DbSession, member: CurrentMember) -> dict:
    batch = db.get(TbBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    calc = get_calc(batch_id, db, member)
    sampling = get_sampling(batch_id, db, member)["rows"]
    return {
        "batch": _batch_detail_response(db, batch),
        "plan": _plan_response(batch.plan) if hasattr(batch, "plan") else _plan_response(db.get(TbExpPlan, batch.exp_id)),
        "researchers": _batch_researchers(db, batch_id),
        "files": _batch_files(db, batch_id),
        "sampling": sampling,
        "calcFull": calc["full"],
        "calcSummary": calc["summary"],
    }


@router.post("/{batch_id}/files", status_code=status.HTTP_201_CREATED)
def upload_batch_file(
    batch_id: str,
    db: DbSession,
    member: CurrentMember,
    fileType: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    if fileType not in {"DO_PH", "CO2_O2", "REF", "TREND_CSV"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid fileType")
    if db.get(TbBatch, batch_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    stored = _save_upload(file, "batches", batch_id)
    record = TbBatchFile(
        batch_id=batch_id,
        file_type=fileType,
        origin_file_nm=file.filename or "upload.bin",
        save_file_nm=stored.name,
        file_path=str(stored),
        file_size=stored.stat().st_size,
        mime_type=file.content_type,
        use_yn="Y",
        reg_dt=datetime.now(),
        reg_id=member.member_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _file_response(record)


@router.get("/{batch_id}/files/{file_id}")
def download_batch_file(batch_id: str, file_id: int, db: DbSession, _: CurrentMember) -> FileResponse:
    record = db.get(TbBatchFile, file_id)
    if record is None or record.batch_id != batch_id or record.use_yn != "Y":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    path = Path(record.file_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(path, media_type=record.mime_type, filename=record.origin_file_nm)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(batch_id: str) -> None:
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)


SAMPLING_COLUMNS = [
    "samplingTime",
    "od",
    "feedWeight",
    "brothVolume",
    "targetProdConc",
    "glucoseConc",
    "lycopene",
    "aCarotene",
    "bCarotene",
    "citricAcid",
    "pyruvicAcid",
    "succinicAcid",
    "lacticAcid",
    "aceticAcid",
]


def _batch_search_response(row) -> dict:
    last_sampled_at = row["last_sampled_at"]
    return {
        "batch_id": row["batch_id"],
        "exp_id": row["exp_id"],
        "batch_no": row["batch_no"],
        "batch_name": row["batch_id"],
        "is_best": row["is_best"],
        "last_sampled_at": last_sampled_at.isoformat() if last_sampled_at else None,
        "sampling_time": number(row["sampling_time"]),
        "od": number(row["od"]),
        "feed_weight": number(row["feed_weight"]),
        "broth_volume": number(row["broth_volume"]),
        "target_prod_conc": number(row["target_prod_conc"]),
        "glucose_conc": number(row["glucose_conc"]),
        "lycopene": number(row["lycopene"]),
        "a_carotene": number(row["a_carotene"]),
        "b_carotene": number(row["b_carotene"]),
        "citric_acid": number(row["citric_acid"]),
        "pyruvic_acid": number(row["pyruvic_acid"]),
        "succinic_acid": number(row["succinic_acid"]),
        "lactic_acid": number(row["lactic_acid"]),
        "acetic_acid": number(row["acetic_acid"]),
    }


def _batch_detail_response(db: DbSession, batch: TbBatch) -> dict:
    plan = db.get(TbExpPlan, batch.exp_id)
    return {
        "batchId": batch.batch_id,
        "planId": batch.exp_id,
        "planCmp": plan.cmp_batch_id if plan else None,
        "purpose": plan.purpose if plan else None,
        "startDt": yyyymmdd(batch.start_dt),
        "params": {
            "prepTime": number(batch.prep_time),
            "equipVol": number(batch.equip_vol),
            "purifyYield": number(batch.purify_yield),
            "dcwOdFactor": number(batch.dcw_od_factor),
            "feedGlucoseConc": number(batch.feed_glucose_conc),
            "feedDensity": number(batch.feed_density),
            "feedGlucosePerFeed": number(batch.feed_glucose_per_feed),
        },
        "comparison": {"type": batch.cmp_type, "targetBatchId": _batch_compare_batch_id(db, batch)},
        "calcSampleId": batch.calc_sample_id,
        "researchers": _batch_researchers(db, batch.batch_id),
        "files": _batch_files(db, batch.batch_id),
    }


def _plan_response(plan: TbExpPlan | None) -> dict:
    if plan is None:
        return {}
    return {
        "id": plan.exp_id,
        "purpose": plan.purpose,
        "strain": plan.strain_nm,
        "batch1": plan.content1,
        "batch2": plan.content2,
        "batch3": plan.content3,
        "batch4": plan.content4,
        "result": plan.result_content,
        "cmp": plan.cmp_batch_id,
        "created": yyyymmdd(plan.reg_dt),
    }


def _batch_researchers(db: DbSession, batch_id: str) -> list[dict]:
    rows = db.execute(
        select(TbBatchResearcher, TbResearcher)
        .join(TbResearcher, TbResearcher.researcher_id == TbBatchResearcher.researcher_id)
        .where(TbBatchResearcher.batch_id == batch_id)
        .order_by(TbBatchResearcher.researcher_role)
    ).all()
    return [
        {"role": br.researcher_role, "id": researcher.researcher_id, "name": researcher.researcher_nm}
        for br, researcher in rows
    ]


def _batch_files(db: DbSession, batch_id: str) -> dict:
    rows = db.scalars(select(TbBatchFile).where(TbBatchFile.batch_id == batch_id, TbBatchFile.use_yn == "Y")).all()
    files = {"doPh": None, "co2O2": None, "ref": None, "trendCsv": None}
    keys = {"DO_PH": "doPh", "CO2_O2": "co2O2", "REF": "ref", "TREND_CSV": "trendCsv"}
    for row in rows:
        files[keys.get(row.file_type, row.file_type)] = _file_response(row)
    return files


def _file_response(record: TbBatchFile) -> dict:
    return {
        "fileId": record.file_id,
        "fileType": record.file_type,
        "fileName": record.origin_file_nm,
        "fileSize": record.file_size,
        "mimeType": record.mime_type,
    }


def _replace_sampling(db: DbSession, batch_id: str, rows: list, member_id: str) -> None:
    batch = db.get(TbBatch, batch_id)
    calc_sampling_time = None
    if batch is not None:
        calc_sample = db.get(TbSampling, batch.calc_sample_id) if batch.calc_sample_id else None
        if calc_sample is not None and calc_sample.batch_id == batch_id:
            calc_sampling_time = calc_sample.sampling_time
        batch.calc_sample_id = None
    sample_ids = db.scalars(select(TbSampling.sample_id).where(TbSampling.batch_id == batch_id)).all()
    _clear_compare_sampling_refs(db, sample_ids)
    db.execute(delete(TbCalcFull).where(TbCalcFull.batch_id == batch_id))
    db.execute(delete(TbCalcSummary).where(TbCalcSummary.batch_id == batch_id))
    db.execute(delete(TbSampling).where(TbSampling.batch_id == batch_id))
    now = datetime.now()
    inserted_samples: list[TbSampling] = []
    for row in rows:
        sample = TbSampling(
            batch_id=batch_id,
            sampling_time=row.samplingTime,
            od=row.od,
            feed_weight=row.feedWeight,
            broth_volume=row.brothVolume,
            target_prod_conc=row.targetProdConc,
            glucose_conc=row.glucoseConc,
            lycopene=row.lycopene,
            a_carotene=row.aCarotene,
            b_carotene=row.bCarotene,
            citric_acid=row.citricAcid,
            pyruvic_acid=row.pyruvicAcid,
            succinic_acid=row.succinicAcid,
            lactic_acid=row.lacticAcid,
            acetic_acid=row.aceticAcid,
            reg_dt=now,
            upd_id=member_id,
        )
        inserted_samples.append(sample)
        db.add(sample)
    if batch is not None and calc_sampling_time is not None:
        db.flush()
        matched_sample = next(
            (sample for sample in inserted_samples if sample.sampling_time == calc_sampling_time),
            None,
        )
        if matched_sample is not None:
            batch.calc_sample_id = matched_sample.sample_id


def _sampling_response(row: TbSampling, calc_sample_id: int | None = None) -> dict:
    return {
        "id": row.sample_id,
        "isCalcSample": row.sample_id == calc_sample_id,
        "samplingTime": number(row.sampling_time),
        "od": number(row.od),
        "feedWeight": number(row.feed_weight),
        "brothVolume": number(row.broth_volume),
        "targetProdConc": number(row.target_prod_conc),
        "glucoseConc": number(row.glucose_conc),
        "lycopene": number(row.lycopene),
        "aCarotene": number(row.a_carotene),
        "bCarotene": number(row.b_carotene),
        "citricAcid": number(row.citric_acid),
        "pyruvicAcid": number(row.pyruvic_acid),
        "succinicAcid": number(row.succinic_acid),
        "lacticAcid": number(row.lactic_acid),
        "aceticAcid": number(row.acetic_acid),
    }


def _calc_full_response(row: TbCalcFull, compare_meta: dict | None = None, sampling_time=None, include_compare: bool = True) -> dict:
    data = {column.name: _serialize(getattr(row, column.name)) for column in TbCalcFull.__table__.columns if column.name != "batch_id"}
    data["base_sample_id"] = row.sample_id
    data["base_sampling_time"] = _serialize(sampling_time)
    data["sampling_time"] = _serialize(sampling_time)
    compare_meta = compare_meta or {}
    if not include_compare:
        data["abs_yield_up"] = None
        data["prod_up"] = None
        data["compare_batch_id"] = None
        data["compare_sample_id"] = None
        data["compare_age"] = None
        data["compare_sampling_time"] = None
        data["compare_time_diff"] = None
        data["matched_batch_id"] = None
        data["matched_sample_id"] = None
        data["matched_sampling_time"] = None
        return data
    data["compare_batch_id"] = compare_meta.get("compare_batch_id")
    data["compare_sample_id"] = compare_meta.get("compare_sample_id")
    data["compare_age"] = _serialize(compare_meta.get("compare_age"))
    data["compare_sampling_time"] = _serialize(compare_meta.get("compare_sampling_time"))
    data["compare_time_diff"] = _serialize(compare_meta.get("compare_time_diff"))
    data["matched_batch_id"] = compare_meta.get("matched_batch_id")
    data["matched_sample_id"] = compare_meta.get("matched_sample_id")
    data["matched_sampling_time"] = _serialize(compare_meta.get("matched_sampling_time"))
    data["abs_yield_up"] = _serialize(compare_meta.get("abs_yield_up"))
    data["prod_up"] = _serialize(compare_meta.get("prod_up"))
    return data


def _calc_summary_response(row: TbCalcSummary, include_compare: bool = True, compare_meta: dict | None = None) -> dict:
    data = {column.name: _serialize(getattr(row, column.name)) for column in TbCalcSummary.__table__.columns if column.name != "batch_id"}
    if not include_compare:
        data["abs_yield_up"] = None
        data["prod_up"] = None
    else:
        compare_meta = compare_meta or {}
        data["abs_yield_up"] = _serialize(compare_meta.get("abs_yield_up"))
        data["prod_up"] = _serialize(compare_meta.get("prod_up"))
    return data


def _clear_compare_sampling_refs(db: DbSession, sample_ids: list[int]) -> None:
    if not sample_ids or not _has_calc_full_compare_columns(db):
        return
    stmt = text(
        """
        UPDATE tb_calc_full
        SET compare_sample_id = NULL,
            compare_age = NULL,
            compare_time_diff = NULL,
            abs_yield_up = NULL,
            prod_up = NULL
        WHERE compare_sample_id IN :sample_ids
        """
    ).bindparams(bindparam("sample_ids", expanding=True))
    db.execute(stmt, {"sample_ids": sample_ids})


def _calc_sampling_time_by_sample_id(db: DbSession, sample_ids: list[int]) -> dict[int, object]:
    if not sample_ids:
        return {}
    stmt = select(TbSampling.sample_id, TbSampling.sampling_time).where(TbSampling.sample_id.in_(sample_ids))
    return {sample_id: sampling_time for sample_id, sampling_time in db.execute(stmt).all()}


def _batch_compare_batch_id(db: DbSession, batch: TbBatch) -> str | None:
    compare_batch_id = batch.cmp_batch_id
    if not compare_batch_id:
        plan = db.get(TbExpPlan, batch.exp_id)
        compare_batch_id = plan.cmp_batch_id if plan else None
    if not compare_batch_id or compare_batch_id == batch.batch_id:
        return None
    if _batch_has_samplings(db, compare_batch_id):
        return compare_batch_id
    compare_batch = db.get(TbBatch, compare_batch_id)
    if compare_batch is None:
        return None
    return _first_sampled_batch_in_experiment(db, compare_batch.exp_id, batch.batch_id)


def _batch_has_samplings(db: DbSession, batch_id: str) -> bool:
    return bool(db.scalar(select(TbSampling.sample_id).where(TbSampling.batch_id == batch_id).limit(1)))


def _first_sampled_batch_in_experiment(db: DbSession, exp_id: str, current_batch_id: str) -> str | None:
    return db.scalar(
        select(TbBatch.batch_id)
        .join(TbSampling, TbSampling.batch_id == TbBatch.batch_id)
        .where(TbBatch.exp_id == exp_id, TbBatch.batch_id != current_batch_id)
        .group_by(TbBatch.batch_id, TbBatch.batch_no)
        .order_by(TbBatch.batch_no, TbBatch.batch_id)
        .limit(1)
    )


def _has_calc_full_compare_columns(db: DbSession) -> bool:
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


def _serialize(value):
    if hasattr(value, "strftime"):
        return yyyymmdd(value)
    if hasattr(value, "as_tuple"):
        return number(value)
    return value


def _parse_date(value: str, field_name: str) -> datetime:
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "INVALID_DATE",
            "message": f"{field_name} must be YYYYMMDD or YYYY-MM-DD.",
        },
    )


def _save_upload(file: UploadFile, area: str, resource_id: str) -> Path:
    directory = Path(settings.upload_dir) / area / resource_id
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{file.filename or 'upload.bin'}"
    path = directory / filename
    with path.open("wb") as output:
        copyfileobj(file.file, output)
    return path
