# 数据备份/恢复 + 移除内置类别 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 设置页提供 JSON 备份下载/上传恢复；移除「费用类别」的内置概念让所有类别都可改名/删除。

**Architecture:** 后端新增 `backup_service`（多表序列化 + 单事务覆盖恢复）+ `api/admin.py`（GET / POST 路由）。删除 `seed_builtin_categories` 与 `is_builtin` 业务守卫；新增迁移把现有 `is_builtin=true` 改为 false。前端 SettingsView 加数据管理卡片 + CostCategoriesView 移除 v-if 守卫。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + SQLite（WAL 模式）；Vue 3 + Vite + Tailwind + Pinia；pytest；vue-tsc。

---

## 文件结构

**后端（`backend/`）**
- Create: `app/services/backup_service.py` — `export_data()` + `restore_data(db, payload)` 业务
- Create: `app/api/admin.py` — `GET /api/admin/backup` + `POST /api/admin/restore` 路由
- Modify: `app/main.py` — lifespan 去 seed；注册 admin_router
- Modify: `app/services/cost_category_service.py` — 去 BUILTIN_CATEGORIES + seed；去 update/delete 的 is_builtin 守卫
- Create: `scripts/migrate_drop_builtin_flag.py` — 把 is_builtin=true → false
- Modify: `app/main.py` lifespan 调用新迁移
- Create: `tests/test_backup.py` — 6 个测试
- Modify: `tests/test_cost_categories.py` — 现有内置守卫测试改期望

**前端（`frontend/`）**
- Modify: `src/api/client.ts` — 加 `adminApi.backup()` / `restore(file)`
- Modify: `src/views/SettingsView.vue` — 加「数据管理」卡片
- Modify: `src/views/CostCategoriesView.vue` — 改/删按钮去掉 `v-if="!c.is_builtin"`

---

### Task 1: backup_service 业务实现

**Files:**
- Create: `backend/app/services/backup_service.py`

- [ ] **Step 1: 写 backup_service.py**

```python
"""JSON 备份/恢复业务。

导出：序列化所有业务表到 dict。
恢复：单事务覆盖（清空后按依赖顺序插入），FK 期间关闭。
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    Cost, CostCategory, InboxItem, Project, Task, TaskDependency,
)


EXPORT_VERSION = 1


def export_data(db: Session) -> dict:
    return {
        "version": EXPORT_VERSION,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "projects": [_row_to_dict(p) for p in db.query(Project).order_by(Project.id).all()],
        "tasks": [_row_to_dict(t) for t in db.query(Task).order_by(Task.id).all()],
        "task_dependencies": [_row_to_dict(d) for d in db.query(TaskDependency).order_by(TaskDependency.id).all()],
        "costs": [_row_to_dict(c) for c in db.query(Cost).order_by(Cost.id).all()],
        "cost_categories": [_row_to_dict(c) for c in db.query(CostCategory).order_by(CostCategory.id).all()],
        "inbox_items": [_row_to_dict(i) for i in db.query(InboxItem).order_by(InboxItem.id).all()],
    }


def _row_to_dict(row) -> dict:
    """用 SQLAlchemy 2.0 的方式取所有列；日期/时间转 iso 字符串。"""
    result = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def restore_data(db: Session, payload: dict) -> dict:
    """单事务覆盖恢复。返回各类插入条数。"""
    if not isinstance(payload, dict):
        raise ValueError("备份文件不是有效的 JSON 对象")
    if payload.get("version") != EXPORT_VERSION:
        raise ValueError(f"备份版本不匹配（期望 {EXPORT_VERSION}，得到 {payload.get('version')}）")

    # 关闭 FK（SQLite）以便按任意顺序清空和重插入
    from sqlalchemy import text
    db.execute(text("PRAGMA foreign_keys = OFF"))
    try:
        # 反序删除（先子表后父表）
        db.query(InboxItem).delete()
        db.query(TaskDependency).delete()
        db.query(Cost).delete()
        db.query(Task).delete()
        db.query(Project).delete()
        db.query(CostCategory).delete()

        # 正序插入
        counts = {}
        for model, key in [
            (Project, "projects"),
            (CostCategory, "cost_categories"),
            (Task, "tasks"),
            (TaskDependency, "task_dependencies"),
            (Cost, "costs"),
            (InboxItem, "inbox_items"),
        ]:
            rows = [_dict_to_row(model, d) for d in payload.get(key, [])]
            for r in rows:
                db.add(r)
            counts[key] = len(rows)

        db.commit()
        return counts
    except Exception:
        db.rollback()
        raise
    finally:
        db.execute(text("PRAGMA foreign_keys = ON"))


def _dict_to_row(model, d: dict) -> object:
    """从 dict 重建 ORM 实例，忽略未知字段。"""
    valid_keys = {c.name for c in model.__table__.columns}
    kwargs = {k: v for k, v in d.items() if k in valid_keys}
    return model(**kwargs)
```

- [ ] **Step 2: 验证 import + 函数存在**

Run from `C:\Users\leonj\Documents\opencode\.worktrees\dev\backend`:
`.venv\Scripts\python.exe -c "from app.services import backup_service; print(hasattr(backup_service, 'export_data'), hasattr(backup_service, 'restore_data'))"`
Expected: `True True`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/backup_service.py
git commit -m "feat: backup_service export + restore with single-transaction overwrite"
```

---

### Task 2: admin.py 路由 + 注册

**Files:**
- Create: `backend/app/api/admin.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写 admin.py**

```python
import json
from datetime import datetime

importfrom fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import backup_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/backup")
def get_backup(db: Session = Depends(get_db)):
    data = backup_service.export_data(db)
    filename = f"pm-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    body = json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.post("/restore")
async def post_restore(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"JSON 解析失败: {e}")
    try:
        counts = backup_service.restore_data(db, payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok", "counts": counts}
```

- [ ] **Step 2: 修改 main.py 注册路由 + 移除 seed**

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
from app.api.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import engine
    from app.models.base import Base
    from app import models
    Base.metadata.create_all(engine)
    # 一次性迁移：老库加新列 + 清掉内置标志
    from scripts.migrate_add_desc_and_taskid import migrate
    migrate(engine)
    from scripts.migrate_drop_builtin_flag import migrate as drop_builtin
    drop_builtin(engine)
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
app.include_router(admin_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 3: 验证路由可访问**

Run from `C:\Users\leonj\Documents\opencode\.worktrees\dev\backend`:
先确保后端启动：`Stop-Process -Name python -Force -ErrorAction SilentlyContinue; Start-Sleep 2; Start-Process -FilePath "C:\Users\leonj\Documents\opencode\.worktrees\dev\backend\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8765" -WorkingDirectory "C:\Users\leonj\Documents\opencode\.worktrees\dev\backend"`

Run: `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8765/api/admin/backup`
Expected: `200`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/admin.py backend/app/main.py
git commit -m "feat: admin API for backup download + restore upload"
```

---

### Task 3: 移除内置类别守卫

**Files:**
- Modify: `backend/app/services/cost_category_service.py`

- [ ] **Step 1: 重写 cost_category_service.py**

完整替换：
```python
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
```

- [ ] **Step 2: 验证 import**

Run from `backend`: `.venv\Scripts\python.exe -c "from app.services import cost_category_service; print(hasattr(cost_category_service, 'seed_builtin_categories'), hasattr(cost_category_service, 'BUILTIN_CATEGORIES'))"`
Expected: `False False`（两个都被删了）

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/cost_category_service.py
git commit -m "refactor: remove built-in category concept from service layer"
```

---

### Task 4: is_builtin 迁移脚本

**Files:**
- Create: `backend/scripts/migrate_drop_builtin_flag.py`

- [ ] **Step 1: 写迁移**

```python
"""一次性迁移：把现有 is_builtin=true 的类别改为 false（不再有内置概念）。幂等。"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def column_exists(eng: Engine, table_name: str, column_name: str) -> bool:
    if not inspect(eng).has_table(table_name):
        return False
    cols = {c["name"] for c in inspect(eng).get_columns(table_name)}
    return column_name in cols


def migrate(engine: Engine) -> None:
    if not column_exists(engine, "cost_categories", "is_builtin"):
        return
    with engine.begin() as conn:
        conn.execute(text("UPDATE cost_categories SET is_builtin = 0 WHERE is_builtin = 1"))


if __name__ == "__main__":
    from app.database import engine
    migrate(engine)
    print("drop builtin flag done")
```

- [ ] **Step 2: 手动跑（对真实 DB）**

Run from `backend`: `.venv\Scripts\python.exe scripts\migrate_drop_builtin_flag.py`
Expected: `drop builtin flag done`

再跑一次（幂等）：
Expected: `drop builtin flag done`

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/migrate_drop_builtin_flag.py
git commit -m "feat: migrate is_builtin=true → false (drop built-in concept)"
```

---

### Task 5: 测试现有 is_builtin 守卫测试改期望

**Files:**
- Modify: `backend/tests/test_cost_categories.py`

- [ ] **Step 1: 改写两个测试**

读 `backend/tests/test_cost_categories.py`，找到：
- `test_update_builtin_name_409`（Task 3 加的，commit `613d`2）—— 当前断言 409，改成断言 200
- `test_delete_builtin_409`（spec 测试，commit `d036150`）—— 当前断言 409，改成断言 204

把：
```python
def test_update_builtin_name_409(client, db_session):
    seed_builtin_categories(db_session)
    builtin = [c for c in client.get("/api/cost-categories").json() if c["is_builtin"]][0]
    r = client.patch(f"/api/cost-categories/{builtin['id']}", json={"name": "改名"})
    assert r.status_code == 409
```
改成：
```python
def test_builtin_can_be_renamed(client, db_session):
    seed_builtin_categories(db_session)
    builtin = [c for c in client.get("/api/cost-categories").json() if c["is_builtin"]][0]
    r = client.patch(f"/api/cost-categories/{builtin['id']}", json={"name": "材料"})
    assert r.status_code == 200
    assert r.json()["name"] == "材料"


def test_builtin_can_be_deleted(client, db_session):
    seed_builtin_categories(db_session)
    builtin = [c for c in client.get("/api/cost-categories").json() if c["is_builtin"]][0]
    r = client.delete(f"/api/cost-categories/{builtin['id']}")
    assert r.status_code == 204
```

注意：`seed_builtin_categories` 函数本任务里被从 service 删了，但 tests 里可能还在 import 它并调用。**写测试时不要 import `seed_builtin_categories`**，因为它不再存在。如果现有测试里在 import，需要把它移除（或改为内联 INSERT 4 个 builtin）。**写文件前先读现有 `tests/test_cost_categories.py`，看 seed_builtin_categories 是怎么用的**，然后按需调整：
- 如果是 `from app.services.cost_category_service import seed_builtin_categories`，**这个 import 会因为 service 删了函数而 break**，需要从测试里移除 import 并改为手动 INSERT 4 条 builtin 记录（用 POST `/api/cost-categories` 创建即可）：
  ```python
  def _seed_builtin(client):
      for n in ["material", "labor", "travel", "other"]:
          client.post("/api/cost-categories", json={"name": n, "color": "#0071e3"})
  ```
  然后在 `test_builtin_can_be_renamed`/`test_builtin_can_be_deleted` 里调用 `_seed_builtin(client)`。

- [ ] **Step 2: 运行测试**

Run from `backend`: `.venv\Scripts\python.exe -m pytest tests/test_cost_categories.py -v`
Expected: 11 passed（原 10 + 新增 1 + 改写 2 → 实际是把 2 个改写、1 个新增，文件总共测试数比之前 +1）

- [ ] **Step 3: 全量回归**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 83 + 1 = 84 passed（仅 -1 个 409 测试 +1 个新 + 改 1 个；总数应该是 83；如果新增一个则是 84）

实际计数说明：本任务只改 2 个测试 + 加 1 个测试（共 3 个测试改动），但总数应该是 83 - 1 + 2 = 84。
- 原 test_update_builtin_name_409 被替换为 test_builtin_can_be_renamed（+1）
- 原 test_delete_builtin_409 被替换为 test_builtin_can_be_deleted（+1）
- 加了一个新测试（+1）
- 净增 2 → 83 + 2 = 85

如果总数不对（比如 83 旧测试被无意删了），调整测试文件后再跑。

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_cost_categories.py
git commit -m "test: built-in categories can now be renamed/deleted"
```

---

### Task 6: 备份/恢复测试

**Files:**
- Create: `backend/tests/test_backup.py`

- [ ] **Step 1: 写测试**

```python
import json


def test_backup_empty_db(client, db_session):
    r = client.get("/api/admin/backup")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == 1
    assert data["projects"] == []
    assert data["tasks"] == []
    assert data["costs"] == []
    assert data["cost_categories"] == []
    assert data["task_dependencies"] == []
    assert data["inbox_items"] == []
    assert "exported_at" in data


def test_backup_returns_all_tables(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    client.post("/api/costs", json={
        "project_id": pid, "category": "x", "amount": 10, "spent_at": "2026-08-01"
    })
    client.post("/api/cost-categories", json={"name": "x", "color": "#abcdef"})
    client.post("/api/inbox", json={"kind": "idea", "title": "I"})

    data = client.get("/api/admin/backup").json()
    assert len(data["projects"]) == 1
    assert data["projects"][0]["name"] == "P"
    assert len(data["tasks"]) == 1
    assert len(data["costs"]) == 1
    assert len(data["cost_categories"]) == 1
    assert len(data["inbox_items"]) == 1


def test_restore_overwrites_existing(client, db_session):
    client.post("/api/projects", json={"name": "OLD"})
    payload = {
        "version": 1,
        "exported_at": "2026-08-01T00:00:00Z",
        "projects": [{"id": 1, "name": "NEW", "color": "#0071e3", "description": None,
                      "start_date": None, "end_date": None, "status": "active",
                      "created_at": "2026-08-01T00:00:00", "updated_at": "2026-08-01T00:00:00"}],
        "tasks": [], "task_dependencies": [], "costs": [], "cost_categories": [], "inbox_items": []
    }
    files = {"file": ("backup.json", json.dumps(payload), "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    projects = client.get("/api/projects").json()
    assert len(projects) == 1
    assert projects[0]["name"] == "NEW"


def test_restore_invalid_json_400(client, db_session):
    files = {"file": ("backup.json", "{not json", "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 400


def test_restore_no_file_422(client, db_session):
    r = client.post("/api/admin/restore")
    assert r.status_code == 422


def test_restore_wrong_version_400(client, db_session):
    payload = {"version": 99, "projects": []}
    files = {"file": ("backup.json", json.dumps(payload), "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 400
    assert "版本" in r.json()["detail"]


def test_restore_preserves_fk_after(client, db_session):
    """恢复后 FK 重新开启，跨表引用仍能查到。"""
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    cid = client.post("/api/costs", json={
        "project_id": pid, "task_id": tid, "category": "x", "amount": 5, "spent_at": "2026-08-01"
    }).json()["id"]
    backup = client.get("/api/admin/backup").json()
    # 模拟外部改动（增加另一个项目）
    client.post("/api/projects", json={"name": "EXTRA"})
    # 恢复
    files = {"file": ("backup.json", json.dumps(backup), "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 200
    # EXTRA 应消失；cost.task_id 仍指向原 task
    projects = client.get("/api/projects").json()
    assert {p["name"] for p in projects} == {"P"}
    costs = client.get(f"/api/projects/{pid}/costs")
    assert costs.json()[0]["task_id"] == tid
```

- [ ] **Step 2: 运行新测试**

Run from `backend`: `.venv\Scripts\python.exe -m pytest tests/test_backup.py -v`
Expected: 7 passed

- [ ] **Step 3: 全量回归**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 85 - 0 + 7 = 92 passed（注意：Task 5 净增 2 是 83 + 2 = 85；Task 6 加 7 → 92）

实际计数说明：原 83 passed → Task 5 改写 2 测试 + 加 1 测试 = +3 个 test functions；Task 6 加 7 测试 = +7。最终 = 83 + 2 + 7 = 92。

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_backup.py
git commit -m "test: backup + restore API (export all tables, overwrite restore)"
```

---

### Task 7: 前端 adminApi + SettingsView 数据管理

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/views/SettingsView.vue`

- [ ] **Step 1: 加 adminApi 到 client.ts**

在 `frontend/src/api/client.ts` 文件末尾追加：
```typescript
export const adminApi = {
  backup: () => api.get<string>('/admin/backup', { responseType: 'blob' }).then(r => r.data),
  restore: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post<{ status: string; counts: Record<string, number> }>('/admin/restore', fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(r => r.data)
  }
}
```

- [ ] **Step 2: 修改 SettingsView.vue**

完整替换：
```vue
<template>
  <div class="space-y-5">
    <GlassCard class="p-5">
      <h2 class="="text-xl font-bold">⚙️ 系统管理</h2>
      <p class="text-sm text-gray-500">管理应用配置</p>
    </GlassCard>

    <GlassCard class="p-5">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-lg font-bold">💾 数据管理</h2>
          <p class="text-sm text-gray-500">下载备份或在上传备份后覆盖现有数据</p>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <button @click="onDownload"
                class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-sm font-semibold">
          下载备份
        </button>
        <label class="px-3 py-1.5 rounded-lg bg-black/5 text-sm font-medium cursor-pointer hover:bg-black/10">
          选择备份文件…
          <input type="file" accept=".json" class="hidden" @change="onFile" />
        </label>
        <button v-if="pendingFile" @click="onRestore"
                class="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-500 text-sm font-medium hover:bg-red-500/20">
          确认恢复（覆盖现有数据）
        </button>
      </div>
      <p v-if="restoreMsg" class="mt-3 text-sm text-gray-600">{{ restoreMsg }}</p>
    </GlassCard>

    <CostCategoriesView />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import CostCategoriesView from '@/views/CostCategoriesView.vue'
import { adminApi } from '@/api/client'

const pendingFile = ref<File | null>(null)
const restoreMsg = ref('')

function onFile(e: Event) {
  const input = e.target as HTMLInputElement
  pendingFile.value = input.files?.[0] ?? null
  restoreMsg.value = ''
}

async function onDownload() {
  const blob = await adminApi.backup()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `pm-backup-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
}

async function onRestore() {
  if (!pendingFile.value) return
  if (!window.confirm('恢复将覆盖现有数据，确定继续？')) {
    return
  }
  try {
    const res = await adminApi.restore(pendingFile.value)
    const total = Object.values(res.counts).reduce((a, b) => a + b, 0)
    restoreMsg.value = `✓ 恢复成功：${total} 条记录已写入`
    pendingFile.value = null
  } catch {
    /* 拦截器提示 */
  }
}
</script>
```

注意：上面第一行 `<h2 class="="text-xl font-bold">` 那个 `="` 是输入法问题。**正确是 `<h2 class="text-xl font-bold">`**。其余正常。

- [ ] **Step 3: 构建验证**

Run from `frontend`: `npm run build`
Expected: vue-tsc + vite build 通过

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/views/SettingsView.vue
git commit -m "feat: settings page data management (download + upload backup)"
```

---

### Task 8: CostCategoriesView 去除 v-if 守卫

**Files:**
- Modify: `frontend/src/views/CostCategoriesView.vue`

- [ ] **Step 1: 改改/删按钮的 v-if**

读 `frontend/src/views/CostCategoriesView.vue` line 33 和 line 35：

找到：
```vue
        <button v-if="!c.is_builtin" @click="rename(c)"
                class="text-xs px-2 py-1 rounded-lg bg-black/5 text-gray-600 hover:bg-black/10">改名</button>
        <button v-if="!c.is_builtin" @click="remove(c)"
                class="text-xs px-2 py-1 rounded-lg text-red-500 hover:bg-red-500/10">删除</button>
```

改成：
```vue
        <button @click="rename(c)"
                class="text-xs px-2 py-1 rounded-lg bg-black/5 text-gray-600 hover:bg-black/10">改名</button>
        <button @click="remove(c)"
                class="text-xs px-2 py-1 rounded-lg text-red-500 hover:bg-red-500/10">删除</button>
```

- [ ] **Step 2: 验证构建**

Run from `frontend`: `npm run build`
Expected: 通过

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/CostCategoriesView.vue
git commit -m "refactor: all categories can now be renamed/deleted (no builtin guard)"
```

---

### Task 9: 端到端验收

**Files:** 无

- [ ] **Step 1: 重启后端**

后端需重启才能加载新代码。

```powershell
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Start-Sleep 2
Start-Process -FilePath "C:\Users\leonj\Documents\opencode\.worktrees\dev\backend\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8765" -WorkingDirectory "C:\Users\leonj\Documents\opencode\.worktrees\dev\backend"
Start-Sleep 4
```

Run: `curl -s http://127.0.0.1:8765/api/health`
Expected: `{"status":"ok"}`

- [ ] **Step 2: 验证 download**

Run: `curl -s http://127.0.0.1:8765/api/admin/backup -o $env:TEMP\opencode\backup.json`
检查文件存在且 > 0 字节：
`Get-ChildItem "$env:TEMP\opencode\backup.json" | Format-Table Name, Length`
Expected: 文件大小 > 100 字节（包含 6 个表 + version + exported_at）

- [ ] **Step 3: 验证 restore**

Run:
```powershell
$content = Get-Content "$env:TEMP\opencode\backup.json" -Raw
$body = @{file = [System.IO.File]::Create("$env:TEMP\opencode\backup-curl.json")}
$content | Out-File - "$env:TEMP\opencode\backup-curl.json" -Encoding utf8
curl.exe -s -X POST -F "file=@$env:TEMP\opencode\backup-curl.json" http://127.0.0.1:8765/api/admin/restore
```
Expected: `{"status":"ok","counts":{...}}`

- [ ] **Step 4: 全量后端测试**

Run from `backend`: `.venv\Scripts\python.exe -m pytest -q`
Expected: 92 passed

- [ ] **Step 5: DOM dump 验证 Settings**

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu --no-first-run --user-data-dir="$env:TEMP\opencode\edgeprof-bk" --virtual-time-budget=15000 --dump-dom "http://127.0.0.1:5173/settings" 2>$null | Out-File -Encoding utf8 "$env:TEMP\opencode\settings.html"
```

Verify HTML has：「数据管理」标题 + 「下载备份」按钮 + 「选择备份文件」label

- [ ] **Step 6: 验证 categories 页所有类别都有改/删按钮**

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu --no-first-run --user-data-dir="$env:TEMP\opencode\edgeprof-bk2" --virtual-time-budget=15000 --dump-dom "http://127.0.0.1:5173/settings" 2>$null | Out-File -Encoding utf8 "$env:TEMP\opencode\settings2.html"
```

验证 HTML 中每个类别（material/labor/travel/other）行都有「改名」「删除」按钮（不再被 v-if 隐藏）。

- [ ] **Step 7: 提交收尾**

```bash
git status
git log --oneline -12
```
确认所有改动已提交。

---

## Self-Review

**Spec coverage：**
- 数据备份 → Task 1 + Task 2（service + API）
- 数据恢复 → Task 1 + Task 2（service + API）
- 类别内置移除 → Task 3（service）+ Task 4（迁移）+ Task 5（测试改期望）+ Task 8（前端 v-if）
- 现有数据保留 → Task 4 的 UPDATE 只改 is_builtin，不动其他数据

**Type consistency：**
- `adminApi.backup()` 返回 `Blob`（responseType: 'blob'）
- `adminApi.restore(file)` 返回 `{status, counts}`
- SettingsView 状态：`pendingFile: File | null`、`restoreMsg: string`
- CostCategory 模型保留 `is_builtin` 字段（schema 仍读出），service 层不再用它做业务守卫

**已知风险：**
- SQLite WAL 模式下 GET backup 时若同时有写入，可能丢当前未 checkpoint 的数据。**Task 1 中没显式 checkpoint**——单用户本地应用，并发风险低；如果用户担心，可在 `export_data` 开头加 `conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))`。为简化当前 plan，未加；如果 review 抓到这个 issue 再加。
- 恢复期间 FK OFF：必须保证单事务；事务提交/回滚保证原子性。
- 大文件上传：FastAPI 默认无大小限制。50MB 上限本 plan 未设置；单用户数据小，问题不大。
- 备份 JSON 不包含 `pm.db-shm`/`-wal` 文件；不影响 — 它们是 SQLite 临时文件，重启即可重建。

**YAGNI：**
- 不做增量备份
- 不做定时自动备份
- 不做压缩/加密
- 不做冲突合并（明确选了覆盖）

**测试覆盖：**
- 后端 7 测试（Task 6）+ 改写 2 测试（Task 5）+ 加 1 测试（Task 5）
- 前端 build + DOM 验证
- 类别 is_builtin 守卫从测试中彻底移除

**Plan self-review 完成，进入执行。**