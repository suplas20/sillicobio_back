from sqlalchemy.orm import Session

from app.core.security import verify_plain_password
from app.crud.member_crud import get_member_by_id
from app.models.member import TbMember


def authenticate_member(db: Session, member_id: str, password: str) -> TbMember | None:
    member = get_member_by_id(db, member_id)
    if member is None:
        return None
    if not verify_plain_password(password, member.password):
        return None
    return member
