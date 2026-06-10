from datetime import datetime

from fastapi import APIRouter, Request, Response, status

from app.api.deps import CurrentMember, DbSession
from app.services.auth_service import authenticate_member
from app.schemas.auth_schema import LoginRequest, UserSessionResponse
from app.utils.exceptions import AppException


router = APIRouter()


@router.post("/login", response_model=UserSessionResponse)
def login(payload: LoginRequest, request: Request, db: DbSession) -> UserSessionResponse:
    member = authenticate_member(db, payload.id, payload.password)
    if member is None:
        raise AppException(
            code="LOGIN_FAILED",
            message="ID 또는 비밀번호가 올바르지 않습니다.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    member.last_login_dt = datetime.now()
    member.last_login_ip = request.client.host if request.client else None
    db.commit()

    request.session["member_id"] = member.member_id
    request.session["role"] = member.role_cd
    return UserSessionResponse(id=member.member_id, name=member.member_nm, role=member.role_cd)


@router.get("/me", response_model=UserSessionResponse)
def get_me(member: CurrentMember) -> UserSessionResponse:
    return UserSessionResponse(id=member.member_id, name=member.member_nm, role=member.role_cd)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> None:
    request.session.clear()
