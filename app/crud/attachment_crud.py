from sqlalchemy.orm import Session

from app.models.batch_file import TbBatchFile
from app.models.exp_file import TbExpFile


def get_exp_file_by_id(db: Session, file_id: int) -> TbExpFile | None:
    return db.get(TbExpFile, file_id)


def get_batch_file_by_id(db: Session, file_id: int) -> TbBatchFile | None:
    return db.get(TbBatchFile, file_id)
