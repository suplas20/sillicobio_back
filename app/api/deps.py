from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.crud.member_crud import get_member_by_id
from app.db.session import get_db
from app.models.member import TbMember


DbSession = Annotated[Session, Depends(get_db)]


def current_member(request: Request, db: DbSession) -> TbMember:
    member_id = request.session.get("member_id")
    if not member_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "로그인이 필요합니다."},
        )
    member = get_member_by_id(db, member_id)
    if member is None:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "로그인이 필요합니다."},
        )
    return member


CurrentMember = Annotated[TbMember, Depends(current_member)]


def admin_member(member: CurrentMember) -> TbMember:
    if member.role_cd != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "관리자 권한이 필요합니다."},
        )
    return member


AdminMember = Annotated[TbMember, Depends(admin_member)]
