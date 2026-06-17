from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import AdminMember, DbSession
from app.models.member import TbMember
from app.schemas.member_schema import MemberCreate, MemberUpdate
from app.utils.formatters import yyyymmdd


router = APIRouter()


@router.get("")
def list_members(
    db: DbSession,
    _: AdminMember,
    id: str | None = None,
    name: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
) -> dict:
    stmt = select(TbMember)
    count_stmt = select(func.count()).select_from(TbMember)
    if id:
        stmt = stmt.where(TbMember.member_id.ilike(f"%{id}%"))
        count_stmt = count_stmt.where(TbMember.member_id.ilike(f"%{id}%"))
    if name:
        stmt = stmt.where(TbMember.member_nm.ilike(f"%{name}%"))
        count_stmt = count_stmt.where(TbMember.member_nm.ilike(f"%{name}%"))

    total = db.scalar(count_stmt) or 0
    members = db.scalars(
        stmt.order_by(TbMember.reg_dt.desc(), TbMember.member_id.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [_member_response(member) for member in members],
    }


@router.get("/{member_id}")
def get_member(member_id: str, db: DbSession, _: AdminMember) -> dict:
    member = db.get(TbMember, member_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _member_response(member)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_member(payload: MemberCreate, db: DbSession, admin: AdminMember) -> dict:
    if payload.role not in {"ADMIN", "USER"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="role must be ADMIN or USER")
    if db.get(TbMember, payload.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="member id already exists")

    member = TbMember(
        member_id=payload.id,
        member_nm=payload.name,
        password=payload.password,
        role_cd=payload.role,
        reg_dt=datetime.now(),
        reg_id=admin.member_id,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return _member_response(member)


@router.put("/{member_id}")
def update_member(member_id: str, payload: MemberUpdate, db: DbSession, admin: AdminMember) -> dict:
    member = db.get(TbMember, member_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if payload.role is not None and payload.role not in {"ADMIN", "USER"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="role must be ADMIN or USER")

    if payload.name is not None:
        member.member_nm = payload.name
    if payload.password is not None:
        member.password = payload.password
    if payload.role is not None:
        member.role_cd = payload.role
    member.upd_dt = datetime.now()
    member.upd_id = admin.member_id
    db.commit()
    db.refresh(member)
    return _member_response(member)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(member_id: str, db: DbSession, _: AdminMember) -> None:
    member = db.get(TbMember, member_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    db.delete(member)
    db.commit()


def _member_response(member: TbMember) -> dict:
    return {
        "id": member.member_id,
        "name": member.member_nm,
        "password": member.password,
        "role": member.role_cd,
        "created": yyyymmdd(member.reg_dt),
    }
