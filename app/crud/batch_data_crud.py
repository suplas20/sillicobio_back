from sqlalchemy.orm import Session

from app.models.batch_data import TbBatchData


def get_batch_data_by_id(db: Session, batch_data_id: int) -> TbBatchData | None:
    return db.get(TbBatchData, batch_data_id)
