from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import TaskCreate, TaskUpdate, TaskRead, TaskMove
from app.services import task_service, project_service

router = APIRouter(tags=["tasks"])


@router.get("/api/projects/{pid}/tasks", response_model=list[TaskRead])
def list_project_tasks(pid: int, db: Session = Depends(get_db)):
    if not project_service.get_project(db, pid):
        raise HTTPException(404, "Project not found")
    return task_service.list_project_tasks(db, pid)


@router.post("/api/projects/{pid}/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(pid: int, data: TaskCreate, db: Session = Depends(get_db)):
    if not project_service.get_project(db, pid):
        raise HTTPException(404, "Project not found")
    payload = data.model_copy(update={"project_id": pid})
    try:
        return task_service.create_task(db, payload)
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/api/tasks/{tid}", response_model=TaskRead)
def get_task(tid: int, db: Session = Depends(get_db)):
    t = task_service.get_task(db, tid)
    if not t:
        raise HTTPException(404, "Task not found")
    return t


@router.patch("/api/tasks/{tid}", response_model=TaskRead)
def update_task(tid: int, data: TaskUpdate, db: Session = Depends(get_db)):
    t = task_service.get_task(db, tid)
    if not t:
        raise HTTPException(404, "Task not found")
    try:
        return task_service.update_task(db, t, data)
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.post("/api/tasks/{tid}/move", response_model=TaskRead)
def move_task(tid: int, data: TaskMove, db: Session = Depends(get_db)):
    t = task_service.get_task(db, tid)
    if not t:
        raise HTTPException(404, "Task not found")
    return task_service.move_task(db, t, data)


@router.delete("/api/tasks/{tid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(tid: int, db: Session = Depends(get_db)):
    t = task_service.get_task(db, tid)
    if not t:
        raise HTTPException(404, "Task not found")
    task_service.delete_task(db, t)
    return None
