from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentMember, DbSession
from app.api.v1.endpoints.batches import download_batch_file, upload_batch_file
from app.api.v1.endpoints.plans import download_plan_file, upload_plan_file
from app.models.batch_file import TbBatchFile
from app.models.exp_file import TbExpFile


router = APIRouter()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_attachment(
    db: DbSession,
    member: CurrentMember,
    resourceType: str = Form(...),
    resourceId: str = Form(...),
    fileType: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    if resourceType == "PLAN":
        return upload_plan_file(resourceId, db, member, fileType, file)
    if resourceType == "BATCH":
        return upload_batch_file(resourceId, db, member, fileType, file)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="resourceType must be PLAN or BATCH")


@router.get("/{attachment_id}")
def get_attachment(attachment_id: int, db: DbSession, member: CurrentMember, resourceType: str = "PLAN") -> FileResponse:
    if resourceType == "PLAN":
        record = db.get(TbExpFile, attachment_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return download_plan_file(record.exp_id, attachment_id, db, member)
    record = db.get(TbBatchFile, attachment_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return download_batch_file(record.batch_id, attachment_id, db, member)


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(attachment_id: int, db: DbSession, _: CurrentMember, resourceType: str = "PLAN") -> None:
    if resourceType == "PLAN":
        record = db.get(TbExpFile, attachment_id)
    else:
        record = db.get(TbBatchFile, attachment_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    record.use_yn = "N"
    db.commit()
