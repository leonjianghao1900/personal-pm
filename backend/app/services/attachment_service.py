"""Attachment storage service.

Files are stored on disk under ``{DATA_DIR}/attachments/{entity_type}/{entity_id}/{uuid}.{ext}``.
Only metadata is persisted in the ``attachments`` table.
"""
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import DATA_DIR
from app.models import Attachment

MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB

ENTITY_LIMITS: dict[str, int] = {
    "task": 10,
    "cost": 5,
    "inbox": 5,
}


def _safe_extension(filename: str) -> str:
    """Return lowercase extension without dot, or empty string.

    Strips any path components and caps length to avoid odd input.
    """
    name = Path(filename).name
    if "." not in name:
        return ""
    ext = name.rsplit(".", 1)[-1].lower()
    if not ext or len(ext) > 10 or not ext.replace("_", "").isalnum():
        return ""
    return ext


def _check_entity(entity_type: str) -> None:
    if entity_type not in ENTITY_LIMITS:
        raise HTTPException(400, f"不支持的实体类型: {entity_type}")


def _check_entity_exists(db: Session, entity_type: str, entity_id: int) -> None:
    """Verify the referenced entity actually exists (else: 404)."""
    from app.models import Cost, InboxItem, Task

    model_map = {"task": Task, "cost": Cost, "inbox": InboxItem}
    model = model_map[entity_type]
    if db.get(model, entity_id) is None:
        raise HTTPException(404, f"{entity_type} #{entity_id} 不存在")


async def save_attachment(
    db: Session,
    entity_type: str,
    entity_id: int,
    file: UploadFile,
) -> Attachment:
    _check_entity(entity_type)
    _check_entity_exists(db, entity_type, entity_id)

    content = await file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"文件超过 {MAX_FILE_BYTES // (1024 * 1024)} MB 限制",
        )

    existing = (
        db.query(Attachment)
        .filter(
            Attachment.entity_type == entity_type,
            Attachment.entity_id == entity_id,
        )
        .count()
    )
    if existing >= ENTITY_LIMITS[entity_type]:
        raise HTTPException(
            400,
            f"{entity_type} 附件已达上限 ({ENTITY_LIMITS[entity_type]} 个)",
        )

    ext = _safe_extension(file.filename or "")
    stored_name = f"{uuid.uuid4().hex}{('.' + ext) if ext else ''}"

    target_dir = DATA_DIR / "attachments" / entity_type / str(entity_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / stored_name

    with target.open("wb") as f:
        f.write(content)

    rel_path = target.relative_to(DATA_DIR).as_posix()

    attachment = Attachment(
        entity_type=entity_type,
        entity_id=entity_id,
        original_name=file.filename or stored_name,
        mime=file.content_type or "application/octet-stream",
        size=len(content),
        stored_path=rel_path,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def list_attachments(
    db: Session, entity_type: str, entity_id: int
) -> list[Attachment]:
    _check_entity(entity_type)
    return (
        db.query(Attachment)
        .filter(
            Attachment.entity_type == entity_type,
            Attachment.entity_id == entity_id,
        )
        .order_by(Attachment.uploaded_at.desc())
        .all()
    )


def get_attachment(db: Session, attachment_id: int) -> Attachment:
    att = db.get(Attachment, attachment_id)
    if not att:
        raise HTTPException(404, "附件不存在")
    return att


def delete_attachment(db: Session, attachment_id: int) -> None:
    att = get_attachment(db, attachment_id)
    file_path = DATA_DIR / att.stored_path
    try:
        file_path.unlink()
    except FileNotFoundError:
        pass
    db.delete(att)
    db.commit()


def delete_attachments_for_entity(
    db: Session, entity_type: str, entity_id: int
) -> int:
    """Remove all attachments (files + DB rows) for an entity.

    Returns number of attachments removed.  Called when the parent
    entity is deleted (cascade).
    """
    rows = (
        db.query(Attachment)
        .filter(
            Attachment.entity_type == entity_type,
            Attachment.entity_id == entity_id,
        )
        .all()
    )
    for row in rows:
        try:
            (DATA_DIR / row.stored_path).unlink()
        except FileNotFoundError:
            pass
        db.delete(row)
    if rows:
        db.commit()
    return len(rows)


def attachments_root() -> Path:
    p = DATA_DIR / "attachments"
    p.mkdir(parents=True, exist_ok=True)
    return p
