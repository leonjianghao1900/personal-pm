from datetime import date

from sqlalchemy.orm import Session

from app.models import Cost, Project, Task


def _compute_progress(tasks: list[Task]) -> int:
    """叶子任务权重为 1，父任务权重 = 子任务权重和。进度 = 已完成叶子权重 / 总叶子权重。"""
    children: dict[int | None, list[Task]] = {}
    for t in tasks:
        children.setdefault(t.parent_id, []).append(t)

    def weight(t: Task) -> int:
        subs = children.get(t.id, [])
        if not subs:
            return 1
        return sum(weight(s) for s in subs)

    def done_weight(t: Task) -> int:
        if t.status == "done":
            return weight(t)
        return sum(done_weight(s) for s in children.get(t.id, []))

    total = sum(weight(t) for t in children.get(None, []))
    if total == 0:
        return 0
    done = sum(done_weight(t) for t in children.get(None, []))
    return round(done / total * 100)


def get_overview(db: Session) -> dict:
    today = date.today()
    projects = db.query(Project).order_by(Project.id).all()
    tasks = db.query(Task).all()

    active_tasks = sum(1 for t in tasks if t.status == "progress")
    delayed_tasks = sum(1 for t in tasks if t.status == "delayed")

    month_key = f"{today.year:04d}-{today.month:02d}"
    this_month_cost = round(
        sum(c.amount for c in db.query(Cost).all() if c.spent_at.strftime("%Y-%m") == month_key),
        2,
    )

    project_rows = []
    for p in projects:
        ptasks = [t for t in tasks if t.project_id == p.id]
        total = len(ptasks)
        done = sum(1 for t in ptasks if t.status == "done")
        due = [
            t for t in ptasks
            if t.end_date is not None and t.end_date >= today
            and t.status not in ("done", "cancelled")
        ]
        next_due = min(due, key=lambda t: t.end_date) if due else None
        project_rows.append({
            "id": p.id,
            "name": p.name,
            "color": p.color,
            "task_total": total,
            "task_done": done,
            "progress": _compute_progress(ptasks),
            "next_due_task": {
                "id": next_due.id,
                "name": next_due.name,
                "end_date": next_due.end_date.isoformat(),
            } if next_due else None,
        })

    return {
        "project_count": len(projects),
        "active_task_count": active_tasks,
        "delayed_task_count": delayed_tasks,
        "this_month_cost": this_month_cost,
        "projects": project_rows,
    }
