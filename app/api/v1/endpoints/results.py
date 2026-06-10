from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import CurrentMember, DbSession
from app.api.v1.endpoints.batches import get_calc_view
from app.models.batch import TbBatch
from app.models.experiment import TbExpPlan
from app.utils.formatters import yyyymmdd


router = APIRouter()


@router.get("")
def list_results(
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
                "batchId": batch.batch_id,
                "purpose": plan.purpose,
                "startDt": yyyymmdd(batch.start_dt),
                "created": yyyymmdd(batch.reg_dt),
            }
            for batch, plan in rows
        ],
    }


@router.get("/experiments/{experiment_id}")
def get_experiment_results(experiment_id: str, db: DbSession, member: CurrentMember) -> dict:
    rows = db.scalars(select(TbBatch.batch_id).where(TbBatch.exp_id == experiment_id).order_by(TbBatch.batch_id)).all()
    return {"planId": experiment_id, "items": [get_calc_view(batch_id, db, member) for batch_id in rows]}


@router.get("/{batch_id}")
def get_batch_results(batch_id: str, db: DbSession, member: CurrentMember) -> dict:
    return get_calc_view(batch_id, db, member)


@router.get("/{batch_id}/chart")
def get_batch_result_chart(batch_id: str, db: DbSession, member: CurrentMember) -> dict:
    view = get_calc_view(batch_id, db, member)
    return {"batchId": batch_id, "items": view["calcFull"]}
