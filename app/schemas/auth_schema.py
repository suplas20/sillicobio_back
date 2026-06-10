from pydantic import BaseModel


class LoginRequest(BaseModel):
    id: str
    password: str


class UserSessionResponse(BaseModel):
    id: str
    name: str
    role: str
