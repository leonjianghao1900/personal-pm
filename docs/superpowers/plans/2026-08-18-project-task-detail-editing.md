# 项目/任务详情编辑 + 费用关联任务 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让项目能起止日期与描述可编辑、任务描述可编辑、费用可选关联任务。

**Architecture:** 后端给 `Project` 加 `description` 列、`Cost` 加 `task_id` 列（FK → tasks，SET NULL 级联）。一次性迁移脚本（lifespan 调用，幂等）。前端新建 `ProjectPanel.vue` 侧滑抽屉（编辑项目）；`TaskDetailView` 描述区改内联编辑；`CostsView` 表单多任务下拉、明细表多列。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + SQLite；Vue 3 + Vite + Tailwind + Pinia；pytest；vue-tsc。

---

## 文件结构

**后端（`backend/`）**
- Modify: `app/models/project.py` — 加 `description`
- Modify: `app/models/cost.py` — 加 `task_id` FK
- Modify: `app/schemas/project.py` — description 进 base/create/update/read
- Modify: `app/schemas/cost.py` — task_id 进 base/create/update/read
- Modify: `app/services/cost_service.py` — create/update 校验 task 必须属于同一 project
- Create: `scripts/migrate_add_desc_and_taskid.py` — 一次性迁移（幂等）
- Modify: `app/main.py` — lifespan 中调用迁移脚本
- Create: `tests/test_project_description.py`
- Modify: `tests/test_costs.py` — 加 task_id 测试

**前端（`frontend/`）**
- Create: `src/components/ProjectPanel.vue` — 侧滑面板（编辑/删除项目）
- Modify: `src/views/GanttView.vue` — 顶部项目名变可点击；新建项目对话框升级为多字段
- Modify: `src/views/TaskDetailView.vue` — 描述区改内联编辑
- Modify: `src/views/CostsView.vue` — 表单多任务下拉 + 明细表多任务列
- Modify: `src/api/types.ts` — `Project.description`、`Cost.task_id`
- Modify: `src/api/client.ts` — `ProjectUpdate` 含 description；`CostInput` 含 task_id

---

### Task 1: Project 加 description 字段（后端模型 + schema）

**Files:**
- Modify: `backend/app/models/project.py`
- Modify: `backend/app/schemas/project.py`

- [ ] **Step 1: 修改 Project 模型**

`backend/app/models/project.py` 在 `name` 行后加：
```python
    description: Mapped[str | None] = mapped_column(String(2000), default=None)
```
完整文件：
```python
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#0071e3")
    description: Mapped[str | None] = mapped_column(String(2000), default=None)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )
    costs: Mapped[list["Cost"]] = relationship(
        "Cost", back_populates="project", cascade="all, delete-orphan"
    )
```

- [ ] **Step 2: 修改 ProjectBase/Create/Update/Read schema**

`backend/app/schemas/project.py` 完整替换：
```python
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default="#0071e3", max_length=20)
    description: str | None = Field(default=None, max_length=2000)
    start_date: date | None = None
    end_date: date | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=2000)
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 3: 验证导入**

Run: `backend\.venv\Scripts\python.exe -c "from app.models import Project; from app.schemas import ProjectRead; print(Projecthasattr(ProjectRead, 'model_fields') and 'description' in ProjectRead.model_fields)"
Expected: `True`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/project.py backend/app/schemas/project.py
git commit -m "feat: add Project.description field"
```

---

### Task 2: Cost 加 task_id 字段（后端模型 + schema）

**Files:**
- Modify: `backend/app/models/cost.py`
- Modify: `backend/app/schemas/cost.py`

- [ ] **Step 1: 修改 Cost 模型**

`backend/app/models/cost.py` 完整替换：
```python
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Cost(Base):
    __tablename__ = "costs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )
    category: Mapped[str] = mapped_column(String(20), default="other", nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    spent_at: Mapped[date] = mapped_column(Date, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="costs")
```

- [ ] **Step 2: 修改 CostBase/Create/Update/Read schema**

`backend/app/schemas/cost.py` 完整替换：
```python
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CostBase(BaseModel):
    category: str = Field("other", max_length=20)
    amount: float = Field(gt=0)
    description: str | None = None
    spent_at: date


    task_id: int | None = None


class CostCreate(CostBase):
    project_id: int


class CostUpdate(BaseModel):
    category: str | None = Field(default=None, max_length=20)
    amount: float | None = Field(default=None, gt=0)
    description: str | None = None
    spent_at: date | None = None
    task_id: int | None = None


class CostRead(CostBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime
```

- [ ] **Step 3: 验证导入**

Run: `backend\.venv\Scripts\python.exe -c "from app.models import Cost; from app.schemas import CostRead; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/cost.py backend/app/schemas/cost.py
git commit -m "feat: add Cost.task_id field"
```

---

### Task 3: cost_service 加 task_id 跨项目校验

**Files:**
- Modify: `backend/app/services/cost_service.py`
- Modify: `backend/app/api/costs.py`（wrap ValueError → 400）

- [ ] **Step 1: 引入 Task 并修改 create_cost/update_cost**

`backend/app/services/cost_service.py` 完整替换：
```python
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Cost, Task
from app.schemas import CostCreate, CostUpdate


def _validate_task_in_project(db: Session, project_id: int, task_id: int | None) -> None:
    if task_id is None:
        return
    t = db.get(Task, task_id)
    if not t:
        raise ValueError("任务不存在")
    if t.project_id != project_id:
        raise ValueError("任务不属于该项目")


def list_project_costs(db: Session, pid: int) -> list[Cost]:
    return (
        db.query(Cost)
        .filter(Cost.project_id == pid)
        .order_by(Cost.spent_at.desc(), Cost.id.desc())
        .all()
    )


def get_cost(db: Session, cid: int) -> Cost | None:
    return db.get(Cost, cid)


def create_cost(db: Session, data: CostCreate) -> Cost:
    _validate_task_in_project(db, data.project_id, data.task_id)
    c = Cost(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def update_cost(db: Session, c: Cost, data: CostUpdate) -> Cost:
    updates = data.model_dump(exclude_unset=True)
    if "task_id" in updates:
        _validate_task_in_project(db, c.project_id, updates["task_id"])
    for k, v in updates.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


def delete_cost(db: Session, c: Cost) -> None:
    db.delete(c)
    db.commit()


def cost_stats(db: Session, project_id: int | None = None) -> dict:
    query = db.query(Cost)
    if project_id is not None:
        query = query.filter(Cost.project_id == project_id)

    total = query.with_entities(func.coalesce(func.sum(Cost.amount), 0)).scalar() or 0.0

    by_category = dict(
        query.with_entities(Cost.category, func.sum(Cost.amount))
        .group_by(Cost.category)
        .all()
    )

    by_month_rows = (
        query.with_entities(func.strftime("%Y-%m", Cost.spent_at), func.sum(Cost.amount))
        .group_by(func.strftime("%Y-%m", Cost.spent_at))
        .order_by(func.strftime("%Y-%m", Cost.spent_at))
        .all()
    )
    by_month = {m: a for m, a in by_month_rows}

    return {
        "total": round(total, 2),
        "count": query.count(),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
        "by_month": {k: round(v, 2) for k, v in by_month.items()},
    }
```

注：上面是完整替换版本。

正确版本：
```python
def _validate_task_in_project(db: Session, project_id: int, task_id: int | None) -> None:
    if task_id is None:
        return
    t = db.get(Task, task_id)
    if not t:
        raise ValueError("任务不存在")
    if t.project_id != project_id:
        raise ValueError("任务不属于该项目")
```

- [ ] **Step 1.5: 在 api/costs.py wrap ValueError → 400**

`backend/app/api/costs.py` 修改两个端点，让 `ValueError` 转 400（不是 409，因为 task 不存在是请求级错误，不是状态冲突）。完整文件：
```python
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
```

- [ ] **Step 2: 验证 import + 全测试仍过**

Run: `.venv\Scripts\python.exe -m pytest -q`（workdir `backend`）
Expected: 73 passed（不变，因为还没新增 task_id 测试）

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/cost_service.py backend/app/api/costs.py
git commit -m "feat: validate Cost.task_id belongs to project (service + 400 wrap)"
```

---

### Task 4: 一次性迁移脚本

**Files:**
- Create: `backend/scripts/__init__.py`（空）
- Create: `backend/scripts/migrate_add_desc_and_taskid.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建空 package init**

`backend/scripts/__init__.py` 内容：
```python
```

- [ ] **Step 2: 写迁移脚本**

`backend/scripts/migrate_add_desc_and_taskid.py`：
```python
"""一次性迁移：为 projects 加 description，为 costs 加 task_id。

幂等：字段已存在则跳过。
对全新数据库（首次 create_all）也会先尝试 ALTER，失败无害（因为字段已存在）。
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.database import engine


def column_exists(table_name: str, column_name: str, eng: Engine) -> bool:
    insp = inspect(eng)
    cols = {c["name"] for c in insp.get_columns(table_name)}
    return column_name in cols


def has_foreign_key(table_name: str, column_name: str, eng: Engine) -> bool:
    insp = inspect(eng)
    for fk in insp.get_foreign_keys(table_name):
        if column_name in fk.get("constrained_columns", []):
            return True
    return False


def migrate(engine: Engine) -> None:
    # projects.description
    if not column_exists("projects", "description", engine):
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE projects ADD COLUMN description VARCHAR(2000)"))

    # costs.task_id + FK
    if not column_exists("costs", "task_id", engine):
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE costs ADD COLUMN task_id INTEGER"))
            # SQLite 不支持 ALTER TABLE ADD CONSTRAINT；FK 在 create_all 时已建（如果表新）
            # 对老表，FK 在每次连接时通过 PRAGMA foreign_keys=ON 强制；这里只补列即可

    # 重创建索引（如缺）
    with engine.begin() as conn:
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_costs_task_id ON costs (task_id)"))
        except Exception:
            pass


if __name__ == "__main__":
    migrate(engine)
    print("migration done")
```

- [ ] **Step 3: 在 lifespan 中调用迁移**

`backend/app/main.py` 完整替换：
```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.projects import router as projects_router
from app.api.tasks import router as tasks_router
from app.api.dependencies import router as deps_router
from app.api.costs import router as costs_router
from app.api.inbox import router as inbox_router
from app.api.cost_categories import router as categories_router
from app.api.stats import router as stats_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import engine, SessionLocal
    from app.models.base import Base
    from app import models
    Base.metadata.create_all(engine)
    # 一次性迁移：老库加新列
    from scripts.migrate_add_desc_and_taskid import migrate
    migrate(engine)
    from app.services.cost_category_service import seed_builtin_categories
    with SessionLocal() as session:
        seed_builtin_categories(session)
    yield


app = FastAPI(title="Personal PM", version="0.1.0", lifespan=lifespan)

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


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: 手动验证迁移（对真实 DB）**

Run: `backend\.venv\Scripts\python.exe scripts\migrate_add_desc_and_taskid.py`
Expected: `migration done`

再跑一次：
Run: `backend\.venv\Scripts\python.exe scripts\migrate_add_desc_and_taskid.py`
Expected: `migration done`（幂等，无报错）

- [ ] **Step 5: Commit**

```bash
git add backend/scripts backend/app/main.py
git commit -m "feat: one-shot migration for Project.description and Cost.task_id"
```

---

### Task 5: Project description 测试

**Files:**
- Create: `backend/tests/test_project_description.py`

- [ ] **Step 1: 写测试**

`backend/tests/test_project_description.py`：
```python
def test_create_project_with_description(client, db_session):
    r = client.post("/api/projects", json={"name": "P", "description": "一个测试项目"})
    assert r.status_code == 201, r.text
    assert r.json()["description"] == "一个测试项目"


def test_update_project_description(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    r = client.patch(f"/api/projects/{pid}", json={"description": "新描述"})
    assert r.status_code == 200
    assert r.json()["description"] == "新描述"


def test_project_description_null_by_default(client, db_session):
    r = client.post("/api/projects", json={"name": "P"})
    assert r.json()["description"] is None


def test_project_description_too_long_422(client, db_session):
    r = client.post("/api/projects", json={"name": "P", "description": "x" * 2001})
    assert r.status_code == 422


def test_project_description_in_list(client, db_session):
    pid = client.post("/api/projects", json={"name": "P", "description": "abc"}).json()["id"]
    r = client.get("/api/projects")
    assert r.json()[0]["description"] == "abc"
```

- [ ] **Step 2: 运行测试**

Run: `.venv\Scripts\python.exe -m pytest tests/test_project_description.py -v`（workdir `backend`）
Expected: 5 passed

- [ ] **Step 3: 全量回归**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 73 原有 + 5 新 = 78 passed

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_project_description.py
git commit -m "test: Project.description CRUD"
```

---

### Task 6: Cost task_id 测试

**Files:**
- Modify: `backend/tests/test_costs.py`（追加用例）

- [ ] **Step 1: 在文件末尾追加 5 个测试**

`backend/tests/test_costs.py` 末尾追加：
```python


def test_create_cost_with_task(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    r = client.post("/api/costs", json={
        "project_id": pid, "category": "other", "amount": 10,
        "spent_at": "2026-08-01", "task_id": tid,
    })
    assert r.status_code == 201, r.text
    assert r.json()["task_id"] == tid


def test_cost_with_cross_project_task_400(client, db_session):
    p1 = client.post("/api/projects", json={"name": "P1"}).json()["id"]
    p2 = client.post("/api/projects", json={"name": "P2"}).json()["id"]
    t1 = client.post(f"/api/projects/{p1}/tasks", json={"name": "T"}).json()["id"]
    r = client.post("/api/costs", json={
        "project_id": p2, "category": "other", "amount": 10,
        "spent_at": "2026-08-01", "task_id": t1,
    })
    assert r.status_code == 400
    assert "任务不属于该项目" in r.json()["detail"]


def test_update_cost_task_id(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    t1 = client.post(f"/api/projects/{pid}/tasks", json={"name": "T1"}).json()["id"]
    t2 = client.post(f"/api/projects/{pid}/tasks", json={"name": "T2"}).json()["id"]
    cid = client.post("/api/costs", json={
        "project_id": pid, "category": "other", "amount": 10,
        "spent_at": "2026-08-01", "task_id": t1,
    }).json()["id"]
    r = client.patch(f"/api/costs/{cid}", json={"task_id": t2})
    assert r.status_code == 200
    assert r.json()["task_id"] == t2


def test_delete_task_sets_cost_task_id_null(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    cid = client.post("/api/costs", json={
        "project_id": pid, "category": "other", "amount": 10,
        "spent_at": "2026-08-01", "task_id": tid,
    }).json()["id"]
    client.delete(f"/api/tasks/{tid}")
    r = client.get(f"/api/projects/{pid}/costs")
    found = next(c for c in r.json() if c["id"] == cid)
    assert found["task_id"] is None


def test_cost_without_task_id_ok(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    r = client.post("/api/costs", json={
        "project_id": pid, "category": "other", "amount": 10, "spent_at": "2026-08-01"
    })
    assert r.status_code == 201
    assert r.json()["task_id"] is None
```

注：上面是完整版本。

正确：
```python
    r = client.get(f"/api/projects/{pid}/costs")
    found = next(c for c in r.json() if c["id"] == cid)
    assert found["task_id"] is None
```

- [ ] **Step 2: 运行测试**

Run: `.venv\Scripts\python.exe -m pytest tests/test_costs.py -v`（workdir `backend`）
Expected: 11 原有 + 5 新 = 16 passed

- [ ] **Step 3: 全量回归**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 78 + 5 = 83 passed

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_costs.py
git commit -m "test: Cost.task_id CRUD + cross-project validation + SET NULL cascade"
```

---

### Task 7: 前端类型 + API client 更新

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 修改 types.ts**

`frontend/src/api/types.ts` 在 `Project` 接口 `status` 行后加：
```typescript
  description: string | null
```

在 `Cost` 接口 `project_id` 行后加：
```typescript
  task_id: number | null
```

完整 Project 接口（参考）：
```typescript
export interface Project {
  id: number
  name: string
  color: string
  description: string | null
  start_date: string | null
  end_date: string | null
  status: ProjectStatus
  created_at: string
  updated_at: string
}
```

完整 Cost 接口：
```typescript
export interface Cost {
  id: number
  project_id: number
  task_id: number | null
  category: CostCategory
  amount: number
  description: string | null
  spent_at: string
  created_at: string
}
```

- [ ] **Step 2: 修改 client.ts**

`frontend/src/api/client.ts` 在 `projectsApi.update` 的 `Pick<Project, ...>` 类型签名中加入 `description`：

找到：
```typescript
  update: (id: number, data: Partial<Pick<Project, 'name' | 'color' | 'start_date' | 'end_date' | 'status'>>) =>
```
改成：
```typescript
  update: (id: number, data: Partial<Pick<Project, 'name' | 'color' | 'description' | 'start_date' | 'end_date' | 'status'>>) =>
```

在 `CostInput` 的 `Pick<Cost, ...>` 中加 `task_id`：

找到：
```typescript
export type CostInput = Partial<
  Pick<Cost, 'category' | 'amount' | 'description' | 'spent_at'>
>
```
改成：
```typescript
export type CostInput = Partial<
  Pick<Cost, 'category' | 'amount' | 'description' | 'spent_at' | 'task_id'>
>
```

- [ ] **Step 3: 构建验证**

Run: `npm run build`（workdir `frontend`）
Expected: vue-tsc + vite build 通过

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/client.ts
git commit -m "feat(frontend): Project.description + Cost.task_id types"
```

---

### Task 8: ProjectPanel 侧滑面板组件

**Files:**
- Create: `frontend/src/components/ProjectPanel.vue`

- [ ] **Step 1: 写组件**

`frontend/src/components/ProjectPanel.vue`：
```vue
<template>
  <Teleport to="body">
    <Transition name="slide">
      <div v-if="open"
           class="fixed inset-0 z-50 flex justify-end"
           @click.self="onCancel">
        <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" @click="onCancel"></div>
        <GlassCard class="relative w-[440px] h-full overflow-y-auto p-6 rounded-none border-r-0">
          <div class="flex items-center justify-between mb-5">
            <h3 class="text-xl font-bold">{{ isEditing ? '编辑项目' : '新建项目' }}</h3>
            <button @click="onCancel" class="w-8 h-8 rounded-lg bg-black/5 hover:bg-black/10 flex items-center justify-center">✕</button>
          </div>

          <label class="block text-xs text-gray-500 mb-1">项目名</label>
          <input ref="nameInput" v-model="form.name" placeholder="项目名"
                 @keyup.enter="onSave"
                 class="w-full px-3 py-2 rounded-lg border border-black/10 mb-4 bg-white/70" />

          <label class="block text-xs text-gray-500 mb-1">颜色</label>
          <div class="flex items-center gap-2 mb-4">
            <button v-for="c in presetColors" :key="c"
                    @click="form.color = c"
                    class="w-7 h-7 rounded-full border-2"
                    :class="form.color === c ? 'border-apple-blue' : 'border-white'"
                    :style="{ background: c }"></button>
          </div>

          <div class="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label class="block text-xs text-gray-500 mb-1">开始日期</label>
              <input v-model="form.start_date" type="date"
                     class="w-full px-3 py-2 rounded-lg border border-black/10 bg-white/70 text-sm" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">截止日期</label>
              <input v-model="form.end_date" type="date"
                     class="w-full px-3 py-2 rounded-lg border border-black/10 bg-white/70 text-sm" />
            </div>
          </div>

          <label class="block text-xs text-gray-500 mb-1">备注</label>
          <textarea v-model="form.description" rows="6" placeholder="项目的目标、范围、关键节点…"
                    class="w-full px-3 py-2 rounded-lg border border-black/10 mb-5 bg-white/70 resize-none"></textarea>

          <div class="flex gap-2 justify-between pt-4 border-t border-black/5">
            <button v-if="isEditing" @click="onDelete"
                    class="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-500 text-sm font-medium hover:bg-red-500/20">
              删除项目
            </button>
            <div class="flex gap-2 ml-auto">
              <button @click="onCancel" class="px-3 py-1.5 rounded-lg bg-black/5 text-sm font-medium">取消</button>
              <button @click="onSave" :disabled="!form.name.trim()"
                      class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed">
                保存
              </button>
            </div>
          </div>
        </GlassCard>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import { projectsApi } from '@/api/client'
import type { Project } from '@/api/types'

const props = defineProps<{
  open: boolean
  project: Project | null  // null = create mode
}>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', project: Project): void
  (e: 'deleted', id: number): void
}>()

const presetColors = ['#0071e3', '#34c759', '#ff9500', '#af52de', '#ff3b30', '#8e8e93']

const isEditing = !!props.project

const form = ref({
  name: '', color: '#0071e3',
  start_date: '', end_date: '', description: ''
})

const nameInput = ref<HTMLInputElement | null>(null)

function loadFromProject() {
  if (props.project) {
    form.value = {
      name: props.project.name,
      color: props.project.color,
      start_date: props.project.start_date ?? '',
      end_date: props.project.end_date ?? '',
      description: props.project.description ?? ''
    }
  } else {
    form.value = { name: '', color: '#0071e3', start_date: '', end_date: '', description: '' }
  }
}

function focusName() {
  nextTick(() => nameInput.value?.focus())
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.open) onCancel()
}

watch(() => props.open, (v) => {
  if (v) { loadFromProject(); focusName() }
})

watch(() => props.project, () => {
  if (props.open) loadFromProject()
})

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

async function onSave() {
  if (!form.value.name.trim()) return
  const payload = {
    name: form.value.name.trim(),
    color: form.value.color,
    description: form.value.description.trim() || null,
    start_date: form.value.start_date || null,
    end_date: form.value.end_date || null,
  }
  try {
    let saved: Project
    if (props.project) {
      saved = await projectsApi.update(props.project.id, payload)
    } else {
      saved = await projectsApi.create(payload)
    }
    emit('saved', saved)
    emit('close')
  } catch { /* interceptor alerts */ }
}

function onCancel() { emit('close') }

async function onDelete() {
  if (!props.project) return
  if (!window.confirm(`删除项目"${props.project.name}"? 所有任务和费用将一并删除`)) return
  const id = props.project.id
  await projectsApi.remove(id)
  emit('deleted', id)
  emit('close')
}
</script>

<style scoped>
.slide-enter-active, .slide-leave-active {
  transition: transform 0.25s ease;
}
.slide-enter-from, .slide-leave-to {
  transform: translateX(100%);
}
</style>
```

- [ ] **Step 2: 构建验证（仅确保 .vue 编译通过）**

先别急着 commit，把 Task 9 改完一起 commit。

---

### Task 9: GanttView 集成 ProjectPanel + 升级新建项目

**Files:**
- Modify: `frontend/src/views/GanttView.vue`

- [ ] **Step 1: 读 GanttView 全文，找修改点**

读 `frontend/src/views/GanttView.vue` 全 294 行。需要修改：
- 顶部 `<select>` 改成可点击的项目按钮（带颜色 + 名称，点开面板）
- 现有 `<button @click="showNewProject = true">+ 新建项目</button>` 改为调 `openNewProject()`
- 移除原 `<Teleport>` 里的新建项目对话框
- 加 `import ProjectPanel from '@/components/ProjectPanel.vue'`
- 加状态：`showProjectPanel: ref(false)`, `panelProject: ref<Project | null>(null)`
- 加方法：`openProjectPanel()`, `openNewProject()`, `onPanelSaved()`, `onPanelDeleted()`

- [ ] **Step 2: 改顶部项目选择**

找到 line 5-10 的 `<select>` 块：
```vue
        <select v-model="selectedProjectId" @change="onProjectChange"
                class="px-3 py-1.5 rounded-lg bg-white/70 border border-black/5 text-sm font-semibold">
          <option v-for="p in projects.projects" :key="p.id" :value="p.id">
            {{ p.name }}
          </option>
        </select>
```

替换为（用 button 显示当前项目，点开面板）：
```vue
        <button @click="openProjectPanel"
                class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/70 border border-black/5 text-sm font-semibold hover:bg-white">
          <span v-if="currentProject" class="w-3 h-3 rounded-full" :style="{ background: currentProject.color }"></span>
          <span>{{ currentProject?.name ?? '选择项目' }}</span>
          <span class="text-gray-10">▾</span>
        </button>
```

并在 `<script setup>` 里加：
```typescript
const currentProject = computed(() =>
  projects.projects.find(p => p.id === selectedProjectId.value) ?? null
)
```

需要在顶部 `import` 加入 `computed`：
```typescript
import { ref, computed, onMounted } from 'vue'
```

- [ ] **Step 3: 「+ 新建项目」按钮**

找到 line 11-13：
```vue
        <button @click="showNewProject = true"
                class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-sm font-semibold">
          + 新建项目
        </button>
```

改成：
```vue
        <button @click="openNewProject"
                class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-sm font-semibold">
          + 新建项目
        </button>
```

- [ ] **Step 4: 移除原有新建项目对话框**

找到 line 88-101 左右的 `<Teleport>` 里的新建项目对话框（带 `showNewProject`），整段删掉。

- [ ] **Step 5: 加状态 + 方法 + 模板中的 ProjectPanel**

在 `<script setup>` 末尾（其他 ref 旁边）加：
```typescript
import ProjectPanel from '@/components/ProjectPanel.vue'
import type { Project } from '@/api/types'

const showProjectPanel = ref(false)
const panelProject = ref<Project | null>(null)

function openProjectPanel() {
  panelProject.value = currentProject.value
  showProjectPanel.value = true
}
function openNewProject() {
  panelProject.value = null
  showProjectPanel.value = true
}
async function onPanelSaved(p: Project) {
  await projects.fetchAll()
  selectedProjectId.value = p.id
}
async function onPanelDeleted() {
  showProjectPanel.value = false
  await projects.fetchAll()
  if (projects.projects.length > 0) {
    selectedProjectId.value = projects.projects[0].id
  } else {
    selectedProjectId.value = null
  }
}
```

并删除原 `showNewProject`/`newProjectName`/`confirmNewProject` 相关代码。

在 template 末尾（其他 `< `<Dialog>` 后或最末尾）加：
```vue
    <ProjectPanel :open="showProjectPanel" :project="panelProject"
                  @close="showProjectPanel = false"
                  @saved="onPanelSaved"
                  @deleted="onPanelDeleted" />
```

- [ ] **Step 6: 构建验证**

Run: `npm run build`（workdir `frontend`）
Expected: vue-tsc + vite build 通过

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ProjectPanel.vue frontend/src/views/GanttView.vue
git commit -m "feat: project side panel + integrate into GanttView"
```

---

### Task 10: TaskDetailView 描述内联编辑

**Files:**
- Modify: `frontend/src/views/TaskDetailView.vue`

- [ ] **Step 1: 替换只读描述区**

找到 line 62-65：
```vue
      <div v-if="task.description" class="mb-5 text-sm leading-relaxed whitespace-pre-wrap">
        {{ task.description }}
      </div>
      <div v-else class="mb-5 text-sm text-gray-400 italic">暂无描述</div>
```

替换为：
```vue
      <div class="mb-5">
        <div v-if="!editingDesc" @click="startEditDesc"
             class="cursor-pointer p-3 rounded-lg hover:bg-black/[0.03] border border-transparent hover:border-black/5 transition"
             :class="!task.description && 'text-gray-400 italic'">
          <div v-if="task.description" class="text-sm leading-relaxed whitespace-pre-wrap">
            {{ task.description }}
          </div>
          <div v-else class="text-sm">点击添加描述…</div>
        </div>
        <div v-else>
          <textarea ref="descInput" v-model="descDraft" rows="6"
                    class="w-full px-3 py-2 rounded-lg border border-black/10 bg-white/70 text-sm resize-none"
                    placeholder="任务的背景、目标、注意事项…"></textarea>
          <div class="flex gap-2 justify-end mt-2">
            <button @click="cancelEditDesc" class="px-3 py-1 rounded-lg bg-black/5 text-xs">取消</button>
            <button @click="saveEditDesc" class="px-3 py-1 rounded-lg bg-apple-blue text-white text-xs font-semibold">保存</button>
          </div>
        </div>
      </div>
```

- [ ] **Step 2: 加状态和方法**

在 `<script setup>` 中加：
```typescript
import { nextTick } from 'vue'  // 顶部若未导入则加

const editingDesc = ref(false)
const descDraft = ref('')
const descInput = ref<HTMLTextAreaElement | null>(null)

function startEditDesc() {
  descDraft.value = task.value?.description ?? ''
  editingDesc.value = true
  nextTick(() => descInput.value?.focus())
}
function cancelEditDesc() {
  editingDesc.value = false
}
async function saveEditDesc() {
  if (!task.value) return
  task.value = await tasksStore.update(task.value.id, {
    description: descDraft.value.trim() || null
  })
  editingDesc.value = false
}
```

- [ ] **Step 3: 构建验证**

Run: `npm run build`（workdir `frontend`）
Expected: 通过

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/TaskDetailView.vue
git commit -m "feat: inline description editing in task detail"
```

---

### Task 11: CostsView 表单多任务下拉 + 明细列

**Files:**
- Modify: `frontend/src/views/CostsView.vue`

- [ ] **Step 1: 表单中加任务下拉**

在 `<select v-model="form.category">` 块后、说明 input 前，加：
```vue
          <label class="block text-xs text-gray-500 mb-1">关联任务（可选）</label>
          <select v-model="form.task_id" class="w-full px-3 py-2 rounded-lg border border-black/10 mb-3 bg-white/70">
            <option :value="null">— 不关联任务 —</option>
            <option v-for="t in projectTasks" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
```

- [ ] **Step 2: 修改表单 ref 默认值 + openCreate**

表单 ref 类型扩展：
```typescript
const form = ref<{
  project_id: number
  amount: number
  spent_at: string
  category: string
  task_id: number | null
  description: string
}>({
  project_id: 0, amount: 0, spent_at: '', category: 'other',
  task_id: null, description: ''
})
```

`openCreate` 中重置：
```typescript
function openCreate() {
  form.value = {
    project_id: projects.currentId ?? projects.projects[0]?.id ?? 0,
    amount: 0,
    spent_at: new Date().toISOString().slice(0, 10),
    category: categories.list[0]?.name ?? '',
    task_id: null,
    description: ''
  }
  showForm.value = true
}
```

`submitForm` 中传 task_id：
```typescript
async function submitForm() {
  if (!form.value.project_id || !form.value.amount || form.value.amount <= 0) return
  await costsApi.create(form.value.project_id, {
    amount: form.value.amount,
    spent_at: form.value.spent_at,
    category: form.value.category,
    task_id: form.value.task_id,
    description: form.value.description || null
  })
  showForm.value = false
  await load()
}
```

- [ ] **Step 3: 加 projectTasks computed + watch 切换项目时清空 task_id**

```typescript
import { useTasksStore } from '@/stores/tasks'

const tasksStore = useTasksStore()

const projectTasks = computed(() =>
  tasksStore.tasks
    .filter(t => t.project_id === form.value.project_id)
    .sort((a, b) => a.sort_order - b.sort_order)
)

import { watch as vueWatch } from 'vue'
vueWatch(() => form.value.project_id, () => {
  form.value.task_id = null
})
```

注意：`watch` 已经在 `<script setup>` 中可能有同名的了，确认一下；如果已有 `import { watch }`，直接用 `watch(...)` 而不是即可。

正确写法（保留原 `import { ref, computed, onMounted, watch }` 中的 `watch`）：
```typescript
import { useTasksStore } from '@/stores/tasks'
const tasksStore = useTasksStore()

const projectTasks = computed(() =>
  tasksStore.tasks
    .filter(t => t.project_id === form.value.project_id)
    .sort((a, b) => a.sort_order - b.sort_order)
)

watch(() => form.value.project_id, () => {
  form.value.task_id = null
})
```

`load()` 中也要拉任务（如果还没拉）：
```typescript
async function load() {
  const pid = projects.currentId ?? projects.projects[0]?.id ?? 0
  await tasksStore.fetchByProject(pid)  // 新增
  const [costsRes, statsRes] = await Promise.all([
    costsApi.listByProject(pid),
    costsApi.stats(filterProject.value ?? undefined)
  ])
  costs.value = costsRes
  stats.value = statsRes
}
```

（`fetchByProject` 已在 tasks store 中存在，DashboardView Task 7 也用过。）

- [ ] **Step 4: 明细表加「任务」列：

在 table 的 thead `<th class="py-2 pr-3">项目</th>` 后加：
```vue
            <th class="py-2 pr-3">任务</th>
```

在对应 `<td>` 列（项目名 td 后）加：
```vue
            <td class="py-2.5 pr-3 text-gray-500">{{ taskName(c.task_id) }}</td>
```

`<script setup>` 加：
```typescript
function taskName(tid: number | null) {
  if (!tid) return '—'
  return tasksStore.byId.get(tid)?.name ?? `#${tid}`
}
```

- [ ] **Step 5: 构建验证**

Run: `npm run build`（workdir `frontend`）
Expected: 通过

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/CostsView.vue
git commit -m "feat: CostsView task dropdown + task column"
```

---

### Task 12: 端到端验收

**Files:** 无（验证步骤）

- [ ] **Step 1: 重启后端（让迁移生效）**

Run:
```powershell
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Start-Sleep 2
Start-Process -FilePath "C:\Users\leonj\Documents\opencode\.worktrees\dev\backend\.venv\Scripts\python.exe" -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8765") -WorkingDirectory "C:\Users\leonj\Documents\opencode\.worktrees\dev\backend" -RedirectStandardOutput "$env:TEMP\opencode\backend.out" -RedirectStandardError "$env:TEMP\opencode\backend.err"
Start-Sleep 4
```

Run: `curl http://127.0.0.1:8765/api/health`
Expected: `{"status":"ok"}`

Run: `curl http://127.0.0.1:8765/api/projects | head -c 200`
Expected: 项目 JSON，含 `description` 字段（老项目 null）

- [ ] **Step 2: 全量后端测试**

Run: `backend\.venv\Scripts\python.exe -m pytest -q`
Expected: 83 passed

- [ ] **Step 3: DOM dump 验证 GanttView 项目面板入口**

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu --no-first-run --user-data-dir="$env:TEMP\opencode\edgeprof-p1" --virtual-time-budget=15000 --dump-dom "http://127.0.0.1:5173/gantt" 2>$null | Out-File -Encoding utf8 "$env:TEMP\opencode\gantt.html"
```
然后验证 HTML有项目颜色圆点 + 名称按钮。

- [ ] **Step 4: 验证 TaskDetailView 描述可编辑**

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu --no-first-run --user-data-dir="$env:TEMP\opencode\edgeprof-p2" --virtual-time-budget=15000 --dump-dom "http://127.0.0.1:5173/gantt/1/task/1" 2>$null | Out-File -Encoding utf8 "$env:TEMP\opencode\td.html"
```
验证 HTML含「点击添加描述…」或描述文本（不报错是）。

- [ ] **Step 5: 验证 CostsView 多任务下拉**

打开 `/costs`，表单中类别下拉后应有「关联任务」下拉。明细表应有「任务」列。

- [ ] **Step 6: 提交收尾**

```bash
git status
git log --oneline -15
```
确认所有改动已提交。

---

## Self-Review 记录

**Spec coverage:**
- 项目时间进度可编辑 → Task 1（schema date）+ Task 8/9（ProjectPanel + GanttView）
- 项目备注描述 → Task 1（description）+ Task 8/9（ProjectPanel）
- 任务备注可编辑 → Task 10（TaskDetailView 内联编辑）
- 费用关联任务 → Task 2（model+schema）+ Task 3（service 校验）+ Task 7（types/API）+ Task 11（CostsView 下拉 + 列）

**Type consistency：**
- `Project.description` / `Cost.task_id` 在 backend model/schema 和 frontend types 一致
- `ProjectUpdate` / `CostInput` 类型签名都扩展了对应字段

**已知风险：**
- 计划中已无占位代码（已自审修复）
- SQLite ALTER TABLE ADD COLUMN 不支持带 FK；FK 只能通过 create_all 在首次建表时建立。对老表（任务 1+2 跑前已存在的库）只能补列，FK 通过 PRAGMA foreign_keys=ON 在每次连接时强制
- 切换项目时 CostsView 的 task_id 自动清空（watch 实现）
- 项目删除会级联删除任务和费用（model 已设 `cascade="all, delete-orphan"`），用户在 onDelete 时 confirm 提示已经写明

**YAGNI：**
- 不做项目归档 UI
- 不做费用批量编辑
- 不做描述富文本/Markdown
- 不做 description 历史版本

**测试：**
- Project description 5 个测试
- Cost task_id 5 个测试（创建/查询/更新/跨项目 400/SET NULL 级联）
- 前端：build pass + DOM 验证

**Plan self-review 完成，进入执行。**