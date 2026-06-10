from sqlalchemy.orm import Session

from app.models.member import TbMember


def get_member_by_id(db: Session, member_id: str) -> TbMember | None:
    return db.get(TbMember, member_id)
