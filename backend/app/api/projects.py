from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project
from app.schemas import ProjectCreate, ProjectUpdate, ProjectRead
from app.services import project_service
from app.services.excel_export import export_project_workbook

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    return project_service.list_projects(db)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    return project_service.create_project(db, data)


@router.get("/{pid}", response_model=ProjectRead)
def get_project(pid: int, db: Session = Depends(get_db)):
    p = project_service.get_project(db, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.patch("/{pid}", response_model=ProjectRead)
def update_project(pid: int, data: ProjectUpdate, db: Session = Depends(get_db)):
    p = project_service.get_project(db, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    return project_service.update_project(db, p, data)


@router.delete("/{pid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(pid: int, db: Session = Depends(get_db)):
    p = project_service.get_project(db, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    project_service.delete_project(db, p)
    return None


@router.get("/{pid}/export")
def export_project(pid: int, db: Session = Depends(get_db)):
    p = project_service.get_project(db, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    try:
        xlsx = export_project_workbook(db, pid)
    except Exception as exc:
        raise HTTPException(500, f"export failed: {exc}") from exc
    safe_name = p.name.encode("ascii", "ignore").decode("ascii") or "project"
    filename = f"project-{pid}-{safe_name}.xlsx"
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
