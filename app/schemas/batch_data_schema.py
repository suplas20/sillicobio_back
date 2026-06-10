from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BatchDataBase(BaseModel):
    batch_id: str
    sample_dt: str | None = None
    sample_time: str | None = None
    temperature: Decimal | None = None
    ph: Decimal | None = None
    dissolved_oxygen: Decimal | None = None
    glucose: Decimal | None = None


class BatchDataCreate(BatchDataBase):
    pass


class BatchDataUpdate(BaseModel):
    sample_dt: str | None = None
    sample_time: str | None = None
    temperature: Decimal | None = None
    ph: Decimal | None = None
    dissolved_oxygen: Decimal | None = None
    glucose: Decimal | None = None


class BatchDataResponse(BatchDataBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
