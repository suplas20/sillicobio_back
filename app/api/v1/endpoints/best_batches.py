from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select

from app.api.deps import CurrentMember, DbSession
from app.models.batch import TbBatch
from app.models.best_batch import TbBestBatch
from app.schemas.api_schema import BestBatchCreateRequest


router = APIRouter()


@router.post("")
def create_best_batch(payload: BestBatchCreateRequest, db: DbSession, member: CurrentMember) -> dict:
    batch = db.get(TbBatch, payload.batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    exists = db.scalar(select(TbBestBatch.best_batch_id).where(TbBestBatch.batch_id == payload.batch_id).limit(1))
    if exists is not None:
        return {
            "message": "이미 베스트 배치로 등록되어 있습니다.",
            "batch_id": payload.batch_id,
            "already_exists": True,
        }

    max_sort_ord = db.scalar(select(func.max(TbBestBatch.sort_ord))) or 0
    best_batch = TbBestBatch(
        exp_id=batch.exp_id,
        batch_id=batch.batch_id,
        sort_ord=max_sort_ord + 1,
        reg_id=member.member_id,
        reg_dt=datetime.now(),
    )
    db.add(best_batch)
    db.commit()
    db.refresh(best_batch)
    return {
        "message": "베스트 배치가 등록되었습니다.",
        "best_batch": {
            "best_batch_id": best_batch.best_batch_id,
            "exp_id": best_batch.exp_id,
            "batch_id": best_batch.batch_id,
            "sort_ord": best_batch.sort_ord,
        },
    }


@router.delete("/by-batch/{batch_id}")
def delete_best_batch_by_batch(batch_id: str, db: DbSession, _: CurrentMember) -> dict:
    result = db.execute(delete(TbBestBatch).where(TbBestBatch.batch_id == batch_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    db.commit()
    return {"message": "베스트 배치가 해제되었습니다.", "batch_id": batch_id}
