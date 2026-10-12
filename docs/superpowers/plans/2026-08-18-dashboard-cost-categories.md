# 总览仪表盘 + 费用类别自定义 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把总览仪表盘从占位页升级为完整数据总览（KPI + 月度日历 + 项目进度 + 费用趋势），并把费用类别从硬编码升级为可增删改的配置项。

**Architecture:** 后端新增 `cost_categories` 表和 `GET /api/stats/overview` 聚合端点；前端新增 categories store、重写 DashboardView、新增设置页费用类别管理、CostsView 动态化。类别字段存名称字符串（零迁移）。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + SQLite；Vue 3 + Vite + Tailwind + Pinia；pytest；vue-tsc。

---

## 文件结构

**后端（worktree: `C:\Users\leonj\Documents\opencode\.worktrees\dev\backend`）**
- Create: `app/models/cost_category.py`
- Create: `app/schemas/cost_category.py`
- Create: `app/services/cost_category_service.py`
- Create: `app/api/cost_categories.py`
- Create: `app/services/overview_service.py`
- Create: `app/api/stats.py`
- Create: `tests/test_cost_categories.py`
- Create: `tests/test_overview.py`
- Modify: `app/models/__init__.py`、`app/schemas/__init__.py`、`app/main.py`

**前端（worktree: `C:\Users\leonj\Documents\opencode\.worktrees\dev\frontend`）**
- Create: `src/stores/categories.ts`
- Create: `src/views/DashboardView.vue`（重写）
- Create: `src/views/SettingsView.vue`
- Create: `src/views/CostCategoriesView.vue`
- Modify: `src/api/types.ts`、`src/api/client.ts`、`src/router.ts`、`src/views/CostsView.vue`

---

### Task 1: cost_categories 模型 + schema

**Files:**
- Create: `backend/app/models/cost_category.py`
- Create: `backend/app/schemas/cost_category.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_cost_categories.py`（本 Task 只做模型/schema，测试在 Task 3）

- [ ] **Step 1: 写模型**

`backend/app/models/cost_category.py`:
```python
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CostCategory(Base):
    __tablename__ = "cost_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#8e8e93")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
```

- [ ] **Step 2: 注册到模型包**

`backend/app/models/__init__.py` 末尾追加:
```python
from app.models.cost_category import CostCategory

__all__ = ["Base", "Project", "Task", "TaskDependency", "Cost", "InboxItem", "CostCategory"]
```

- [ ] **Step 3: 写 schema**

`backend/app/schemas/cost_category.py`:
```python
from pydantic import BaseModel, ConfigDict, Field


class CostCategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#8e8e93", pattern="^#[0-9a-fA-F]{6}$")
    sort_order: int = 0


class CostCategoryCreate(CostCategoryBase):
    pass


class CostCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern="^#[0-9a-fA-F]{6}$")
    sort_order: int | None = None


class CostCategoryRead(CostCategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_builtin: bool
```

- [ ] **Step 4: 注册到 schemas 包**

`backend/app/schemas/__init__.py` 末尾追加:
```python
from app.schemas.cost_category import CostCategoryCreate, CostCategoryUpdate, CostCategoryRead

__all__ = [ ... 现有列表 ..., "CostCategoryCreate", "CostCategoryUpdate", "CostCategoryRead"]
```

- [ ] **Step 5: 验证导入**

Run: `backend\.venv\Scripts\python.exe -c "from app.models import CostCategory; from app.schemas import CostCategoryRead; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/cost_category.py backend/app/schemas/cost_category.py backend/app/models/__init__.py backend/app/schemas/__init__.py
git commit -m "feat: add CostCategory model + schemas"
```

---

### Task 2: cost_categories service + API + 种子数据

**Files:**
- Create: `backend/app/services/cost_category_service.py`
- Create: `backend/app/api/cost_categories.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/database.py`

- [ ] **Step 1: 写 service**

`backend/app/services/cost_category_service.py`:
```python
from sqlalchemy.orm import Session

from app.models import Cost, CostCategory
from app.schemas import CostCategoryCreate, CostCategoryUpdate

BUILTIN_CATEGORIES = [
    {"name": "material", "color": "#0071e3"},
    {"name": "labor", "color": "#34c759"},
    {"name": "travel", "color": "#ff9500"},
    {"name": "other", "color": "#af52de"},
]


def seed_builtin_categories(db: Session) -> None:
    if db.query(CostCategory).count() > 0:
        return
    for i, c in enumerate(BUILTIN_CATEGORIES):
        db.add(CostCategory(**c, is_builtin=True, sort_order=i))
    db.commit()


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
    for k, v in updates.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


def delete_category(db: Session, c: CostCategory) -> None:
    if c.is_builtin:
        raise ValueError("内置类别不可删除")
    used = db.query(Cost).filter(Cost.category == c.name).count()
    if used > 0:
        raise ValueError(f"该类别已被 {used} 笔费用使用")
    db.delete(c)
    db.commit()
```

- [ ] **Step 2: 写 API**

`backend/app/api/cost_categories.py`:
```python
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
```

- [ ] **Step 3: 注册路由**

`backend/app/main.py` 追加 import 和 include：
```python
from app.api.cost_categories import router as categories_router
...
app.include_router(categories_router)
```

- [ ] **Step 4: lifespan 里种子**

`backend/app/main.py` 的 lifespan 中，`Base.metadata.create_all(engine)` 之后追加：
```python
    from app.database import SessionLocal
    from app.services.cost_category_service import seed_builtin_categories
    with SessionLocal() as session:
        seed_builtin_categories(session)
```

- [ ] **Step 5: 手动验证**

Run（先确认后端已重启）: `curl http://127.0.0.1:8765/api/cost-categories`
Expected: 返回 4 个内置类别 JSON（material/labor/travel/other）

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/cost_category_service.py backend/app/api/cost_categories.py backend/app/main.py
git commit -m "feat: cost categories API + builtin seed"
```

---

### Task 3: 后端测试 cost_categories

**Files:**
- Create: `backend/tests/test_cost_categories.py`

- [ ] **Step 1: 写测试**

`backend/tests/test_cost_categories.py`:
```python
def _mk_cat(client, name="新类别", color="#123456"):
    r = client.post("/api/cost-categories", json={"name": name, "color": color})
    assert r.status_code == 201, r.text
    return r.json()


def test_list_builtin_seeded(client, db_session):
    # conftest 不跑 lifespan，直接手动种子
    from app.services.cost_category_service import seed_builtin_categories
    seed_builtin_categories(db_session)
    r = client.get("/api/cost-categories")
    assert r.status_code == 200
    assert len(r.json()) == 4
    names = {c["name"] for c in r.json()}
    assert names == {"material", "labor", "travel", "other"}


def test_create_category(client, db_session):
    c = _mk_cat(client)
    assert c["name"] == "新类别"
    assert c["is_builtin"] is False


def test_duplicate_name_409(client, db_session):
    from app.services.cost_category_service import seed_builtin_categories
    seed_builtin_categories(db_session)
    r = client.post("/api/cost-categories", json={"name": "material", "color": "#111111"})
    assert r.status_code == 409


def test_update_category_name_and_color(client, db_session):
    c = _mk_cat(client)
    r = client.patch(f"/api/cost-categories/{c['id']}", json={"name": "改名", "color": "#abcdef"})
    assert r.status_code == 200
    assert r.json()["name"] == "改名"
    assert r.json()["color"] == "#abcdef"


def test_update_duplicate_name_409(client, db_session):
    _mk_cat(client, "类别A")
    c = _mk_cat(client, "类别B")
    r = client.patch(f"/api/cost-categories/{c['id']}", json={"name": "类别A"})
    assert r.status_code == 409


def test_delete_category(client, db_session):
    c = _mk_cat(client)
    r = client.delete(f"/api/cost-categories/{c['id']}")
    assert r.status_code == 204
    assert client.get("/api/cost-categories").json() == []


def test_delete_builtin_409(client, db_session):
    from app.services.cost_category_service import seed_builtin_categories
    seed_builtin_categories(db_session)
    builtin = [c for c in client.get("/api/cost-categories").json() if c["is_builtin"]][0]
    r = client.delete(f"/api/cost-categories/{builtin['id']}")
    assert r.status_code == 409


def test_delete_referenced_409(client, db_session):
    from app.services.cost_category_service import seed_builtin_categories
    seed_builtin_categories(db_session)
    # 用种子类别建一笔费用
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    r = client.post("/api/costs", json={
        "project_id": pid, "category": "material", "amount": 10, "spent_at": "2026-08-01"
    })
    assert r.status_code == 201
    cat_id = [c for c in client.get("/api/cost-categories").json() if c["name"] == "material"][0]["id"]
    r = client.delete(f"/api/cost-categories/{cat_id}")
    assert r.status_code == 409


def test_delete_missing_404(client, db_session):
    r = client.delete("/api/cost-categories/9999")
    assert r.status_code == 404
```

- [ ] **Step 2: 运行测试**

Run: `backend\.venv\Scripts\python.exe -m pytest tests/test_cost_categories.py -v`
Expected: 全部 PASS（注意：conftest 的 `client` fixture 不走 lifespan，所以内置类别种子需在测试内手动调用 `seed_builtin_categories`）

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_cost_categories.py
git commit -m "test: cost categories API tests"
```

---

### Task 4: overview 聚合 service + API

**Files:**
- Create: `backend/app/services/overview_service.py`
- Create: `backend/app/api/stats.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写 service**

`backend/app/services/overview_service.py`:
```python
from datetime import date

from sqlalchemy.orm import Session

from app.models import Project, Task


def _compute_progress(tasks: list[Task]) -> int:
    """叶子任务权重为 1，父任务权重 = 子任务权重和。进度 = 已完成叶子权重 / 总叶子权重。"""
    children: dict[int | None, list[Task]] = {}
    for t in tasks:
        children.setdefault(t.parent_id, []).append(t)

    def weight(t: Task) -> int:
        subs = children.get(t.id, [])
        if not subs:
            return 1
        return sum(weight(s) for s in subs)

    def done_weight(t: Task) -> int:
        if t.status == "done":
            return weight(t)
        return sum(done_weight(s) for s in children.get(t.id, []))

    total = sum(weight(t) for t in children.get(None, []))
    if total == 0:
        return 0
    done = sum(done_weight(t) for t in children.get(None, []))
    return round(done / total * 100)


def get_overview(db: Session) -> dict:
    today = date.today()
    projects = db.query(Project).order_by(Project.id).all()
    tasks = db.query(Task).all()

    active_tasks = sum(1 for t in tasks if t.status == "progress")
    delayed_tasks = sum(1 for t in tasks if t.status == "delayed")

    month_key = f"{today.year:04d}-{today.month:02d}"
    from app.models import Cost
    this_month_cost = round(
        sum(c.amount for c in db.query(Cost).all() if c.spent_at.strftime("%Y-%m") == month_key),
        2,
    )

    project_rows = []
    for p in projects:
        ptasks = [t for t in tasks if t.project_id == p.id]
        total = len(ptasks)
        done = sum(1 for t in ptasks if t.status == "done")
        due = [
            t for t in ptasks
            if t.end_date is not None and t.end_date >= today
            and t.status not in ("done", "cancelled")
        ]
        next_due = min(due, key=lambda t: t.end_date) if due else None
        project_rows.append({
            "id": p.id,
            "name": p.name,
            "color": p.color,
            "task_total": total,
            "task_done": done,
            "progress": _compute_progress(ptasks),
            "next_due_task": {
                "id": next_due.id,
                "name": next_due.name,
                "end_date": next_due.end_date.isoformat(),
            } if next_due else None,
        })

    return {
        "project_count": len(projects),
        "active_task_count": active_tasks,
        "delayed_task_count": delayed_tasks,
        "this_month_cost": this_month_cost,
        "projects": project_rows,
    }
```

- [ ] **Step 2: 写 API**

`backend/app/api/stats.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import overview_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    return overview_service.get_overview(db)
```

- [ ] **Step 3: 注册路由**

`backend/app/main.py` 追加 import 和 include：
```python
from app.api.stats import router as stats_router
...
app.include_router(stats_router)
```

- [ ] **Step 4: 手动验证**

Run: `curl http://127.0.0.1:8765/api/stats/overview`
Expected: 返回项目数/任务数/本月支出/项目进度 JSON

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/overview_service.py backend/app/api/stats.py backend/app/main.py
git commit -m "feat: overview stats endpoint"
```

---

### Task 5: 后端测试 overview

**Files:**
- Create: `backend/tests/test_overview.py`

- [ ] **Step 1: 写测试**

`backend/tests/test_overview.py`:
```python
def test_overview_empty(client, db_session):
    r = client.get("/api/stats/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["project_count"] == 0
    assert body["active_task_count"] == 0
    assert body["delayed_task_count"] == 0
    assert body["this_month_cost"] == 0.0
    assert body["projects"] == []


def test_overview_counts_and_progress(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    # 3 个叶子任务，1 个完成
    client.post(f"/api/projects/{pid}/tasks", json={"name": "A", "status": "done"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "B", "status": "progress"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "C", "status": "delayed"})
    # 本月一笔费用
    client.post("/api/costs", json={
        "project_id": pid, "category": "other", "amount": 100, "spent_at": "2026-08-01"
    })
    r = client.get("/api/stats/overview")
    body = r.json()
    assert body["project_count"] == 1
    assert body["active_task_count"] == 1
    assert body["delayed_task_count"] == 1
    assert body["this_month_cost"] == 100.0
    p = body["projects"][0]
    assert p["task_total"] == 3
    assert p["task_done"] == 1
    assert p["progress"] == 33


def test_overview_nested_progress(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    root = client.post(f"/api/projects/{pid}/tasks", json={"name": "根"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/tasks", json={"name": "A", "parent_id": root}).json()["id"]
    b = client.post(f"/api/projects/{pid}/tasks", json={"name": "B", "parent_id": root}).json()["id"]
    client.post(f"/api/projects/{pid}/tasks", json={"name": "A1", "parent_id": a, "status": "done"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "A2", "parent_id": a, "status": "done"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "B1", "parent_id": b})
    # 权重：A1=1, A2=1, B1=1，B 无子任务(父任务算 0 除非完成)
    r = client.get("/api/stats/overview")
    p = r.json()["projects"][0]
    # 叶子 = A1,A2,B1 + B? B 无子任务所以 B 是叶子(权重1, 未完成)
    # 总叶子权重 4，完成 A1+A2=2 → 50%
    assert p["progress"] == 50


def test_overview_next_due(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    client.post(f"/api/projects/{pid}/tasks", json={"name": "晚的", "end_date": "2026-09-01"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "早的", "end_date": "2026-08-20"})
    r = client.get("/api/stats/overview")
    nd = r.json()["projects"][0]["next_due_task"]
    assert nd["name"] == "早的"
    assert nd["end_date"] == "2026-08-20"
```

- [ ] **Step 2: 运行测试**

Run: `backend\.venv\Scripts\python.exe -m pytest tests/test_overview.py -v`
Expected: 全部 PASS

- [ ] **Step 3: 全量回归**

Run: `backend\.venv\Scripts\python.exe -m pytest -q`
Expected: 55 + 9 + 8 = 72 tests 全 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_overview.py
git commit -m "test: overview stats endpoint tests"
```

---

### Task 6: 前端 categories store + API + 类型

**Files:**
- Create: `frontend/src/stores/categories.ts`
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 添加类型**

`frontend/src/api/types.ts` 中把现有的 `export type CostCategory = 'material' | ...` 重命名为 `export type BuiltinCostCategory = 'material' | ...`；把 `Cost.category: CostCategory` 改为 `category: string`（类别现在是动态字符串，不是硬编码联合）。然后追加：
```typescript
export interface CostCategory {
  id: number
  name: string
  color: string
  is_builtin: boolean
  sort_order: number
}
```

- [ ] **Step 2: 添加 API**

`frontend/src/api/client.ts` 末尾追加：
```typescript
export const categoriesApi = {
  list: () => api.get<CostCategory[]>('/cost-categories').then(r => r.data),
  create: (data: { name: string; color: string }) =>
    api.post<CostCategory>('/cost-categories', data).then(r => r.data),
  update: (id: number, data: Partial<Pick<CostCategory, 'name' | 'color' | 'sort_order'>>) =>
    api.patch<CostCategory>(`/cost-categories/${id}`, data).then(r => r.data),
  remove: (id: number) => api.delete(`/cost-categories/${id}`).then(() => undefined)
}
```
（更新 `import type` 行加入 `CostCategory`）

- [ ] **Step 3: 写 store**

`frontend/src/stores/categories.ts`:
```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { categoriesApi } from '@/api/client'
import type { CostCategory } from '@/api/types'

export const useCategoriesStore = defineStore('categories', () => {
  const list = ref<CostCategory[]>([])

  const byName = computed(() => {
    const m = new Map<string, CostCategory>()
    list.value.forEach(c => m.set(c.name, c))
    return m
  })

  function colorOf(name: string): string {
    return byName.value.get(name)?.color ?? '#8e8e93'
  }

  async function fetchAll() {
    list.value = await categoriesApi.list()
  }

  async function create(data: { name: string; color: string }) {
    const c = await categoriesApi.create(data)
    list.value.push(c)
    return c
  }

  async function update(id: number, data: Partial<Pick<CostCategory, 'name' | 'color' | 'sort_order'>>) {
    const c = await categoriesApi.update(id, data)
    const idx = list.value.findIndex(x => x.id === id)
    if (idx >= 0) list.value[idx] = c
    return c
  }

  async function remove(id: number) {
    await categoriesApi.remove(id)
    list.value = list.value.filter(c => c.id !== id)
  }

  return { list, byName, colorOf, fetchAll, create, update, remove }
})
```

- [ ] **Step 4: 构建验证**

Run: `npm run build`
Expected: vue-tsc 无错误，build 成功

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/categories.ts frontend/src/api/types.ts frontend/src/api/client.ts
git commit -m "feat: categories store + API client"
```

---

### Task 7: DashboardView 重写（KPI + 月度日历 + 项目进度 + 费用趋势）

**Files:**
- Create: `frontend/src/views/DashboardView.vue`（重写）
- Modify: `frontend/src/api/client.ts`（加 overview API）

- [ ] **Step 1: 加 overview API**

`frontend/src/api/client.ts` 追加：
```typescript
export interface OverviewProject {
  id: number
  name: string
  color: string
  task_total: number
  task_done: number
  progress: number
  next_due_task: { id: number; name: string; end_date: string } | null
}

export interface Overview {
  project_count: number
  active_task_count: number
  delayed_task_count: number
  this_month_cost: number
  projects: OverviewProject[]
}

export const statsApi = {
  overview: () => api.get<Overview>('/stats/overview').then(r => r.data)
}
```

- [ ] **Step 2: 写 DashboardView.vue**

`frontend/src/views/DashboardView.vue`（完整替换）:
```vue
<template>
  <div class="space-y-5">
    <!-- KPI 行 -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <GlassCard class="p-4">
        <div class="text-xs text-gray-500 mb-1">📁 项目数</div>
        <div class="text-3xl font-bold">{{ overview?.project_count ?? 0 }}</div>
      </GlassCard>
      <GlassCard class="p-4">
        <div class="text-xs text-gray-500 mb-1">🔵 进行中任务</div>
        <div class="text-3xl font-bold text-apple-blue">{{ overview?.active_task_count ?? 0 }}</div>
      </GlassCard>
      <GlassCard class="p-4">
        <div class="text-xs text-gray-500 mb-1">⚠️ 延期任务</div>
        <div class="text-3xl font-bold text-apple-orange">{{ overview?.delayed_task_count ?? 0 }}</div>
      </GlassCard>
      <GlassCard class="p-4">
        <div class="text-xs text-gray-500 mb-1">💰 本月支出</div>
        <div class="text-3xl font-bold">¥{{ (overview?.this_month_cost ?? 0).toFixed(2) }}</div>
      </GlassCard>
    </div>

    <!-- 月度日历 -->
    <GlassCard class="p-5">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold">📅 月度任务日历</h2>
        <div class="flex items-center gap-2">
          <button @click="prevMonth" class="px-3 py-1 rounded-lg bg-black/5 hover:bg-black/10 text-sm font-medium">◀</button>
          <span class="text-sm font-semibold w-28 text-center">{{ monthLabel }}</span>
          <button @click="nextMonth" class="px-3 py-1 rounded-lg bg-black/5 hover:bg-black/10 text-sm font-medium">▶</button>
          <button @click="goToday" class="px-3 py-1 rounded-lg bg-apple-blue/10 text-apple-blue text-sm font-medium">回到本月</button>
        </div>
      </div>
      <div class="grid grid-cols-7 gap-1 text-center text-xs text-gray-500 mb-1">
        <div v-for="w in weekdays" :key="w">{{ w }}</div>
      </div>
      <div class="grid grid-cols-7 gap-1">
        <div v-for="d in calendarCells" :key="d.key"
             class="min-h-[88px] rounded-lg border p-1.5"
             :class="[d.isToday ? 'border-apple-blue bg-apple-blue/5' : 'border-black/5 bg-white/40', d.inMonth ? '' : 'opacity-30']">
          <div class="text-xs font-semibold" :class="{ 'text-apple-blue': d.isToday }">{{ d.day }}</div>
          <div class="mt-1 space-y-1">
            <div v-for="t in d.tasks" :key="t.id"
                 @click="openTask(t.id)"
                 class="text-[11px] px-1 py-0.5 rounded bg-white/80 shadow-sm cursor-pointer truncate hover:bg-white"
                 :title="t.projectName + ' · ' + t.name">
              <span class="inline-block w-1.5 h-1.5 rounded-full mr-1" :style="{ background: statusColor(t.status) }"></span>
              {{ t.projectName }}·{{ t.name }}
            </div>
          </div>
        </div>
      </div>
    </GlassCard>

    <!-- 项目进度 -->
    <GlassCard class="p-5">
      <h2 class="text-lg font-bold mb-4">📁 项目进度</h2>
      <div v-if="overview && overview.projects.length === 0" class="text-sm text-gray-400 text-center py-8">
        还没有项目，去创建第一个吧
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div v-for="p in overview?.projects ?? []" :key="p.id"
             @click="goProject(p.id)"
             class="p-4 rounded-xl bg-white/50 border border-black/5 cursor-pointer hover:bg-white/80 transition">
          <div class="flex items-center gap-2 mb-2">
            <span class="w-3 h-3 rounded-full" :style="{ background: p.color }"></span>
            <span class="font-semibold">{{ p.name }}</span>
            <span class="ml-auto text-xs text-gray-500">{{ p.task_done }}/{{ p.task_total }} 完成</span>
          </div>
          <div class="h-2 bg-black/5 rounded-full overflow-hidden mb-2">
            <div class="h-full bg-gradient-to-r from-sky-400 to-apple-blue"
                 :style="{ width: p.progress + '%' }"></div>
          </div>
          <div class="text-xs text-gray-500">
            {{ p.progress }}%
            <span v-if="p.next_due_task" class="ml-2">⏰ 下个截止：{{ p.next_due_task.name }}（{{ p.next_due_task.end_date }}）</span>
          </div>
        </div>
      </div>
    </GlassCard>

    <!-- 月度费用趋势 -->
    <GlassCard class="p-5">
      <h2 class="text-lg font-bold mb-4">💰 月度费用趋势</h2>
      <div v-if="monthBars.length === 0" class="text-sm text-gray-400 text-center py-8">暂无费用数据</div>
      <div v-else class="flex items-end gap-2 h-40 px-2">
        <div v-for="m in monthBars" :key="m.key" class="flex-1 flex flex-col items-center gap-1">
          <div class="w-full max-w-[40px] rounded-t-md bg-apple-blue"
               :style="{ height: barHeight(m.total) + 'px' }"
               :title="`${m.label}: ¥${m.total.toFixed(2)}`"></div>
          <div class="text-[10px] text-gray-500">{{ m.short }}</div>
        </div>
      </div>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import GlassCard from '@/components/GlassCard.vue'
import { statsApi, costsApi } from '@/api/client'
import { useProjectsStore } from '@/stores/projects'
import { useTasksStore } from '@/stores/tasks'
import type { Overview, CostStats, TaskStatus } from '@/api/types'

const router = useRouter()
const projects = useProjectsStore()
const tasksStore = useTasksStore()

const overview = ref<Overview | null>(null)
const costStats = ref<CostStats>({ total: 0, count: 0, by_category: {}, by_month: {} })

const viewMonth = ref(new Date())
const weekdays = ['日', '一', '二', '三', '四', '五', '六']

const statusColorMap: Record<TaskStatus, string> = {
  todo: '#8e8e93', progress: '#0071e3', delayed: '#ff9500',
  done: '#34c759', cancelled: '#af52de'
}
function statusColor(s: TaskStatus) { return statusColorMap[s] ?? '#8e8e93' }

const monthLabel = computed(() => {
  const d = viewMonth.value
  return `${d.getFullYear()}年${d.getMonth() + 1}月`
})

interface CellTask { id: number; name: string; projectName: string; status: TaskStatus }
interface CalendarCell {
  key: string; day: number; inMonth: boolean; isToday: boolean; tasks: CellTask[]
}

const calendarCells = computed<CalendarCell[]>(() => {
  const y = viewMonth.value.getFullYear()
  const m = viewMonth.value.getMonth()
  const first = new Date(y, m, 1)
  const daysInMonth = new Date(y, m + 1, 0).getDate()
  const lead = first.getDay()
  const today = new Date()
  const todayKey = `${today.getFullYear()}-${today.getMonth()}-${today.getDate()}`

  const allTasks = tasksStore.tasks.map(t => {
    const p = projects.byId.get(t.project_id)
    return { ...t, projectName: p?.name ?? `#${t.project_id}` }
  })

  const cells: CalendarCell[] = []
  const totalCells = Math.ceil((lead + daysInMonth) / 7) * 7
  for (let i = 0; i < totalCells; i++) {
    const dayNum = i - lead + 1
    const inMonth = dayNum >= 1 && dayNum <= daysInMonth
    const d = new Date(y, m, dayNum)
    const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
    const isToday = key === todayKey
    const dayTasks: CellTask[] = []
    if (inMonth) {
      for (const t of allTasks) {
        if (!t.start_date) continue
        const start = new Date(t.start_date + 'T00:00:00')
        const end = t.end_date ? new Date(t.end_date + 'T00:00:00') : start
        if (t.status === 'done' || t.status === 'cancelled') continue
        // 进行中(落在区间) 或 截止(当天=end)
        const inRange = d >= start && d <= end
        const isDue = d.getTime() === end.getTime()
        if (inRange || isDue) {
          dayTasks.push({ id: t.id, name: t.name, projectName: t.projectName, status: t.status })
        }
      }
    }
    cells.push({ key, day: dayNum, inMonth, isToday, tasks: dayTasks })
  }
  return cells
})

function prevMonth() { viewMonth.value = new Date(viewMonth.value.getFullYear(), viewMonth.value.getMonth() - 1, 1) }
function nextMonth() { viewMonth.value = new Date(viewMonth.value.getFullYear(), viewMonth.value.getMonth() + 1, 1) }
function goToday() { viewMonth.value = new Date() }

function openTask(taskId: number) {
  const t = tasksStore.tasks.find(x => x.id === taskId)
  if (t) router.push(`/gantt/${t.project_id}/task/${taskId}`)
}

function goProject(projectId: number) {
  projects.select(projectId)
  router.push('/gantt')
}

const monthBars = computed(() => {
  const months = Object.entries(costStats.value.by_month)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-12)
    .map(([key, total]) => ({ key, total, short: key.slice(2).replace('-', '/'), label: key }))
  return months
})

const maxMonth = computed(() => Math.max(...monthBars.value.map(m => m.total), 1))
function barHeight(total: number) { return Math.max(2, Math.round((total / maxMonth.value) * 100)) }

onMounted(async () => {
  if (projects.projects.length === 0) await projects.fetchAll()
  await Promise.all([
    tasksStore.fetchAll?.(),
    statsApi.overview().then(d => { overview.value = d }),
    costsApi.stats().then(d => { costStats.value = d })
  ])
})
</script>
```

**注意**：`tasksStore.fetchAll` 当前不存在（store 只有 `fetchByProject`）。按 Task 7 的商店实现，需要给 tasks store 增加 `fetchAll` 方法（拉所有项目的任务）。Step 3 处理。

- [ ] **Step 3: tasks store 增加 fetchAll**

`frontend/src/stores/tasks.ts` 末尾追加：
```typescript
  async function fetchAll() {
    const { projectsApi } = await import('@/api/client')
    const plist = await projectsApi.list()
    const result: Task[] = []
    const deps: TaskDependency[] = []
    for (const p of plist) {
      result.push(...await tasksApi.listByProject(p.id))
      deps.push(...await depsApi.listByProject(p.id))
    }
    tasks.value = result
    dependencies.value = deps
  }
```
并在 return 中加入 `fetchAll`。

同时给 `frontend/src/stores/projects.ts` 添加 `byId` getter（DashboardView 需要）：
```typescript
  const byId = computed(() => {
    const m = new Map<number, Project>()
    projects.value.forEach(p => m.set(p.id, p))
    return m
  })
```
并加入 return。确保文件顶部已 import `Project` 类型（当前已有）。

- [ ] **Step 4: 构建验证**

Run: `npm run build`
Expected: vue-tsc 无错误（若有 TS 错误，按报错修正类型标注）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/DashboardView.vue frontend/src/api/client.ts frontend/src/stores/tasks.ts
git commit -m "feat: dashboard overview with monthly calendar"
```

---

### Task 8: SettingsView + CostCategoriesView

**Files:**
- Create: `frontend/src/views/SettingsView.vue`
- Create: `frontend/src/views/CostCategoriesView.vue`
- Modify: `frontend/src/router.ts`

- [ ] **Step 1: 写 CostCategoriesView**

`frontend/src/views/CostCategoriesView.vue`:
```vue
<template>
  <GlassCard class="p-5">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-lg font-bold">🏷️ 费用类别</h2>
        <p class="text-sm text-gray-500">管理费用类别与颜色，删除已被使用的类别会被拒绝</p>
      </div>
      <button @click="openCreate" class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-sm font-semibold">
        + 添加类别
      </button>
    </div>

    <div class="space-y-2">
      <div v-for="c in categories.list" :key="c.id"
           class="flex items-center gap-3 p-3 rounded-xl bg-black/[0.02] border border-black/5">
        <span class="w-4 h-4 rounded-full shrink-0" :style="{ background: c.color }"></span>
        <div class="flex-1">
          <div class="flex items-center gap-2">
            <span class="font-semibold">{{ c.name }}</span>
            <span v-if="c.is_builtin" class="text-[10px] px-1.5 py-0.5 rounded bg-black/5 text-gray-500">内置</span>
          </div>
          <span class="text-xs text-gray-400">{{ c.color }}</span>
        </div>
        <div class="flex items-center gap-1">
          <button v-for="color in presetColors" :key="color" @click="changeColor(c, color)"
                  class="w-5 h-5 rounded-full border-2"
                  :class="c.color === color ? 'border-apple-blue' : 'border-white'"
                  :style="{ background: color }"></button>
        </div>
        <button v-if="!c.is_builtin" @click="rename(c)"
                class="text-xs px-2 py-1 rounded-lg bg-black/5 text-gray-600 hover:bg-black/10">改名</button>
        <button v-if="!c.is_builtin" @click="remove(c)"
                class="text-xs px-2 py-1 rounded-lg text-red-500 hover:bg-red-500/10">删除</button>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showForm" class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50"
           @click.self="showForm = false">
        <GlassCard class="p-6 w-96">
          <h3 class="text-lg font-bold mb-4">{{ editing?.id ? '重命名类别' : '添加类别' }}</h3>
          <label class="block text-xs text-gray-500 mb-1">类别名</label>
          <input v-model="formName" placeholder="如：设计费" @keyup.enter="submitForm"
                 class="w-full px-3 py-2 rounded-lg border border-black/10 mb-3 bg-white/70" />
          <div class="flex gap-2 justify-end">
            <button @click="showForm = false" class="px-3 py-1.5 rounded-lg bg-black/5">取消</button>
            <button @click="submitForm" class="px-3 py-1.5 rounded-lg bg-apple-blue text-white font-semibold">保存</button>
          </div>
        </GlassCard>
      </div>
    </Teleport>
  </GlassCard>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import { useCategoriesStore } from '@/stores/categories'
import type { CostCategory } from '@/api/types'

const categories = useCategoriesStore()
const presetColors = ['#0071e3', '#34c759', '#ff9500', '#af52de', '#ff3b30', '#8e8e93']

const showForm = ref(false)
const editing = ref<CostCategory | null>(null)
const formName = ref('')

function openCreate() {
  editing.value = null
  formName.value = ''
  showForm.value = true
}

function rename(c: CostCategory) {
  editing.value = c
  formName.value = c.name
  showForm.value = true
}

async function submitForm() {
  if (!formName.value.trim()) return
  try {
    if (editing.value?.id) {
      await categories.update(editing.value.id, { name: formName.value.trim() })
    } else {
      await categories.create({ name: formName.value.trim(), color: presetColors[0] })
    }
  } catch { /* 409 由 axios 拦截器弹窗提示 */ }
  showForm.value = false
}

async function changeColor(c: CostCategory, color: string) {
  await categories.update(c.id, { color })
}

async function remove(c: CostCategory) {
  if (!window.confirm(`删除类别"${c.name}"?`)) return
  try {
    await categories.remove(c.id)
  } catch { /* 409 由拦截器提示 */ }
}

onMounted(() => { if (categories.list.length === 0) categories.fetchAll() })
</script>
```

- [ ] **Step 2: 写 SettingsView**

`frontend/src/views/SettingsView.vue`:
```vue
<template>
  <div>
    <GlassCard class="p-5 mb-5">
      <h2 class="text-xl font-bold">⚙️ 系统管理</h2>
      <p class="text-sm text-gray-500">管理应用配置</p>
    </GlassCard>
    <CostCategoriesView />
  </div>
</template>

<script setup lang="ts">
import GlassCard from '@/components/GlassCard.vue'
import CostCategoriesView from '@/views/CostCategoriesView.vue'
</script>
```

- [ ] **Step 3: 更新路由**

`frontend/src/router.ts`：把 `/settings` 从 DashboardView 占位改为 SettingsView：
```typescript
  { path: '/settings', component: () => import('@/views/SettingsView.vue') },
```

- [ ] **Step 4: 构建验证**

Run: `npm run build`
Expected: 无 TS 错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/SettingsView.vue frontend/src/views/CostCategoriesView.vue frontend/src/router.ts
git commit -m "feat: settings page with cost category management"
```

---

### Task 9: CostsView 动态类别适配

**Files:**
- Modify: `frontend/src/views/CostsView.vue`

- [ ] **Step 1: 改为动态类别**

`frontend/src/views/CostsView.vue` 修改点：
1. 移除 `categoryMeta` 硬编码数组，改用 `useCategoriesStore`
2. `catColor(cat)` 改为 `categories.colorOf(cat)`
3. `catLabel(cat)` 改为查 `categories.list`：`categories.list.find(c => c.name === cat)?.name ?? cat`
4. 表单类别下拉改用 `v-for="c in categories.list"`，`:value="c.name"`
5. 饼图 `categoryList` computed 基于 `categories.list` × `stats.by_category`
6. 页面右上角加「⚙ 类别」按钮 → `router.push('/settings')`
7. onMounted 时 `categories.fetchAll()`

具体修改（对应代码位置）：
```typescript
import { useCategoriesStore } from '@/stores/categories'
const categories = useCategoriesStore()

function catColor(cat: string) { return categories.colorOf(cat) }
function catLabel(cat: string) {
  return categories.list.find(c => c.name === cat)?.name ?? cat
}

const categoryList = computed(() =>
  categories.list.map(c => ({
    key: c.name,
    label: c.name,
    color: c.color,
    total: stats.value.by_category[c.name] ?? 0,
    pct: stats.value.total > 0 ? Math.round(((stats.value.by_category[c.name] ?? 0) / stats.value.total) * 100) : 0
  })).filter(c => c.total > 0 || categories.list.length === 0)
)
```
表单下拉模板改为：
```html
<select v-model="form.category" class="...">
  <option v-for="c in categories.list" :key="c.id" :value="c.name">{{ c.name }}</option>
</select>
```
onMounted 追加：`if (categories.list.length === 0) await categories.fetchAll()`

- [ ] **Step 2: 构建验证**

Run: `npm run build`
Expected: 无 TS 错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/CostsView.vue
git commit -m "feat: CostsView uses dynamic cost categories"
```

---

### Task 10: 端到端验收

**Files:** 无（验证脚本）

- [ ] **Step 1: 重启后端（让种子生效）**

先确认 8765 端口无进程或重启：
```powershell
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Start-Sleep 2
& backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```
Run: `curl http://127.0.0.1:8765/api/cost-categories`
Expected: 4 个内置类别

- [ ] **Step 2: 后端全量测试**

Run: `backend\.venv\Scripts\python.exe -m pytest -q`
Expected: 72 tests PASS

- [ ] **Step 3: DOM dump 验证 Dashboard**

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu --no-first-run --user-data-dir="$env:TEMP\opencode\edgeprof-dash" --virtual-time-budget=15000 --dump-dom "http://127.0.0.1:5173/dashboard" 2>$null | Out-File -Encoding utf8 "$env:TEMP\opencode\dash.html"
```
Expected: 页面包含「项目数」「月度任务日历」「项目进度」「月度费用趋势」，且 KPI 数字非 0

- [ ] **Step 4: DOM dump 验证 Settings**

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu --no-first-run --user-data-dir="$env:TEMP\opencode\edgeprof-set" --virtual-time-budget=15000 --dump-dom "http://127.0.0.1:5173/settings" 2>$null | Out-File -Encoding utf8 "$env:TEMP\opencode\settings.html"
```
Expected: 页面包含 4 个内置类别名（material/labor/travel/other）

- [ ] **Step 5: DOM dump 验证 CostsView 动态化**

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu --no-first-run --user-data-dir="$env:TEMP\opencode\edgeprof-costs2" --virtual-time-budget=15000 --dump-dom "http://127.0.0.1:5173/costs" 2>$null | Out-File -Encoding utf8 "$env:TEMP\opencode\costs2.html"
```
Expected: 类别下拉包含「material」等选项，饼图 conic-gradient 存在

- [ ] **Step 6: 提交收尾**

```bash
git status
git log --oneline -5
```
确认所有改动已提交，提交信息完整。

---

## Self-Review 记录

**Spec coverage:**
- KPI 行 → Task 4/5（overview API）+ Task 7（DashboardView）
- 月度日历格视图 → Task 7（calendarCells）
- 项目卡片网格 → Task 7（项目进度 section）
- 费用趋势柱图 → Task 7（monthBars）
- cost_categories 表 → Task 1
- 种子数据 → Task 2
- CRUD API + 409 → Task 2/3
- 设置页 → Task 8
- CostsView 动态化 → Task 9
- 验收 → Task 10

**Type consistency：**
- `CostCategory` / `categoriesApi` / `useCategoriesStore` 在 Task 6/8/9 一致
- `Overview` / `statsApi.overview` 在 Task 7 定义并在 DashboardView 使用
- `fetchAll`（tasks store）在 Task 7 定义并调用
- `seed_builtin_categories` 在 Task 2 定义、Task 2 生命周期调用、Task 3 测试调用
- `projects.byId` 已在 Task 7 Step 3 补充给 projects store

**已知风险：**
- 现有 5 笔演示数据的 category 是 `material/labor/travel/other`，与内置类别名一致，无需迁移。
- DashboardView 引用了 `tasksStore.tasks`（所有项目任务），依赖 Task 7 的 `fetchAll` 填充，且要求任务带 `start_date` 才在日历显示。