from fastapi import APIRouter

from app.services import update_service

router = APIRouter(prefix="/api/updates", tags=["updates"])


@router.get("/check")
def check_update(force: bool = False):
    return update_service.check_for_update(force=force)
