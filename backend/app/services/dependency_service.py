from sqlalchemy.orm import Session

from app.models import Task, TaskDependency
from app.services import task_service


def _creates_cycle(db: Session, predecessor_id: int, successor_id: int) -> bool:
    """True if adding predecessor->successor would create a directed cycle.

    Walk downstream from successor_id following predecessor->successor edges; if
    we ever reach predecessor_id, the new edge would close a loop.
    """
    visited: set[int] = set()
    stack = [successor_id]
    while stack:
        node = stack.pop()
        if node == predecessor_id:
            return True
        if node in visited:
            continue
        visited.add(node)
        downstream = (
            db.query(TaskDependency)
            .filter(TaskDependency.predecessor_id == node)
            .all()
        )
        stack.extend(d.successor_id for d in downstream)
    return False


def add_dependency(
    db: Session, successor_id: int, predecessor_id: int, dep_type: str
) -> tuple[TaskDependency, bool]:
    succ = task_service.get_task(db, successor_id)
    pred = task_service.get_task(db, predecessor_id)
    if not succ or not pred:
        raise LookupError("Task not found")

    if succ.id == pred.id:
        raise ValueError("Self-dependency not allowed")

    if succ.project_id != pred.project_id:
        raise ValueError("Dependency must be within the same project")

    existing = (
        db.query(TaskDependency)
        .filter(
            TaskDependency.predecessor_id == predecessor_id,
            TaskDependency.successor_id == successor_id,
        )
        .first()
    )
    if existing:
        return existing, False

    if _creates_cycle(db, predecessor_id, successor_id):
        raise ValueError("Dependency would create cycle")

    dep = TaskDependency(
        predecessor_id=predecessor_id,
        successor_id=successor_id,
        dep_type=dep_type,
    )
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep, True


def list_project_dependencies(db: Session, pid: int) -> list[TaskDependency]:
    return (
        db.query(TaskDependency)
        .join(Task, TaskDependency.successor_id == Task.id)
        .filter(Task.project_id == pid)
        .order_by(TaskDependency.id)
        .all()
    )


def delete_dependency(db: Session, dep_id: int) -> bool:
    dep = db.get(TaskDependency, dep_id)
    if not dep:
        return False
    db.delete(dep)
    db.commit()
    return True
