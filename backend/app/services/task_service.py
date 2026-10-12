from sqlalchemy.orm import Session

from app.models import Task
from app.schemas import TaskCreate, TaskUpdate, TaskMove


def _validate_parent(db: Session, project_id: int, parent_id: int | None, task_id: int | None = None) -> None:
    if parent_id is None:
        return
    parent = db.get(Task, parent_id)
    if parent is None:
        raise ValueError("parent not found")
    if parent.project_id != project_id:
        raise ValueError("parent belongs to different project")
    if task_id is not None and parent_id == task_id:
        raise ValueError("task cannot be its own parent")
    if task_id is not None:
        cursor = parent_id
        while cursor is not None:
            if cursor == task_id:
                raise ValueError("would create cycle")
            node = db.get(Task, cursor)
            if node is None:
                break
            cursor = node.parent_id


def create_task(db: Session, data: TaskCreate) -> Task:
    if data.project_id is None:
        raise ValueError("project_id is required")
    _validate_parent(db, data.project_id, data.parent_id)
    t = Task(**data.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def list_project_tasks(db: Session, pid: int) -> list[Task]:
    return (
        db.query(Task)
        .filter(Task.project_id == pid)
        .order_by(Task.sort_order, Task.id)
        .all()
    )


def get_task(db: Session, tid: int) -> Task | None:
    return db.get(Task, tid)


def update_task(db: Session, t: Task, data: TaskUpdate) -> Task:
    updates = data.model_dump(exclude_unset=True)
    if "parent_id" in updates:
        _validate_parent(db, t.project_id, updates["parent_id"], task_id=t.id)
    for k, v in updates.items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


def move_task(db: Session, t: Task, data: TaskMove) -> Task:
    t.start_date = data.start_date
    t.end_date = data.end_date
    db.commit()
    db.refresh(t)
    return t


def delete_task(db: Session, t: Task) -> None:
    from app.services.attachment_service import delete_attachments_for_entity

    delete_attachments_for_entity(db, "task", t.id)
    db.delete(t)
    db.commit()
