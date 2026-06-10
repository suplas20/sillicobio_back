from pydantic import BaseModel, ConfigDict


class BatchBase(BaseModel):
    experiment_id: str
    batch_no: str | None = None
    start_dt: str | None = None
    end_dt: str | None = None
    status_cd: str | None = None


class BatchCreate(BatchBase):
    pass


class BatchUpdate(BaseModel):
    batch_no: str | None = None
    start_dt: str | None = None
    end_dt: str | None = None
    status_cd: str | None = None


class BatchResponse(BatchBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
