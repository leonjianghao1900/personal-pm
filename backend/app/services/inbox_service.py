from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import InboxItem, Task
from app.schemas import InboxCreate, InboxPromote, InboxUpdate


def list_inbox(db: Session, kind: str | None = None) -> list[InboxItem]:
    query = db.query(InboxItem)
    if kind:
        query = query.filter(InboxItem.kind == kind)
    return query.order_by(InboxItem.created_at.desc()).all()


def get_inbox_item(db: Session, iid: int) -> InboxItem | None:
    return db.get(InboxItem, iid)


def create_inbox_item(db: Session, data: InboxCreate) -> InboxItem:
    item = InboxItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_inbox_item(db: Session, item: InboxItem, data: InboxUpdate) -> InboxItem:
    updates = data.model_dump(exclude_unset=True)
    if "status" in updates:
        new_status = updates["status"]
        if new_status == "completed" and item.status != "completed":
            item.completed_at = datetime.utcnow()
        if new_status != "completed":
            item.completed_at = None
    for k, v in updates.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


def promote_inbox_item(
    db: Session, item: InboxItem, data: InboxPromote
) -> tuple[Task, InboxItem]:
    from app.schemas import TaskCreate

    project_id = data.project_id or item.project_id
    if project_id is None:
        raise ValueError("project_id is required to promote")

    start = date.fromisoformat(data.start_date) if data.start_date else date.today()
    end = (
        date.fromisoformat(data.end_date)
        if data.end_date
        else start + timedelta(days=1)
    )

    payload = TaskCreate(
        project_id=project_id,
        name=data.name or item.title,
        priority=item.priority,
        start_date=start,
        end_date=end,
    )
    t = Task(**payload.model_dump())
    db.add(t)
    db.flush()

    item.promoted_task_id = t.id
    item.status = "archived"
    db.commit()
    db.refresh(t)
    db.refresh(item)
    return t, item


def delete_inbox_item(db: Session, item: InboxItem) -> None:
    from app.services.attachment_service import delete_attachments_for_entity

    delete_attachments_for_entity(db, "inbox", item.id)
    db.delete(item)
    db.commit()