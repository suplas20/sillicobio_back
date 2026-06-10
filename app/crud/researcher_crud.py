from sqlalchemy.orm import Session

from app.models.researcher import TbResearcher


def get_researcher_by_id(db: Session, researcher_id: str) -> TbResearcher | None:
    return db.get(TbResearcher, researcher_id)
