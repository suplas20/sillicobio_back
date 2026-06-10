from sqlalchemy.orm import Session

from app.models.batch import TbBatch


def get_batch_by_id(db: Session, batch_id: str) -> TbBatch | None:
    return db.get(TbBatch, batch_id)
