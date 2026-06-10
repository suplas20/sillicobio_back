from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import AdminMember, CurrentMember, DbSession
from app.models.researcher import TbResearcher
from app.schemas.researcher_schema import ResearcherCreate, ResearcherUpdate


router = APIRouter()


@router.get("")
def list_researchers(
    db: DbSession,
    _: CurrentMember,
    id: str | None = None,
    name: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
) -> dict:
    stmt = select(TbResearcher).where(TbResearcher.use_yn == "Y")
    count_stmt = select(func.count()).select_from(TbResearcher).where(TbResearcher.use_yn == "Y")
    if id:
        stmt = stmt.where(TbResearcher.researcher_id.ilike(f"%{id}%"))
        count_stmt = count_stmt.where(TbResearcher.researcher_id.ilike(f"%{id}%"))
    if name:
        stmt = stmt.where(TbResearcher.researcher_nm.ilike(f"%{name}%"))
        count_stmt = count_stmt.where(TbResearcher.researcher_nm.ilike(f"%{name}%"))
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(TbResearcher.researcher_id).offset((page - 1) * size).limit(size)).all()
    return {"total": total, "page": page, "size": size, "items": [_researcher_response(row) for row in rows]}


@router.get("/{researcher_id}")
def get_researcher(researcher_id: str, db: DbSession, _: CurrentMember) -> dict:
    researcher = db.get(TbResearcher, researcher_id)
    if researcher is None or researcher.use_yn != "Y":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _researcher_response(researcher)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_researcher(payload: ResearcherCreate, db: DbSession, admin: AdminMember) -> dict:
    researcher_id = _next_researcher_id(db)
    researcher = TbResearcher(
        researcher_id=researcher_id,
        researcher_nm=payload.name,
        email=payload.email,
        tel=payload.tel,
        use_yn="Y",
        reg_dt=datetime.now(),
        reg_id=admin.member_id,
    )
    db.add(researcher)
    db.commit()
    db.refresh(researcher)
    return _researcher_response(researcher)


@router.put("/{researcher_id}")
def update_researcher(researcher_id: str, payload: ResearcherUpdate, db: DbSession, admin: AdminMember) -> dict:
    researcher = db.get(TbResearcher, researcher_id)
    if researcher is None or researcher.use_yn != "Y":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if payload.name is not None:
        researcher.researcher_nm = payload.name
    if payload.email is not None:
        researcher.email = payload.email
    if payload.tel is not None:
        researcher.tel = payload.tel
    researcher.upd_dt = datetime.now()
    researcher.upd_id = admin.member_id
    db.commit()
    db.refresh(researcher)
    return _researcher_response(researcher)


@router.delete("/{researcher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_researcher(researcher_id: str, db: DbSession, admin: AdminMember) -> None:
    researcher = db.get(TbResearcher, researcher_id)
    if researcher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    researcher.use_yn = "N"
    researcher.upd_dt = datetime.now()
    researcher.upd_id = admin.member_id
    db.commit()


def _researcher_response(researcher: TbResearcher) -> dict:
    return {
        "id": researcher.researcher_id,
        "name": researcher.researcher_nm,
        "email": researcher.email,
        "tel": researcher.tel,
    }


def _next_researcher_id(db: DbSession) -> str:
    ids = db.scalars(select(TbResearcher.researcher_id).where(TbResearcher.researcher_id.like("RES%"))).all()
    next_no = 1
    if ids:
        next_no = max(int(value[3:]) for value in ids if value[3:].isdigit()) + 1
    return f"RES{next_no:03d}"
