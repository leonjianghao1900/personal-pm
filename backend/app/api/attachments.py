from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import DATA_DIR, get_db
from app.schemas import AttachmentRead
from app.services import attachment_service

router = APIRouter(prefix="/api/attachments", tags=["attachments"])

# Routes are ordered so /{aid}/* patterns are matched before /{entity_type}/{entity_id}.
# Otherwise /api/attachments/{int}/download would shadow into the entity endpoint.


@router.get("/{aid}/download")
def download(aid: int, db: Session = Depends(get_db)):
    att = attachment_service.get_attachment(db, aid)
    full_path = DATA_DIR / att.stored_path
    if not full_path.exists():
        raise HTTPException(404, "附件文件已丢失")
    return FileResponse(
        path=str(full_path),
        media_type=att.mime or "application/octet-stream",
        filename=att.original_name,
    )


@router.get("/{aid}", response_model=AttachmentRead)
def get_meta(aid: int, db: Session = Depends(get_db)):
    return attachment_service.get_attachment(db, aid)


@router.delete("/{aid}", status_code=204)
def delete(aid: int, db: Session = Depends(get_db)):
    attachment_service.delete_attachment(db, aid)
    return None


@router.post(
    "/{entity_type}/{entity_id}",
    response_model=AttachmentRead,
    status_code=201,
)
async def upload(
    entity_type: str = Path(..., pattern="^(task|cost|inbox)$"),
    entity_id: int = Path(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await attachment_service.save_attachment(db, entity_type, entity_id, file)


@router.get("/{entity_type}/{entity_id}", response_model=list[AttachmentRead])
def list_for_entity(
    entity_type: str = Path(..., pattern="^(task|cost|inbox)$"),
    entity_id: int = Path(...),
    db: Session = Depends(get_db),
):
    return attachment_service.list_attachments(db, entity_type, entity_id)
