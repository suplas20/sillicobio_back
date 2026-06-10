from pydantic import BaseModel, ConfigDict


class ExperimentBase(BaseModel):
    title: str
    purpose: str | None = None
    researcher_id: str | None = None


class ExperimentCreate(ExperimentBase):
    pass


class ExperimentUpdate(BaseModel):
    title: str | None = None
    purpose: str | None = None
    researcher_id: str | None = None
    status_cd: str | None = None


class ExperimentResponse(ExperimentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status_cd: str | None = None
