from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DependencyCreate, DependencyRead
from app.services import dependency_service, project_service

router = APIRouter(tags=["dependencies"])


@router.get("/api/projects/{pid}/dependencies", response_model=list[DependencyRead])
def list_project_dependencies(pid: int, db: Session = Depends(get_db)):
    if not project_service.get_project(db, pid):
        raise HTTPException(404, "Project not found")
    return dependency_service.list_project_dependencies(db, pid)


@router.post("/api/tasks/{tid}/dependencies", response_model=DependencyRead)
def add_dependency(
    tid: int,
    data: DependencyCreate,
    db: Session = Depends(get_db),
    response: Response = None,
):
    try:
        dep, created = dependency_service.add_dependency(
            db, tid, data.predecessor_id, data.dep_type
        )
    except LookupError:
        raise HTTPException(404, "Task not found")
    except ValueError as e:
        raise HTTPException(400, str(e))
    if created:
        response.status_code = status.HTTP_201_CREATED
    return dep


@router.delete("/api/dependencies/{dep_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dependency(dep_id: int, db: Session = Depends(get_db)):
    if not dependency_service.delete_dependency(db, dep_id):
        raise HTTPException(404, "Dependency not found")
    return None
