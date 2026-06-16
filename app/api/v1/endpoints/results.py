from datetime import datetime
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.api.deps import CurrentMember, DbSession
from app.api.v1.endpoints.batches import get_calc_view
from app.models.batch import TbBatch
from app.models.experiment import TbExpPlan
from app.schemas.api_schema import ResultPdfDownloadRequest
from app.services.pdf_service import create_results_pdf_zip
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


@router.post("/pdf-download")
def download_result_pdfs(
    payload: ResultPdfDownloadRequest,
    db: DbSession,
    member: CurrentMember,
) -> StreamingResponse:
    batch_ids = _pdf_batch_ids(db, payload)
    if not batch_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF로 다운로드할 배치가 없습니다.")
    views = [get_calc_view(batch_id, db, member) for batch_id in batch_ids]
    zip_bytes = create_results_pdf_zip(views)
    filename = f"batch_result_pdfs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/{batch_id}")
def get_batch_results(batch_id: str, db: DbSession, member: CurrentMember) -> dict:
    return get_calc_view(batch_id, db, member)


@router.get("/{batch_id}/chart")
def get_batch_result_chart(batch_id: str, db: DbSession, member: CurrentMember) -> dict:
    view = get_calc_view(batch_id, db, member)
    return {"batchId": batch_id, "items": view["calcFull"]}


def _pdf_batch_ids(db: DbSession, payload: ResultPdfDownloadRequest) -> list[str]:
    if payload.scope == "selected":
        if not payload.batch_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="선택 다운로드에는 batch_ids가 필요합니다.")
        existing_ids = set(db.scalars(select(TbBatch.batch_id).where(TbBatch.batch_id.in_(payload.batch_ids))).all())
        missing_ids = [batch_id for batch_id in payload.batch_ids if batch_id not in existing_ids]
        if missing_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"배치를 찾을 수 없습니다: {', '.join(missing_ids)}")
        return list(dict.fromkeys(payload.batch_ids))

    stmt = select(TbBatch.batch_id).join(TbExpPlan, TbExpPlan.exp_id == TbBatch.exp_id)
    if payload.plan_id:
        stmt = stmt.where(TbBatch.exp_id.ilike(f"%{payload.plan_id}%"))
    if payload.batch_id:
        stmt = stmt.where(TbBatch.batch_id.ilike(f"%{payload.batch_id}%"))
    if payload.purpose:
        stmt = stmt.where(TbExpPlan.purpose.ilike(f"%{payload.purpose}%"))
    return db.scalars(stmt.order_by(TbBatch.batch_id)).all()
