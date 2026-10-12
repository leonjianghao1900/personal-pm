from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.projects import router as projects_router
from app.api.tasks import router as tasks_router
from app.api.dependencies import router as deps_router
from app.api.costs import router as costs_router
from app.api.inbox import router as inbox_router
from app.api.cost_categories import router as categories_router
from app.api.stats import router as stats_router
from app.api.attachments import router as attachments_router
from app.api.updates import router as updates_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import engine
    from app.models.base import Base
    from app import models
    Base.metadata.create_all(engine)
    # 一次性迁移：老库加新列
    from scripts.migrate_add_desc_and_taskid import migrate
    migrate(engine)
    from scripts.migrate_drop_builtin_flag import migrate as drop_builtin
    drop_builtin(engine)
    from scripts import migrate_add_cost_name
    migrate_add_cost_name.migrate(engine)
    from scripts import migrate_add_attachments
    migrate_add_attachments.migrate(engine)
    yield


app = FastAPI(title="Personal PM", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(deps_router)
app.include_router(costs_router)
app.include_router(inbox_router)
app.include_router(categories_router)
app.include_router(stats_router)
app.include_router(attachments_router)
app.include_router(updates_router)
app.include_router(admin_router)


DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
INDEX = DIST / "index.html"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/version")
def version():
    from app.version import APP_VERSION, BUILD_TIME
    return {"version": APP_VERSION, "build_time": BUILD_TIME}


if INDEX.exists():
    assets = DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        """SPA 回退：非 /api 路径一律返回 index.html，由前端路由接管。"""
        candidate = DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(INDEX)
