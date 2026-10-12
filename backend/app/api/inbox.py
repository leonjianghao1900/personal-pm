from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import InboxCreate, InboxPromote, InboxRead, InboxUpdate
from app.services import inbox_service

router = APIRouter(prefix="/api/inbox", tags=["inbox"])


@router.get("", response_model=list[InboxRead])
def list_inbox(kind: str | None = None, db: Session = Depends(get_db)):
    return inbox_service.list_inbox(db, kind)


@router.post("", response_model=InboxRead, status_code=status.HTTP_201_CREATED)
def create_inbox(data: InboxCreate, db: Session = Depends(get_db)):
    return inbox_service.create_inbox_item(db, data)


@router.patch("/{iid}", response_model=InboxRead)
def update_inbox(iid: int, data: InboxUpdate, db: Session = Depends(get_db)):
    item = inbox_service.get_inbox_item(db, iid)
    if not item:
        raise HTTPException(404, "Inbox item not found")
    return inbox_service.update_inbox_item(db, item, data)


@router.post("/{iid}/promote", response_model=InboxRead)
def promote_inbox(iid: int, data: InboxPromote, db: Session = Depends(get_db)):
    item = inbox_service.get_inbox_item(db, iid)
    if not item:
        raise HTTPException(404, "Inbox item not found")
    try:
        _, item = inbox_service.promote_inbox_item(db, item, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return item


@router.delete("/{iid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inbox(iid: int, db: Session = Depends(get_db)):
    item = inbox_service.get_inbox_item(db, iid)
    if not item:
        raise HTTPException(404, "Inbox item not found")
    inbox_service.delete_inbox_item(db, item)
    return None