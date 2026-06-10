from sqlalchemy.orm import Session

from app.models.experiment import TbExperiment


def get_experiment_by_id(db: Session, experiment_id: str) -> TbExperiment | None:
    return db.get(TbExperiment, experiment_id)
