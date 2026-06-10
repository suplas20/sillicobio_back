from pydantic import BaseModel, ConfigDict


class ResearcherBase(BaseModel):
    name: str
    email: str | None = None
    tel: str | None = None


class ResearcherCreate(ResearcherBase):
    pass


class ResearcherUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    tel: str | None = None


class ResearcherResponse(ResearcherBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
