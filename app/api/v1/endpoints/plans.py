from datetime import datetime
from pathlib import Path
from shutil import copyfileobj

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from app.api.deps import CurrentMember, DbSession
from app.core.config import settings
from app.models.batch import TbBatch
from app.models.exp_file import TbExpFile
from app.models.experiment import TbExpPlan
from app.schemas.api_schema import PlanSaveRequest
from app.utils.formatters import yyyymmdd


router = APIRouter()


@router.get("")
def list_plans(
    db: DbSession,
    _: CurrentMember,
    id: str | None = None,
    purpose: str | None = None,
    createdFrom: str | None = None,
    createdTo: str | None = None,
    sort: str = "created,desc",
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
    if createdFrom:
        start = datetime.strptime(createdFrom, "%Y%m%d")
        stmt = stmt.where(TbExpPlan.reg_dt >= start)
        count_stmt = count_stmt.where(TbExpPlan.reg_dt >= start)
    if createdTo:
        end = datetime.strptime(createdTo, "%Y%m%d").replace(hour=23, minute=59, second=59)
        stmt = stmt.where(TbExpPlan.reg_dt <= end)
        count_stmt = count_stmt.where(TbExpPlan.reg_dt <= end)

    direction = sort.split(",")[-1] if sort else "desc"
    order_by = TbExpPlan.reg_dt.asc() if direction == "asc" else TbExpPlan.reg_dt.desc()
    total = db.scalar(count_stmt) or 0
    plans = db.scalars(stmt.order_by(order_by).offset((page - 1) * size).limit(size)).all()
    return {"total": total, "page": page, "size": size, "items": [_plan_response(db, plan) for plan in plans]}


@router.get("/{plan_id}")
def get_plan(plan_id: str, db: DbSession, _: CurrentMember) -> dict:
    plan = db.get(TbExpPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _plan_response(db, plan)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanSaveRequest, db: DbSession, member: CurrentMember) -> dict:
    plan_id = _next_plan_id(db)
    plan = TbExpPlan(
        exp_id=plan_id,
        purpose=payload.purpose,
        content1=payload.batch1,
        content2=payload.batch2,
        content3=payload.batch3,
        content4=payload.batch4,
        strain_nm=payload.strain,
        cmp_batch_id=payload.cmp,
        result_content=payload.result,
        reg_dt=datetime.now(),
        reg_id=member.member_id,
    )
    db.add(plan)
    batches = []
    for index in range(1, 5):
        batch = TbBatch(
            batch_id=f"{plan_id}_BAT{index:02d}",
            exp_id=plan_id,
            batch_no=f"{index:02d}",
            reg_dt=datetime.now(),
        )
        db.add(batch)
        batches.append(batch)
    db.commit()
    db.refresh(plan)
    return {
        "plan": _plan_response(db, plan),
        "batches": [{"id": batch.batch_id, "planId": batch.exp_id} for batch in batches],
    }


@router.put("/{plan_id}")
def update_plan(plan_id: str, payload: PlanSaveRequest, db: DbSession, member: CurrentMember) -> dict:
    plan = db.get(TbExpPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    plan.purpose = payload.purpose
    plan.content1 = payload.batch1
    plan.content2 = payload.batch2
    plan.content3 = payload.batch3
    plan.content4 = payload.batch4
    plan.strain_nm = payload.strain
    plan.cmp_batch_id = payload.cmp
    plan.result_content = payload.result
    plan.upd_dt = datetime.now()
    plan.upd_id = member.member_id
    db.commit()
    db.refresh(plan)
    return _plan_response(db, plan)


@router.post("/{plan_id}/files", status_code=status.HTTP_201_CREATED)
def upload_plan_file(
    plan_id: str,
    db: DbSession,
    member: CurrentMember,
    fileType: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    if fileType not in {"PLAN", "ALL"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="fileType must be PLAN or ALL")
    if db.get(TbExpPlan, plan_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    stored = _save_upload(file, "plans", plan_id)
    record = TbExpFile(
        exp_id=plan_id,
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


@router.get("/{plan_id}/files/{file_id}")
def download_plan_file(plan_id: str, file_id: int, db: DbSession, _: CurrentMember) -> FileResponse:
    record = db.get(TbExpFile, file_id)
    if record is None or record.exp_id != plan_id or record.use_yn != "Y":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    path = Path(record.file_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(path, media_type=record.mime_type, filename=record.origin_file_nm)


def _plan_response(db: DbSession, plan: TbExpPlan) -> dict:
    files = db.scalars(select(TbExpFile).where(TbExpFile.exp_id == plan.exp_id, TbExpFile.use_yn == "Y")).all()
    plan_file = next((file for file in files if file.file_type == "PLAN"), None)
    all_file = next((file for file in files if file.file_type == "ALL"), None)
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
        "planFile": _file_response(plan_file) if plan_file else None,
        "allFile": _file_response(all_file) if all_file else None,
        "created": yyyymmdd(plan.reg_dt),
    }


def _file_response(record: TbExpFile) -> dict:
    return {
        "fileId": record.file_id,
        "fileType": record.file_type,
        "fileName": record.origin_file_nm,
        "fileSize": record.file_size,
        "mimeType": record.mime_type,
    }


def _save_upload(file: UploadFile, area: str, resource_id: str) -> Path:
    directory = Path(settings.upload_dir) / area / resource_id
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{file.filename or 'upload.bin'}"
    path = directory / filename
    with path.open("wb") as output:
        copyfileobj(file.file, output)
    return path


def _next_plan_id(db: DbSession) -> str:
    ids = db.scalars(select(TbExpPlan.exp_id).where(TbExpPlan.exp_id.like("LAB%"))).all()
    next_no = 1
    if ids:
        next_no = max(int(value[3:]) for value in ids if value[3:].isdigit()) + 1
    return f"LAB{next_no:05d}"
