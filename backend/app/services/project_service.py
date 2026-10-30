from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Project, Task
from app.schemas import ProjectCreate, ProjectUpdate


def _task_counts(db: Session) -> dict[int, int]:
    """Map project_id -> number of tasks, in a single query."""
    rows = db.query(Task.project_id, func.count(Task.id)).group_by(Task.project_id).all()
    return {pid: count for pid, count in rows}


def create_project(db: Session, data: ProjectCreate) -> Project:
    p = Project(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    p.task_count = 0
    return p


def list_projects(db: Session) -> list[Project]:
    projects = db.query(Project).order_by(Project.id).all()
    counts = _task_counts(db)
    for p in projects:
        p.task_count = counts.get(p.id, 0)
    return projects


def get_project(db: Session, pid: int) -> Project | None:
    p = db.get(Project, pid)
    if p is not None:
        p.task_count = (
            db.query(func.count(Task.id)).filter(Task.project_id == pid).scalar() or 0
        )
    return p


def update_project(db: Session, p: Project, data: ProjectUpdate) -> Project:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    p.task_count = (
        db.query(func.count(Task.id)).filter(Task.project_id == p.id).scalar() or 0
    )
    return p


def delete_project(db: Session, p: Project) -> None:
    db.delete(p)
    db.commit()
