from sqlalchemy.orm import Session

from app.models import Cost, CostCategory
from app.schemas import CostCategoryCreate, CostCategoryUpdate


def list_categories(db: Session) -> list[CostCategory]:
    return db.query(CostCategory).order_by(CostCategory.sort_order, CostCategory.id).all()


def get_category(db: Session, cid: int) -> CostCategory | None:
    return db.get(CostCategory, cid)


def create_category(db: Session, data: CostCategoryCreate) -> CostCategory:
    if db.query(CostCategory).filter(CostCategory.name == data.name).first():
        raise ValueError("类别名已存在")
    c = CostCategory(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def update_category(db: Session, c: CostCategory, data: CostCategoryUpdate) -> CostCategory:
    updates = data.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] != c.name:
        if db.query(CostCategory).filter(CostCategory.name == updates["name"]).first():
            raise ValueError("类别名已存在")
    old_name = c.name
    new_name = updates.get("name")
    if new_name is not None and new_name != old_name:
        db.query(Cost).filter(Cost.category == old_name).update(
            {Cost.category: new_name}, synchronize_session=False
        )
    for k, v in updates.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


def delete_category(db: Session, c: CostCategory) -> None:
    used = db.query(Cost).filter(Cost.category == c.name).count()
    if used > 0:
        raise ValueError(f"该类别已被 {used} 笔费用使用")
    db.delete(c)
    db.commit()
