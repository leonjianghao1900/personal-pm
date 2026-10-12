from sqlalchemy.orm import Session

from app.models import Project
from app.schemas import ProjectCreate, ProjectUpdate


def create_project(db: Session, data: ProjectCreate) -> Project:
    p = Project(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def list_projects(db: Session) -> list[Project]:
    return db.query(Project).order_by(Project.id).all()


def get_project(db: Session, pid: int) -> Project | None:
    return db.get(Project, pid)


def update_project(db: Session, p: Project, data: ProjectUpdate) -> Project:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


def delete_project(db: Session, p: Project) -> None:
    db.delete(p)
    db.commit()
