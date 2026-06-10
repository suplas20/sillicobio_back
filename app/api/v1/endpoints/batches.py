from datetime import datetime
from pathlib import Path
from shutil import copyfileobj

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select

from app.api.deps import CurrentMember, DbSession
from app.core.config import settings
from app.models.batch import TbBatch
from app.models.batch_data import TbSampling
from app.models.batch_file import TbBatchFile
from app.models.batch_researcher import TbBatchResearcher
from app.models.calc_full import TbCalcFull
from app.models.calc_summary import TbCalcSummary
from app.models.experiment import TbExpPlan
from app.models.researcher import TbResearcher
from app.schemas.api_schema import BatchDetailSaveRequest, SamplingSaveRequest
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
    rows = db.execute(stmt.order_by(TbBatch.batch_id).limit(100)).all()
    return {
        "items": [
            {"batchId": batch.batch_id, "planId": batch.exp_id, "purpose": plan.purpose}
            for batch, plan in rows
        ]
    }


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
    if payload.startDt:
        batch.start_dt = datetime.strptime(payload.startDt, "%Y%m%d").date()
    batch.prep_time = payload.params.prepTime
    batch.equip_vol = payload.params.equipVol
    batch.purify_yield = payload.params.purifyYield
    batch.dcw_od_factor = payload.params.dcwOdFactor
    batch.feed_glucose_conc = payload.params.feedGlucoseConc
    batch.feed_density = payload.params.feedDensity
    batch.feed_glucose_per_feed = payload.params.feedGlucosePerFeed
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
    if db.get(TbBatch, batch_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    rows = db.scalars(
        select(TbSampling).where(TbSampling.batch_id == batch_id).order_by(TbSampling.sampling_time)
    ).all()
    return {"batchId": batch_id, "columns": SAMPLING_COLUMNS, "rows": [_sampling_response(row) for row in rows]}


@router.put("/{batch_id}/sampling")
def save_sampling(batch_id: str, payload: SamplingSaveRequest, db: DbSession, member: CurrentMember) -> dict:
    if db.get(TbBatch, batch_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    _replace_sampling(db, batch_id, payload.rows, member.member_id)
    db.commit()
    return {"batchId": batch_id, "message": "샘플링 데이터가 저장되었습니다.", "recalculated": True}


@router.get("/{batch_id}/calc")
def get_calc(batch_id: str, db: DbSession, _: CurrentMember) -> dict:
    if db.get(TbBatch, batch_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    full = db.scalars(select(TbCalcFull).where(TbCalcFull.batch_id == batch_id).order_by(TbCalcFull.age)).all()
    summary = db.get(TbCalcSummary, batch_id)
    return {
        "batchId": batch_id,
        "full": [_calc_full_response(row) for row in full],
        "summary": _calc_summary_response(summary) if summary else {},
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


def _batch_detail_response(db: DbSession, batch: TbBatch) -> dict:
    plan = db.get(TbExpPlan, batch.exp_id)
    return {
        "batchId": batch.batch_id,
        "planId": batch.exp_id,
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
        "comparison": {"type": batch.cmp_type, "targetBatchId": batch.cmp_batch_id},
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
    db.execute(delete(TbSampling).where(TbSampling.batch_id == batch_id))
    now = datetime.now()
    for row in rows:
        db.add(
            TbSampling(
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
        )


def _sampling_response(row: TbSampling) -> dict:
    return {
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


def _calc_full_response(row: TbCalcFull) -> dict:
    return {column.name: _serialize(getattr(row, column.name)) for column in TbCalcFull.__table__.columns if column.name != "batch_id"}


def _calc_summary_response(row: TbCalcSummary) -> dict:
    return {column.name: _serialize(getattr(row, column.name)) for column in TbCalcSummary.__table__.columns if column.name != "batch_id"}


def _serialize(value):
    if hasattr(value, "strftime"):
        return yyyymmdd(value)
    if hasattr(value, "as_tuple"):
        return number(value)
    return value


def _save_upload(file: UploadFile, area: str, resource_id: str) -> Path:
    directory = Path(settings.upload_dir) / area / resource_id
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{file.filename or 'upload.bin'}"
    path = directory / filename
    with path.open("wb") as output:
        copyfileobj(file.file, output)
    return path
