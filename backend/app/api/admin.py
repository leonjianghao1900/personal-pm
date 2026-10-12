import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import backup_service

router = APIRouter(prefix="/api/admin", tags=["admin"])
MAX_BACKUP_BYTES = 50 * 1024 * 1024
MAX_FULL_BACKUP_BYTES = 500 * 1024 * 1024  # 500 MB for ZIP w/ attachments


@router.get("/backup")
def get_backup(db: Session = Depends(get_db)):
    data = backup_service.export_data(db)
    filename = f"pm-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    body = json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/restore")
async def post_restore(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read(MAX_BACKUP_BYTES + 1)
    if len(raw) > MAX_BACKUP_BYTES:
        raise HTTPException(413, "备份文件超过 50MB 限制")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(400, f"JSON 解析失败: {e}")
    try:
        counts = backup_service.restore_data(db, payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok", "counts": counts}


@router.get("/backup/full")
def get_backup_full(db: Session = Depends(get_db)):
    """ZIP containing JSON + attachments/ — complete backup with files."""
    body, filename = backup_service.export_full(db)
    return Response(
        content=body,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/restore/full")
async def post_restore_full(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Restore from a complete ZIP backup (JSON + attachment files)."""
    raw = await file.read(MAX_FULL_BACKUP_BYTES + 1)
    if len(raw) > MAX_FULL_BACKUP_BYTES:
        raise HTTPException(413, "备份 zip 超过 500MB 限制")
    try:
        counts = backup_service.restore_full(db, raw)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok", "counts": counts}
