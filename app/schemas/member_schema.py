from pydantic import BaseModel, ConfigDict


class MemberBase(BaseModel):
    id: str
    name: str
    role: str


class MemberCreate(MemberBase):
    password: str


class MemberUpdate(BaseModel):
    name: str | None = None
    password: str | None = None
    role: str | None = None


class MemberResponse(MemberBase):
    model_config = ConfigDict(from_attributes=True)
