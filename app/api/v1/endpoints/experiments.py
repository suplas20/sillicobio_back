from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentMember, DbSession
from app.api.v1.endpoints.plans import create_plan as create_plan_api
from app.api.v1.endpoints.plans import get_plan as get_plan_api
from app.api.v1.endpoints.plans import update_plan as update_plan_api
from app.models.batch import TbBatch
from app.models.experiment import TbExpPlan
from app.schemas.api_schema import PlanSaveRequest
from app.utils.formatters import yyyymmdd


router = APIRouter()


@router.get("")
def list_experiments(
    db: DbSession,
    member: CurrentMember,
    id: str | None = None,
    purpose: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
) -> dict:
    stmt = select(TbExpPlan)
    count_stmt = select(func.count()).select_from(TbExpPlan)
    if id:
        stmt = stmt.where(TbExpPlan.exp_id.ilike(f"%{id}%"))
        count_stmt = count_stmt.where(TbExpPlan.exp_id.ilike(f"%{id}%"))
    if purpose:
        stmt = stmt.where(TbExpPlan.purpose.ilike(f"%{purpose}%"))
        count_stmt = count_stmt.where(TbExpPlan.purpose.ilike(f"%{purpose}%"))
    total = db.scalar(count_stmt) or 0
    plans = db.scalars(stmt.order_by(TbExpPlan.reg_dt.desc()).offset((page - 1) * size).limit(size)).all()
    return {"total": total, "page": page, "size": size, "items": [_experiment_response(plan) for plan in plans]}


@router.get("/my")
def list_my_experiments(db: DbSession, member: CurrentMember) -> dict:
    plans = db.scalars(select(TbExpPlan).where(TbExpPlan.reg_id == member.member_id).order_by(TbExpPlan.reg_dt.desc())).all()
    return {"items": [_experiment_response(plan) for plan in plans]}


@router.get("/{experiment_id}")
def get_experiment(experiment_id: str, db: DbSession, member: CurrentMember) -> dict:
    return get_plan_api(experiment_id, db, member)


@router.get("/{experiment_id}/batches")
def list_experiment_batches(experiment_id: str, db: DbSession, _: CurrentMember) -> dict:
    batches = db.scalars(select(TbBatch).where(TbBatch.exp_id == experiment_id).order_by(TbBatch.batch_id)).all()
    return {"items": [{"id": batch.batch_id, "planId": batch.exp_id, "batchNo": batch.batch_no} for batch in batches]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_experiment(payload: PlanSaveRequest, db: DbSession, member: CurrentMember) -> dict:
    return create_plan_api(payload, db, member)


@router.put("/{experiment_id}")
def update_experiment(experiment_id: str, payload: PlanSaveRequest, db: DbSession, member: CurrentMember) -> dict:
    return update_plan_api(experiment_id, payload, db, member)


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experiment(experiment_id: str) -> None:
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)


def _experiment_response(plan: TbExpPlan) -> dict:
    return {
        "id": plan.exp_id,
        "purpose": plan.purpose,
        "strain": plan.strain_nm,
        "result": plan.result_content,
        "created": yyyymmdd(plan.reg_dt),
    }
