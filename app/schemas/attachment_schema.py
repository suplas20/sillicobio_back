from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource_type: str
    resource_id: str
    original_filename: str
    content_type: str | None = None
    file_size: int | None = None
