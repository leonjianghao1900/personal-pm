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

__all__ = [
    "admin_router",
    "projects_router",
    "tasks_router",
    "deps_router",
    "costs_router",
    "inbox_router",
    "categories_router",
    "stats_router",
    "attachments_router",
    "updates_router",
]
