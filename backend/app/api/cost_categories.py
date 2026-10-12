from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CostCategoryCreate, CostCategoryRead, CostCategoryUpdate
from app.services import cost_category_service

router = APIRouter(prefix="/api/cost-categories", tags=["cost-categories"])


@router.get("", response_model=list[CostCategoryRead])
def list_categories(db: Session = Depends(get_db)):
    return cost_category_service.list_categories(db)


@router.post("", response_model=CostCategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(data: CostCategoryCreate, db: Session = Depends(get_db)):
    try:
        return cost_category_service.create_category(db, data)
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.patch("/{cid}", response_model=CostCategoryRead)
def update_category(cid: int, data: CostCategoryUpdate, db: Session = Depends(get_db)):
    c = cost_category_service.get_category(db, cid)
    if not c:
        raise HTTPException(404, "Category not found")
    try:
        return cost_category_service.update_category(db, c, data)
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.delete("/{cid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(cid: int, db: Session = Depends(get_db)):
    c = cost_category_service.get_category(db, cid)
    if not c:
        raise HTTPException(404, "Category not found")
    try:
        cost_category_service.delete_category(db, c)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return None