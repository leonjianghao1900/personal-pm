from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Cost, Task
from app.schemas import CostCreate, CostUpdate


def _validate_task_in_project(db: Session, project_id: int, task_id: int | None) -> None:
    if task_id is None:
        return
    t = db.get(Task, task_id)
    if not t:
        raise ValueError("任务不存在")
    if t.project_id != project_id:
        raise ValueError("任务不属于该项目")


def list_project_costs(db: Session, pid: int) -> list[Cost]:
    return (
        db.query(Cost)
        .filter(Cost.project_id == pid)
        .order_by(Cost.spent_at.desc(), Cost.id.desc())
        .all()
    )


def get_cost(db: Session, cid: int) -> Cost | None:
    return db.get(Cost, cid)


def create_cost(db: Session, data: CostCreate) -> Cost:
    _validate_task_in_project(db, data.project_id, data.task_id)
    c = Cost(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def update_cost(db: Session, c: Cost, data: CostUpdate) -> Cost:
    updates = data.model_dump(exclude_unset=True)
    new_project_id = updates.get("project_id", c.project_id)
    if "task_id" in updates:
        _validate_task_in_project(db, new_project_id, updates["task_id"])
    elif "project_id" in updates and c.task_id is not None:
        t = db.get(Task, c.task_id)
        if not t or t.project_id != new_project_id:
            updates["task_id"] = None
    for k, v in updates.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


def delete_cost(db: Session, c: Cost) -> None:
    from app.services.attachment_service import delete_attachments_for_entity

    delete_attachments_for_entity(db, "cost", c.id)
    db.delete(c)
    db.commit()


def cost_stats(db: Session, project_id: int | None = None) -> dict:
    query = db.query(Cost)
    if project_id is not None:
        query = query.filter(Cost.project_id == project_id)

    total = query.with_entities(func.coalesce(func.sum(Cost.amount), 0)).scalar() or 0.0

    by_category = dict(
        query.with_entities(Cost.category, func.sum(Cost.amount))
        .group_by(Cost.category)
        .all()
    )

    by_month_rows = (
        query.with_entities(func.strftime("%Y-%m", Cost.spent_at), func.sum(Cost.amount))
        .group_by(func.strftime("%Y-%m", Cost.spent_at))
        .order_by(func.strftime("%Y-%m", Cost.spent_at))
        .all()
    )
    by_month = {m: a for m, a in by_month_rows}

    return {
        "total": round(total, 2),
        "count": query.count(),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
        "by_month": {k: round(v, 2) for k, v in by_month.items()},
    }
