from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentMember, DbSession
from app.models.batch_data import TbSampling
from app.schemas.api_schema import SamplingRow
from app.utils.formatters import number


router = APIRouter()


@router.get("")
def list_batch_data(
    db: DbSession,
    _: CurrentMember,
    batchId: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
) -> dict:
    stmt = select(TbSampling)
    count_stmt = select(func.count()).select_from(TbSampling)
    if batchId:
        stmt = stmt.where(TbSampling.batch_id == batchId)
        count_stmt = count_stmt.where(TbSampling.batch_id == batchId)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(TbSampling.batch_id.desc(), TbSampling.sampling_time.desc(), TbSampling.sample_id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return {"total": total, "page": page, "size": size, "items": [_sampling_response(row) for row in rows]}


@router.get("/{batch_data_id}")
def get_batch_data(batch_data_id: int, db: DbSession, _: CurrentMember) -> dict:
    row = db.get(TbSampling, batch_data_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _sampling_response(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_batch_data(payload: SamplingRow, db: DbSession, member: CurrentMember, batchId: str) -> dict:
    row = _row_from_payload(batchId, payload, member.member_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _sampling_response(row)


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def bulk_create_batch_data(payload: list[SamplingRow], db: DbSession, member: CurrentMember, batchId: str) -> dict:
    rows = [_row_from_payload(batchId, item, member.member_id) for item in payload]
    db.add_all(rows)
    db.commit()
    return {"created": len(rows)}


@router.put("/{batch_data_id}")
def update_batch_data(batch_data_id: int, payload: SamplingRow, db: DbSession, member: CurrentMember) -> dict:
    row = db.get(TbSampling, batch_data_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    _apply_payload(row, payload)
    row.upd_dt = datetime.now()
    row.upd_id = member.member_id
    db.commit()
    db.refresh(row)
    return _sampling_response(row)


@router.delete("/{batch_data_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch_data(batch_data_id: int, db: DbSession, _: CurrentMember) -> None:
    row = db.get(TbSampling, batch_data_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    db.delete(row)
    db.commit()


def _row_from_payload(batch_id: str, payload: SamplingRow, member_id: str) -> TbSampling:
    row = TbSampling(batch_id=batch_id, sampling_time=payload.samplingTime, reg_dt=datetime.now(), upd_id=member_id)
    _apply_payload(row, payload)
    return row


def _apply_payload(row: TbSampling, payload: SamplingRow) -> None:
    row.sampling_time = payload.samplingTime
    row.od = payload.od
    row.feed_weight = payload.feedWeight
    row.broth_volume = payload.brothVolume
    row.target_prod_conc = payload.targetProdConc
    row.glucose_conc = payload.glucoseConc
    row.lycopene = payload.lycopene
    row.a_carotene = payload.aCarotene
    row.b_carotene = payload.bCarotene
    row.citric_acid = payload.citricAcid
    row.pyruvic_acid = payload.pyruvicAcid
    row.succinic_acid = payload.succinicAcid
    row.lactic_acid = payload.lacticAcid
    row.acetic_acid = payload.aceticAcid


def _sampling_response(row: TbSampling) -> dict:
    return {
        "id": row.sample_id,
        "batchId": row.batch_id,
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
