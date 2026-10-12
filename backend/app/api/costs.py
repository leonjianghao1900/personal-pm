from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Cost
from app.schemas import CostCreate, CostRead, CostUpdate
from app.services import cost_service, project_service

router = APIRouter(tags=["costs"])


@router.get("/api/projects/{pid}/costs", response_model=list[CostRead])
def list_project_costs(pid: int, db: Session = Depends(get_db)):
    if not project_service.get_project(db, pid):
        raise HTTPException(404, "Project not found")
    return cost_service.list_project_costs(db, pid)


@router.post("/api/costs", response_model=CostRead, status_code=status.HTTP_201_CREATED)
def create_cost(data: CostCreate, db: Session = Depends(get_db)):
    if not project_service.get_project(db, data.project_id):
        raise HTTPException(404, "Project not found")
    try:
        return cost_service.create_cost(db, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.patch("/api/costs/{cid}", response_model=CostRead)
def update_cost(cid: int, data: CostUpdate, db: Session = Depends(get_db)):
    c: Cost | None = cost_service.get_cost(db, cid)
    if not c:
        raise HTTPException(404, "Cost not found")
    try:
        return cost_service.update_cost(db, c, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/api/costs/{cid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cost(cid: int, db: Session = Depends(get_db)):
    c = cost_service.get_cost(db, cid)
    if not c:
        raise HTTPException(404, "Cost not found")
    cost_service.delete_cost(db, c)
    return None


@router.get("/api/stats/costs")
def cost_stats(
    project_id: int | None = None, db: Session = Depends(get_db)
):
    return cost_service.cost_stats(db, project_id)