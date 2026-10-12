# 个人项目管理小软件 · P1 核心骨架 · 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 跑通核心骨架：能创建项目、能创建多层级任务、甘特图能展示并拖拽改日期、点击任务能进详情页、双击桌面图标能启动。

**Architecture:** 前后端分离。后端 FastAPI + SQLAlchemy + SQLite（端口 8765），前端 Vue 3 + Vite + Tailwind + Pinia + frappe-gantt（端口 5173，Vite 代理到后端）。`start.py` 拉起两个进程并打开浏览器。

**Tech Stack:** Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Alembic / SQLite / pytest；Vue 3.4 / Vite 5 / TypeScript / Tailwind 3 / Pinia 2 / frappe-gantt / vue-router 4。

**参考文档：**
- 设计：`docs/superpowers/specs/2026-08-17-personal-pm-design.md`
- UI mockup：`C:\Users\leonj\Documents\Obsidian\opencode\01-Projects\personal-pm-tool\attachments\ui-mockups\*.html`（浏览器打开）

**前置条件：**
- Python 3.11+ 已安装（验证：`python --version`）
- Node.js 18+ 已安装（验证：`node --version`）
- 工作目录：`C:\Users\leonj\Documents\opencode`

---

## 文件结构

实施 P1 阶段会创建/修改以下文件。每个文件职责单一，便于后续阶段扩展。

### 后端 (`backend/`)

```
backend/
├── pyproject.toml              # 依赖声明（uv/pip 可用）
├── alembic.ini                 # Alembic 配置
├── alembic/
│   ├── env.py                  # Alembic 环境
│   └── versions/
│       └── 0001_initial.py     # 初始迁移（3 张表）
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口 + 路由挂载
│   ├── database.py             # SQLAlchemy engine + SessionLocal + get_db
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py             # DeclarativeBase
│   │   ├── project.py          # Project ORM
│   │   ├── task.py             # Task ORM（多层级）
│   │   └── task_dependency.py  # TaskDependency ORM
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── project.py          # ProjectCreate / ProjectUpdate / ProjectRead
│   │   └── task.py             # TaskCreate / TaskUpdate / TaskRead / TaskMove
│   ├── api/
│   │   ├── __init__.py
│   │   ├── projects.py         # /api/projects/* 路由
│   │   ├── tasks.py            # /api/projects/{id}/tasks, /api/tasks/{id} 路由
│   │   └── dependencies.py     # /api/tasks/{id}/dependencies 路由
│   └── services/
│       ├── __init__.py
│       ├── project_service.py  # 业务逻辑
│       └── task_service.py     # 含层级、循环依赖检测
└── tests/
    ├── __init__.py
    ├── conftest.py             # 测试 fixture（内存 SQLite）
    ├── test_projects.py
    ├── test_tasks.py
    └── test_dependencies.py
```

### 前端 (`frontend/`)

```
frontend/
├── package.json
├── vite.config.ts              # 代理 /api 和 /ws 到 8765
├── tailwind.config.js
├── postcss.config.js
├── tsconfig.json
├── index.html
└── src/
    ├── main.ts                 # 挂载 Vue、Pinia、Router
    ├── App.vue                 # 根布局（SideRail + RouterView）
    ├── style.css               # Tailwind + Liquid Glass 工具类
    ├── router.ts               # 4 个路由
    ├── api/
    │   └── client.ts           # Axios 实例 + 类型化方法
    ├── stores/
    │   ├── projects.ts         # Pinia store
    │   └── tasks.ts            # 含层级扁平化
    ├── components/
    │   ├── SideRail.vue        # 左侧系统栏（5 主功能 + ⚙ 占位）
    │   ├── TopBar.vue          # 顶栏（导航 + 项目选择器）
    │   ├── GlassCard.vue       # 玻璃面板基础组件
    │   └── StatusBadge.vue     # 状态徽章
    └── views/
        ├── DashboardView.vue   # 总览仪表盘（基础版：项目列表 + KPI）
        ├── GanttView.vue       # 甘特图（frappe-gantt 集成 + 拖拽改日期）
        ├── TaskDetailView.vue  # 任务详情
        └── ProjectListView.vue # 项目管理（含新建项目对话框）
```

### 启动脚本（根目录）

```
start.py                        # 一键启动：后端 + 前端 + 浏览器
启动.bat                         # Windows 桌面图标入口
```

---

## 任务分解

按依赖关系排序，前面的任务产出供后续使用。

---

### Task 1: 后端项目初始化与依赖

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: 创建 `backend/pyproject.toml`**

```toml
[project]
name = "personal-pm-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "pydantic>=2.6",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "httpx>=0.27",
    "pytest-asyncio>=0.23",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]
```

- [ ] **Step 2: 创建空包标记**

创建文件 `backend/app/__init__.py`（空文件）。

- [ ] **Step 3: 创建 `backend/app/database.py`**

```python
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "pm.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# SQLite 启用 WAL 模式提升并发，busy_timeout 避免多任务编辑卡死
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 5.0},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: 创建 `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Personal PM", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: 安装依赖并验证启动**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --port 8765
```

预期：Uvicorn 启动输出 `Application startup complete.`，`http://127.0.0.1:8765/docs` 可访问。

另开终端验证：

```bash
curl http://127.0.0.1:8765/api/health
```

预期输出：`{"status":"ok"}`

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat(backend): init FastAPI app with SQLite engine"
```

---

### Task 2: SQLAlchemy 数据模型（3 张表）

**Files:**
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/project.py`
- Create: `backend/app/models/task.py`
- Create: `backend/app/models/task_dependency.py`
- Create: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建 `backend/app/models/__init__.py`**

```python
from app.models.base import Base
from app.models.project import Project
from app.models.task import Task
from app.models.task_dependency import TaskDependency

__all__ = ["Base", "Project", "Task", "TaskDependency"]
```

- [ ] **Step 2: 创建 `backend/app/models/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

> `Base` 定义在 models 层（而不是 database.py），避免循环导入并保持职责清晰：database.py 负责连接，models 负责 ORM。

- [ ] **Step 3: 删除 `app/database.py` 里的 Base 定义**

编辑 `backend/app/database.py`，删除 `class Base(DeclarativeBase): pass` 这一整段（4 行，从 `class Base` 到空行）。改为：

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
```

并在文件顶部删除 `DeclarativeBase` 导入。最终文件应是：

```python
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "pm.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 5.0},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: 创建 `backend/app/models/project.py`**

```python
from datetime import datetime
from sqlalchemy import String, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#0071e3")
    start_date: Mapped[Date | None] = mapped_column(Date)
    end_date: Mapped[Date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )
```

- [ ] **Step 5: 创建 `backend/app/models/task.py`**

```python
from datetime import date, datetime
from sqlalchemy import String, Date, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String(20), default="todo", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_milestone: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    project = relationship("Project", back_populates="tasks")
    children: Mapped[list["Task"]] = relationship(
        "Task", back_populates="parent", cascade="all, delete-orphan",
        order_by="Task.sort_order",
    )
    parent: Mapped["Task | None"] = relationship(
        "Task", back_populates="children", remote_side=[id]
    )
```

- [ ] **Step 6: 创建 `backend/app/models/task_dependency.py`**

```python
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    predecessor_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    successor_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(10), default="FS")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 7: 验证模型可创建表**

```bash
cd backend && .venv\Scripts\activate
python -c "from app.models import Base; from app.database import engine; Base.metadata.create_all(engine); print('OK')"
```

预期：`OK`。然后检查 `data/pm.db` 文件已创建。

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/
git commit -m "feat(backend): add Project, Task, TaskDependency models"
```

---

### Task 3: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/project.py`
- Create: `backend/app/schemas/task.py`

- [ ] **Step 1: 创建 `backend/app/schemas/__init__.py`**

```python
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead
from app.schemas.task import TaskCreate, TaskUpdate, TaskRead, TaskMove

__all__ = [
    "ProjectCreate", "ProjectUpdate", "ProjectRead",
    "TaskCreate", "TaskUpdate", "TaskRead", "TaskMove",
]
```

- [ ] **Step 2: 创建 `backend/app/schemas/project.py`**

```python
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = "#0071e3"
    start_date: date | None = None
    end_date: date | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
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

- [ ] **Step 3: 创建 `backend/app/schemas/task.py`**

```python
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class TaskBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    parent_id: int | None = None
    status: str = "todo"
    priority: str = "normal"
    start_date: date | None = None
    end_date: date | None = None
    progress: int = Field(0, ge=0, le=100)
    is_milestone: bool = False
    sort_order: int = 0


class TaskCreate(TaskBase):
    project_id: int | None = None


class TaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    parent_id: int | None = None
    status: str | None = None
    priority: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    progress: int | None = Field(None, ge=0, le=100)
    is_milestone: bool | None = None
    sort_order: int | None = None


class TaskMove(BaseModel):
    """拖拽改日期"""
    start_date: date
    end_date: date


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 4: 验证导入无错**

```bash
cd backend && .venv\Scripts\activate
python -c "from app.schemas import ProjectCreate, TaskCreate; print('OK')"
```

预期：`OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat(backend): add Pydantic schemas for project and task"
```

---

### Task 4: 项目服务层与 API（含 TDD）

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/project_service.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/projects.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_projects.py`

- [ ] **Step 1: 创建测试 fixture `backend/tests/conftest.py`**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.models import Base
from app.database import get_db
from app.main import app


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

- [ ] **Step 2: 写失败的测试 `backend/tests/test_projects.py`**

```python
def test_create_project(client):
    r = client.post("/api/projects", json={"name": "装修"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "装修"
    assert data["status"] == "active"
    assert data["color"] == "#0071e3"
    assert "id" in data


def test_list_projects(client):
    client.post("/api/projects", json={"name": "项目A"})
    client.post("/api/projects", json={"name": "项目B"})
    r = client.get("/api/projects")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_project(client):
    r = client.post("/api/projects", json={"name": "学习"})
    pid = r.json()["id"]
    r2 = client.get(f"/api/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "学习"


def test_get_nonexistent_returns_404(client):
    r = client.get("/api/projects/9999")
    assert r.status_code == 404


def test_update_project(client):
    pid = client.post("/api/projects", json={"name": "原"}).json()["id"]
    r = client.patch(f"/api/projects/{pid}", json={"name": "新", "color": "#ff9500"})
    assert r.status_code == 200
    assert r.json()["name"] == "新"
    assert r.json()["color"] == "#ff9500"


def test_delete_project_cascades_tasks(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    client.post(f"/api/projects/{pid}/tasks", json={"name": "T1"})
    r = client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204
    r2 = client.get(f"/api/projects/{pid}")
    assert r2.status_code == 404
```

- [ ] **Step 3: 跑测试确认失败**

```bash
cd backend && .venv\Scripts\activate
pytest tests/test_projects.py -v
```

预期：FAIL（路由 404 Not Found）

- [ ] **Step 4: 创建服务层 `backend/app/services/project_service.py`**

```python
from sqlalchemy.orm import Session
from app.models import Project
from app.schemas import ProjectCreate, ProjectUpdate


def create_project(db: Session, data: ProjectCreate) -> Project:
    p = Project(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def list_projects(db: Session) -> list[Project]:
    return db.query(Project).order_by(Project.id).all()


def get_project(db: Session, pid: int) -> Project | None:
    return db.get(Project, pid)


def update_project(db: Session, p: Project, data: ProjectUpdate) -> Project:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


def delete_project(db: Session, p: Project) -> None:
    db.delete(p)
    db.commit()
```

- [ ] **Step 5: 创建空包标记**

创建文件 `backend/app/services/__init__.py`（空）和 `backend/app/api/__init__.py`（空）。

- [ ] **Step 6: 创建路由 `backend/app/api/projects.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project
from app.schemas import ProjectCreate, ProjectUpdate, ProjectRead
from app.services import project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    return project_service.list_projects(db)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    return project_service.create_project(db, data)


@router.get("/{pid}", response_model=ProjectRead)
def get_project(pid: int, db: Session = Depends(get_db)):
    p = project_service.get_project(db, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.patch("/{pid}", response_model=ProjectRead)
def update_project(pid: int, data: ProjectUpdate, db: Session = Depends(get_db)):
    p = project_service.get_project(db, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    return project_service.update_project(db, p, data)


@router.delete("/{pid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(pid: int, db: Session = Depends(get_db)):
    p = project_service.get_project(db, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    project_service.delete_project(db, p)
    return None
```

- [ ] **Step 7: 在 main.py 挂载路由**

修改 `backend/app/main.py`，在 `app = FastAPI(...)` 之后、`@app.get("/api/health")` 之前加：

```python
from app.api.projects import router as projects_router
app.include_router(projects_router)
```

最终文件应是：

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.projects import router as projects_router

app = FastAPI(title="Personal PM", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 8: 跑测试确认通过**

```bash
cd backend && .venv\Scripts\activate
pytest tests/test_projects.py -v
```

预期：6 个测试全部 PASS

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat(backend): project CRUD API with TDD"
```

---

### Task 5: 任务服务层与 API（含 TDD，含多层级）

**Files:**
- Create: `backend/app/services/task_service.py`
- Create: `backend/app/api/tasks.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_tasks.py`

- [ ] **Step 1: 写失败的测试 `backend/tests/test_tasks.py`**

```python
def test_create_task_in_project(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    r = client.post(f"/api/projects/{pid}/tasks", json={"name": "T1"})
    assert r.status_code == 201
    assert r.json()["name"] == "T1"
    assert r.json()["project_id"] == pid


def test_list_project_tasks(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    client.post(f"/api/projects/{pid}/tasks", json={"name": "T1"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "T2"})
    r = client.get(f"/api/projects/{pid}/tasks")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_create_child_task(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    parent = client.post(f"/api/projects/{pid}/tasks", json={"name": "父"}).json()["id"]
    r = client.post(f"/api/projects/{pid}/tasks", json={"name": "子", "parent_id": parent})
    assert r.status_code == 201
    assert r.json()["parent_id"] == parent


def test_update_task(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    r = client.patch(f"/api/tasks/{tid}", json={"status": "progress", "progress": 50})
    assert r.status_code == 200
    assert r.json()["status"] == "progress"
    assert r.json()["progress"] == 50


def test_move_task_changes_dates(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    r = client.post(f"/api/tasks/{tid}/move", json={"start_date": "2026-08-20", "end_date": "2026-08-25"})
    assert r.status_code == 200
    assert r.json()["start_date"] == "2026-08-20"
    assert r.json()["end_date"] == "2026-08-25"


def test_delete_task(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    r = client.delete(f"/api/tasks/{tid}")
    assert r.status_code == 204
    r2 = client.get(f"/api/projects/{pid}/tasks")
    assert len(r2.json()) == 0
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd backend && .venv\Scripts\activate
pytest tests/test_tasks.py -v
```

预期：全部 FAIL（路由不存在）

- [ ] **Step 3: 创建服务层 `backend/app/services/task_service.py`**

```python
from datetime import date
from sqlalchemy.orm import Session
from app.models import Task
from app.schemas import TaskCreate, TaskUpdate, TaskMove


def create_task(db: Session, data: TaskCreate) -> Task:
    t = Task(**data.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def list_project_tasks(db: Session, pid: int) -> list[Task]:
    return (
        db.query(Task)
        .filter(Task.project_id == pid)
        .order_by(Task.sort_order, Task.id)
        .all()
    )


def get_task(db: Session, tid: int) -> Task | None:
    return db.get(Task, tid)


def update_task(db: Session, t: Task, data: TaskUpdate) -> Task:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


def move_task(db: Session, t: Task, data: TaskMove) -> Task:
    t.start_date = data.start_date
    t.end_date = data.end_date
    db.commit()
    db.refresh(t)
    return t


def delete_task(db: Session, t: Task) -> None:
    db.delete(t)
    db.commit()
```

- [ ] **Step 4: 创建路由 `backend/app/api/tasks.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Task
from app.schemas import TaskCreate, TaskUpdate, TaskRead, TaskMove
from app.services import task_service, project_service

router = APIRouter(tags=["tasks"])


@router.get("/api/projects/{pid}/tasks", response_model=list[TaskRead])
def list_project_tasks(pid: int, db: Session = Depends(get_db)):
    if not project_service.get_project(db, pid):
        raise HTTPException(404, "Project not found")
    return task_service.list_project_tasks(db, pid)


@router.post("/api/projects/{pid}/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(pid: int, data: TaskCreate, db: Session = Depends(get_db)):
    if not project_service.get_project(db, pid):
        raise HTTPException(404, "Project not found")
    payload = data.model_copy(update={"project_id": pid})
    return task_service.create_task(db, payload)


@router.get("/api/tasks/{tid}", response_model=TaskRead)
def get_task(tid: int, db: Session = Depends(get_db)):
    t = task_service.get_task(db, tid)
    if not t:
        raise HTTPException(404, "Task not found")
    return t


@router.patch("/api/tasks/{tid}", response_model=TaskRead)
def update_task(tid: int, data: TaskUpdate, db: Session = Depends(get_db)):
    t = task_service.get_task(db, tid)
    if not t:
        raise HTTPException(404, "Task not found")
    return task_service.update_task(db, t, data)


@router.post("/api/tasks/{tid}/move", response_model=TaskRead)
def move_task(tid: int, data: TaskMove, db: Session = Depends(get_db)):
    t = task_service.get_task(db, tid)
    if not t:
        raise HTTPException(404, "Task not found")
    return task_service.move_task(db, t, data)


@router.delete("/api/tasks/{tid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(tid: int, db: Session = Depends(get_db)):
    t = task_service.get_task(db, tid)
    if not t:
        raise HTTPException(404, "Task not found")
    task_service.delete_task(db, t)
    return None
```

- [ ] **Step 5: 在 main.py 挂载路由**

修改 `backend/app/main.py`，增加：

```python
from app.api.tasks import router as tasks_router
app.include_router(tasks_router)
```

在 `app.include_router(projects_router)` 之后插入新行。

- [ ] **Step 6: 跑测试确认通过**

```bash
cd backend && .venv\Scripts\activate
pytest tests/test_tasks.py -v
```

预期：6 个测试全部 PASS

- [ ] **Step 7: 跑全部测试确保项目 + 任务都通**

```bash
cd backend && .venv\Scripts\activate
pytest -v
```

预期：12 个测试全部 PASS

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat(backend): task CRUD API with multi-level nesting"
```

---

### Task 6: 任务依赖 API（含循环检测）

**Files:**
- Create: `backend/app/api/dependencies.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_dependencies.py`

- [ ] **Step 1: 写失败的测试 `backend/tests/test_dependencies.py`**

```python
def test_add_dependency(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    t1 = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    t2 = client.post(f"/api/projects/{pid}/tasks", json={"name": "B"}).json()["id"]
    r = client.post(f"/api/tasks/{t2}/dependencies", json={"predecessor_id": t1})
    assert r.status_code == 201
    assert r.json()["predecessor_id"] == t1
    assert r.json()["successor_id"] == t2


def test_dependency_requires_existing_tasks(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    t = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    r = client.post(f"/api/tasks/{t}/dependencies", json={"predecessor_id": 9999})
    assert r.status_code == 404


def test_self_dependency_rejected(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    t = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    r = client.post(f"/api/tasks/{t}/dependencies", json={"predecessor_id": t})
    assert r.status_code == 400


def test_cycle_rejected(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    b = client.post(f"/api/projects/{pid}/tasks", json={"name": "B"}).json()["id"]
    client.post(f"/api/tasks/{b}/dependencies", json={"predecessor_id": a})  # B 依赖 A
    r = client.post(f"/api/tasks/{a}/dependencies", json={"predecessor_id": b})  # A 不能依赖 B（环）
    assert r.status_code == 400


def test_delete_dependency(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    b = client.post(f"/api/projects/{pid}/tasks", json={"name": "B"}).json()["id"]
    dep = client.post(f"/api/tasks/{b}/dependencies", json={"predecessor_id": a}).json()["id"]
    r = client.delete(f"/api/dependencies/{dep}")
    assert r.status_code == 204
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd backend && .venv\Scripts\activate
pytest tests/test_dependencies.py -v
```

预期：全部 FAIL

- [ ] **Step 3: 创建 `backend/app/api/dependencies.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Task, TaskDependency
from app.services import task_service

router = APIRouter(tags=["dependencies"])


def _creates_cycle(db: Session, predecessor_id: int, successor_id: int) -> bool:
    """DFS 检测 predecessor -> successor 路径是否会导致环"""
    visited = set()

    def dfs(node_id: int) -> bool:
        if node_id == predecessor_id:
            return True
        if node_id in visited:
            return False
        visited.add(node_id)
        deps = (
            db.query(TaskDependency)
            .filter(TaskDependency.predecessor_id == node_id)
            .all()
        )
        return any(dfs(d.successor_id) for d in deps)

    return dfs(successor_id)


@router.post("/api/tasks/{tid}/dependencies", status_code=status.HTTP_201_CREATED)
def add_dependency(
    tid: int,
    payload: dict,
    db: Session = Depends(get_db),
):
    """payload: {predecessor_id: int, type?: str}"""
    predecessor_id = payload.get("predecessor_id")
    dep_type = payload.get("type", "FS")

    if not predecessor_id:
        raise HTTPException(400, "predecessor_id required")

    succ = task_service.get_task(db, tid)
    pred = task_service.get_task(db, predecessor_id)
    if not succ or not pred:
        raise HTTPException(404, "Task not found")

    if succ.id == pred.id:
        raise HTTPException(400, "Self-dependency not allowed")

    if _creates_cycle(db, predecessor_id, succ.id):
        raise HTTPException(400, "Dependency would create cycle")

    existing = (
        db.query(TaskDependency)
        .filter(
            TaskDependency.predecessor_id == predecessor_id,
            TaskDependency.successor_id == succ.id,
        )
        .first()
    )
    if existing:
        return existing

    dep = TaskDependency(
        predecessor_id=predecessor_id,
        successor_id=succ.id,
        type=dep_type,
    )
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep


@router.delete("/api/dependencies/{dep_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dependency(dep_id: int, db: Session = Depends(get_db)):
    dep = db.get(TaskDependency, dep_id)
    if not dep:
        raise HTTPException(404, "Dependency not found")
    db.delete(dep)
    db.commit()
    return None
```

- [ ] **Step 4: 在 main.py 挂载路由**

修改 `backend/app/main.py`，增加：

```python
from app.api.dependencies import router as deps_router
app.include_router(deps_router)
```

- [ ] **Step 5: 跑测试确认通过**

```bash
cd backend && .venv\Scripts\activate
pytest tests/test_dependencies.py -v
```

预期：5 个测试全部 PASS

- [ ] **Step 6: 跑全部测试**

```bash
cd backend && .venv\Scripts\activate
pytest -v
```

预期：17 个测试全部 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): task dependency API with cycle detection"
```

---

### Task 7: 前端项目初始化

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/style.css`
- Create: `frontend/src/env.d.ts`

- [ ] **Step 1: 创建 `frontend/package.json`**

```json
{
  "name": "personal-pm-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0",
    "frappe-gantt": "^0.6.1"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@vitejs/plugin-vue": "^5.0.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.0",
    "vite": "^5.1.0",
    "vue-tsc": "^2.0.0"
  }
}
```

- [ ] **Step 2: 创建 `frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8765', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8765', ws: true, changeOrigin: true }
    }
  }
})
```

- [ ] **Step 3: 创建 `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "noEmit": true,
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue", "env.d.ts"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: 创建 `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: 创建 `frontend/tailwind.config.js`**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      colors: {
        apple: {
          blue: '#0071e3',
          green: '#34c759',
          orange: '#ff9500',
          red: '#ff3b30',
          purple: '#af52de',
          gray: '#8e8e93'
        }
      },
      backdropBlur: { xs: '10px' },
      boxShadow: {
        glass: '0 8px 32px rgba(0,0,0,0.08), 0 1px 0 rgba(255,255,255,1) inset'
      }
    }
  },
  plugins: []
}
```

- [ ] **Step 6: 创建 `frontend/postcss.config.js`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {}
  }
}
```

- [ ] **Step 7: 创建 `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>个人 PM</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

- [ ] **Step 8: 创建 `frontend/src/env.d.ts`**

```typescript
/// <reference types="vite/client" />
```

- [ ] **Step 9: 创建 `frontend/src/style.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html, body {
    height: 100%;
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", system-ui, sans-serif;
    color: #1d1d1f;
    background:
      radial-gradient(ellipse at 15% 0%, #c7e0ff 0%, transparent 45%),
      radial-gradient(ellipse at 85% 100%, #ffd6e7 0%, transparent 45%),
      linear-gradient(180deg, #f5f5f7 0%, #ececf1 100%);
    background-attachment: fixed;
  }
}

@layer components {
  .glass {
    background: rgba(255, 255, 255, 0.65);
    backdrop-filter: blur(30px) saturate(180%);
    -webkit-backdrop-filter: blur(30px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.9);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08), 0 1px 0 rgba(255, 255, 255, 1) inset;
  }
  .glass-card {
    @apply glass rounded-2xl;
  }
}
```

- [ ] **Step 10: 创建 `frontend/src/App.vue`**

```vue
<template>
  <div class="min-h-screen">
    <h1 class="text-3xl font-bold p-8">个人 PM 启动成功 ✅</h1>
  </div>
</template>

<script setup lang="ts">
</script>
```

- [ ] **Step 11: 创建 `frontend/src/main.ts`**

```typescript
import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

createApp(App).mount('#app')
```

- [ ] **Step 12: 安装依赖**

```bash
cd frontend
npm install
```

预期：无错误，`node_modules/` 创建

- [ ] **Step 13: 启动前端验证**

```bash
cd frontend
npm run dev
```

预期：Vite 输出 `Local: http://localhost:5173/`，浏览器访问看到"个人 PM 启动成功 ✅"

- [ ] **Step 14: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): init Vue 3 + Vite + Tailwind scaffold"
```

---

### Task 8: API client + Pinia stores

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/stores/projects.ts`
- Create: `frontend/src/stores/tasks.ts`

- [ ] **Step 1: 创建类型定义 `frontend/src/api/types.ts`**

```typescript
export type ProjectStatus = 'active' | 'archived'
export type TaskStatus = 'todo' | 'progress' | 'delayed' | 'done' | 'cancelled'
export type Priority = 'low' | 'normal' | 'high' | 'urgent'

export interface Project {
  id: number
  name: string
  color: string
  start_date: string | null
  end_date: string | null
  status: ProjectStatus
  created_at: string
  updated_at: string
}

export interface Task {
  id: number
  project_id: number
  parent_id: number | null
  name: string
  description: string | null
  status: TaskStatus
  priority: Priority
  start_date: string | null
  end_date: string | null
  progress: number
  sort_order: number
  is_milestone: boolean
  created_at: string
  updated_at: string
}

export interface TaskDependency {
  id: number
  predecessor_id: number
  successor_id: number
  type: string
}
```

- [ ] **Step 2: 创建 API client `frontend/src/api/client.ts`**

```typescript
import axios from 'axios'
import type { Project, Task, TaskDependency } from './types'

const api = axios.create({ baseURL: '/api' })

// Projects
export const projectsApi = {
  list: () => api.get<Project[]>('/projects').then(r => r.data),
  get: (id: number) => api.get<Project>(`/projects/${id}`).then(r => r.data),
  create: (data: { name: string; color?: string; start_date?: string; end_date?: string }) =>
    api.post<Project>('/projects', data).then(r => r.data),
  update: (id: number, data: Partial<Project>) =>
    api.patch<Project>(`/projects/${id}`, data).then(r => r.data),
  remove: (id: number) => api.delete(`/projects/${id}`).then(() => undefined)
}

// Tasks
export const tasksApi = {
  listByProject: (projectId: number) =>
    api.get<Task[]>(`/projects/${projectId}/tasks`).then(r => r.data),
  get: (id: number) => api.get<Task>(`/tasks/${id}`).then(r => r.data),
  create: (projectId: number, data: Partial<Task>) =>
    api.post<Task>(`/projects/${projectId}/tasks`, data).then(r => r.data),
  update: (id: number, data: Partial<Task>) =>
    api.patch<Task>(`/tasks/${id}`, data).then(r => r.data),
  move: (id: number, start_date: string, end_date: string) =>
    api.post<Task>(`/tasks/${id}/move`, { start_date, end_date }).then(r => r.data),
  remove: (id: number) => api.delete(`/tasks/${id}`).then(() => undefined)
}

// Dependencies
export const depsApi = {
  listByProject: (projectId: number) =>
    api.get<TaskDependency[]>(`/projects/${projectId}/dependencies`).then(r => r.data),
  add: (taskId: number, predecessorId: number) =>
    api.post<TaskDependency>(`/tasks/${taskId}/dependencies`, { predecessor_id: predecessorId })
      .then(r => r.data),
  remove: (id: number) => api.delete(`/dependencies/${id}`).then(() => undefined)
}
```

- [ ] **Step 3: 创建项目 store `frontend/src/stores/projects.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectsApi } from '@/api/client'
import type { Project } from '@/api/types'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref<Project[]>([])
  const currentId = ref<number | null>(null)

  const current = computed(() =>
    projects.value.find(p => p.id === currentId.value) ?? null
  )

  async function fetchAll() {
    projects.value = await projectsApi.list()
    if (currentId.value === null && projects.value.length > 0) {
      currentId.value = projects.value[0].id
    }
  }

  async function create(data: { name: string; color?: string }) {
    const p = await projectsApi.create(data)
    projects.value.push(p)
    currentId.value = p.id
    return p
  }

  async function remove(id: number) {
    await projectsApi.remove(id)
    projects.value = projects.value.filter(p => p.id !== id)
    if (currentId.value === id) {
      currentId.value = projects.value[0]?.id ?? null
    }
  }

  function select(id: number) { currentId.value = id }

  return { projects, currentId, current, fetchAll, create, remove, select }
})
```

- [ ] **Step 4: 创建任务 store `frontend/src/stores/tasks.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tasksApi, depsApi } from '@/api/client'
import type { Task, TaskDependency } from '@/api/types'

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref<Task[]>([])
  const dependencies = ref<TaskDependency[]>([])

  const byId = computed(() => {
    const m = new Map<number, Task>()
    tasks.value.forEach(t => m.set(t.id, t))
    return m
  })

  const roots = computed(() => tasks.value.filter(t => t.parent_id === null))

  async function fetchByProject(projectId: number) {
    tasks.value = await tasksApi.listByProject(projectId)
    const { depsApi } = await import('@/api/client')
    dependencies.value = await depsApi.listByProject(projectId)
  }

  async function create(projectId: number, data: Partial<Task>) {
    const t = await tasksApi.create(projectId, data)
    tasks.value.push(t)
    return t
  }

  async function update(id: number, data: Partial<Task>) {
    const t = await tasksApi.update(id, data)
    const idx = tasks.value.findIndex(x => x.id === id)
    if (idx >= 0) tasks.value[idx] = t
    return t
  }

  async function move(id: number, start: string, end: string) {
    const t = await tasksApi.move(id, start, end)
    const idx = tasks.value.findIndex(x => x.id === id)
    if (idx >= 0) tasks.value[idx] = t
  }

  async function remove(id: number) {
    await tasksApi.remove(id)
    tasks.value = tasks.value.filter(t => t.id !== id)
  }

  async function addDependency(taskId: number, predecessorId: number) {
    const d = await depsApi.add(taskId, predecessorId)
    dependencies.value.push(d)
    return d
  }

  return { tasks, dependencies, byId, roots, fetchByProject, create, update, move, remove, addDependency }
})
```

- [ ] **Step 5: 启动前端验证无 TS 错误**

```bash
cd frontend
npm run build
```

预期：vue-tsc 输出无错误，vite build 成功生成 `dist/`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api frontend/src/stores
git commit -m "feat(frontend): API client and Pinia stores"
```

---

### Task 9: 路由 + 主布局（侧栏 + 顶栏）

**Files:**
- Create: `frontend/src/router.ts`
- Modify: `frontend/src/App.vue`
- Create: `frontend/src/components/SideRail.vue`
- Create: `frontend/src/components/TopBar.vue`
- Create: `frontend/src/components/GlassCard.vue`
- Create: `frontend/src/components/StatusBadge.vue`

- [ ] **Step 1: 创建 `frontend/src/components/GlassCard.vue`**

```vue
<template>
  <div class="glass-card">
    <slot />
  </div>
</template>
```

- [ ] **Step 2: 创建 `frontend/src/components/StatusBadge.vue`**

```vue
<template>
  <span :class="['inline-block text-xs font-semibold px-2 py-0.5 rounded-md', cls]">
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TaskStatus } from '@/api/types'

const props = defineProps<{ status: TaskStatus }>()

const map: Record<TaskStatus, { cls: string; label: string }> = {
  todo:       { cls: 'bg-gray-100 text-gray-700',         label: '未开始' },
  progress:   { cls: 'bg-blue-100 text-apple-blue',       label: '进行中' },
  delayed:    { cls: 'bg-orange-100 text-apple-orange',   label: '延期' },
  done:       { cls: 'bg-green-100 text-apple-green',     label: '已完成' },
  cancelled:  { cls: 'bg-purple-100 text-apple-purple',   label: '已取消' }
}
const cls = computed(() => map[props.status].cls)
const label = computed(() => map[props.status].label)
</script>
```

- [ ] **Step 3: 创建 `frontend/src/components/SideRail.vue`**

```vue
<template>
  <aside class="glass-card sticky top-5 p-3 flex flex-col items-center gap-1 self-start">
    <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl
                bg-gradient-to-br from-apple-blue to-apple-purple text-transparent">
      <span class="bg-gradient-to-br from-apple-blue to-apple-purple
                   bg-clip-text text-transparent font-bold">◉</span>
    </div>
    <div class="w-8 h-px bg-black/10 my-1"></div>
    <RailIcon v-for="item in mainItems" :key="item.path" :to="item.path" :icon="item.icon"
              :active="isActive(item.path)" :title="item.label" />
    <div class="w-8 h-px bg-black/10 my-1"></div>
    <RailIcon to="/settings" icon="⚙" :title="系统管理" />
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import RailIcon from './RailIcon.vue'

const route = useRoute()
const mainItems = [
  { path: '/dashboard', icon: '📊', label: '总览仪表盘' },
  { path: '/gantt',     icon: '📅', label: '甘特图' },
  { path: '/tasks',     icon: '✅', label: '任务管理' },
  { path: '/costs',     icon: '💰', label: '费用记录' },
  { path: '/inbox',     icon: '📥', label: '临时收件箱' }
]

function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}
</script>
```

- [ ] **Step 4: 创建 `frontend/src/components/RailIcon.vue`**

```vue
<template>
  <RouterLink
    :to="to"
    :title="title"
    class="w-12 h-12 rounded-2xl flex items-center justify-center text-xl cursor-pointer
           transition-all hover:bg-black/5 hover:scale-105"
    :class="active ? 'bg-gradient-to-br from-apple-blue to-indigo-500 text-white shadow-lg' : 'text-gray-500'"
  >
    {{ icon }}
  </RouterLink>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
defineProps<{ to: string; icon: string; title: string; active?: boolean }>()
</script>
```

- [ ] **Step 5: 创建 `frontend/src/components/TopBar.vue`**

```vue
<template>
  <GlassCard class="flex items-center justify-between px-5 py-3">
    <div class="text-lg font-bold bg-gradient-to-r from-apple-blue to-apple-purple
                bg-clip-text text-transparent">
      📋 个人 PM
    </div>
    <nav class="flex gap-1">
      <button v-for="n in nav" :key="n.path"
              @click="$router.push(n.path)"
              :class="['px-3 py-1.5 rounded-lg text-sm font-medium transition',
                       $route.path === n.path
                         ? 'bg-apple-blue/15 text-apple-blue'
                         : 'text-gray-500 hover:bg-black/5']">
        {{ n.label }}
      </button>
    </nav>
    <div class="flex gap-2">
      <button class="w-8 h-8 rounded-lg bg-white/60 border border-black/5">🔍</button>
      <button class="w-8 h-8 rounded-lg bg-white/60 border border-black/5">🌙</button>
    </div>
  </GlassCard>
</template>

<script setup lang="ts">
import GlassCard from './GlassCard.vue'
const nav = [
  { path: '/dashboard', label: '总览' },
  { path: '/gantt',     label: '甘特图' },
  { path: '/tasks',     label: '任务' },
  { path: '/costs',     label: '费用' },
  { path: '/inbox',     label: '收件箱' }
]
</script>
```

- [ ] **Step 6: 创建 `frontend/src/router.ts`**

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('@/views/DashboardView.vue') },
  { path: '/gantt', component: () => import('@/views/GanttView.vue') },
  { path: '/gantt/:projectId', component: () => import('@/views/GanttView.vue') },
  { path: '/gantt/:projectId/task/:taskId', component: () => import('@/views/TaskDetailView.vue') },
  { path: '/tasks', component: () => import('@/views/ProjectListView.vue') },
  { path: '/costs', component: () => import('@/views/DashboardView.vue') },
  { path: '/inbox', component: () => import('@/views/DashboardView.vue') },
  { path: '/settings', component: () => import('@/views/DashboardView.vue') }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})
```

> P1 阶段 4 个非核心路由复用 DashboardView 占位，P2/P3 阶段再替换为真实页面。

- [ ] **Step 7: 替换 `frontend/src/App.vue`**

```vue
<template>
  <div class="max-w-[1500px] mx-auto p-5 grid grid-cols-[72px_1fr] gap-4 min-h-screen">
    <SideRail />
    <div class="flex flex-col gap-4">
      <TopBar />
      <RouterView />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import SideRail from '@/components/SideRail.vue'
import TopBar from '@/components/TopBar.vue'
import { useProjectsStore } from '@/stores/projects'

const projects = useProjectsStore()

onMounted(() => {
  projects.fetchAll()
})
</script>
```

- [ ] **Step 8: 创建占位视图 `frontend/src/views/DashboardView.vue`**

```vue
<template>
  <GlassCard class="p-8 text-center">
    <h2 class="text-2xl font-bold mb-2">📊 总览仪表盘</h2>
    <p class="text-gray-500">P2 阶段实现完整内容。当前仅占位。</p>
    <p class="mt-4 text-sm text-gray-400">项目数: {{ projects.projects.length }}</p>
  </GlassCard>
</template>

<script setup lang="ts">
import GlassCard from '@/components/GlassCard.vue'
import { useProjectsStore } from '@/stores/projects'
const projects = useProjectsStore()
</script>
```

- [ ] **Step 9: 创建占位视图 `frontend/src/views/ProjectListView.vue`**

```vue
<template>
  <GlassCard class="p-8">
    <h2 class="text-2xl font-bold mb-4">📁 项目管理</h2>
    <button @click="onCreate" class="bg-apple-blue text-white px-4 py-2 rounded-lg">
      + 新建项目
    </button>
    <ul class="mt-4 space-y-2">
      <li v-for="p in projects.projects" :key="p.id"
          class="p-3 rounded-lg bg-white/60 flex items-center justify-between">
        <span class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full" :style="{ background: p.color }"></span>
          {{ p.name }}
        </span>
        <button @click="projects.remove(p.id)" class="text-red-500 text-sm">删除</button>
      </li>
    </ul>
  </GlassCard>
</template>

<script setup lang="ts">
import GlassCard from '@/components/GlassCard.vue'
import { useProjectsStore } from '@/stores/projects'
const projects = useProjectsStore()

async function onCreate() {
  const name = prompt('项目名')
  if (name) await projects.create({ name })
}
</script>
```

- [ ] **Step 10: 创建 `frontend/src/views/GanttView.vue` 占位**

```vue
<template>
  <GlassCard class="p-8">
    <h2 class="text-2xl font-bold mb-2">📅 甘特图</h2>
    <p class="text-gray-500">P1 阶段任务 10 实现完整甘特图。</p>
  </GlassCard>
</template>

<script setup lang="ts">
import GlassCard from '@/components/GlassCard.vue'
</script>
```

- [ ] **Step 11: 创建 `frontend/src/views/TaskDetailView.vue` 占位**

```vue
<template>
  <GlassCard class="p-8">
    <h2 class="text-2xl font-bold mb-2">✅ 任务详情</h2>
    <p class="text-gray-500">P1 阶段任务 11 实现完整内容。当前仅占位。</p>
    <p class="mt-2 text-sm text-gray-400">任务 ID: {{ $route.params.taskId }}</p>
  </GlassCard>
</template>

<script setup lang="ts">
import GlassCard from '@/components/GlassCard.vue'
</script>
```

- [ ] **Step 12: 更新 `frontend/src/main.ts` 挂载路由**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- [ ] **Step 13: 启动验证**

```bash
cd frontend
npm run dev
```

预期：浏览器访问 `http://localhost:5173`，看到左侧栏 5 个图标、顶栏、占位 Dashboard。点击"📁 项目管理"创建项目，刷新仍在。

- [ ] **Step 14: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): router + main layout (SideRail, TopBar)"
```

---

### Task 10: 甘特图页（frappe-gantt 集成 + 拖拽改日期）

**Files:**
- Modify: `frontend/src/views/GanttView.vue`
- Modify: `frontend/src/views/GanttView.vue` (样式)

- [ ] **Step 1: 创建 `frontend/src/views/GanttView.vue` 完整版**

```vue
<template>
  <GlassCard class="p-5">
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-3">
        <button @click="prevMonth" class="w-8 h-8 rounded-lg bg-white/60 border border-black/5">◀</button>
        <button @click="goToday" class="px-3 py-1.5 rounded-lg bg-apple-blue/10 text-apple-blue text-sm font-semibold">今天</button>
        <button @click="nextMonth" class="w-8 h-8 rounded-lg bg-white/60 border border-black/5">▶</button>
        <span class="ml-3 font-semibold">{{ periodLabel }}</span>
      </div>
      <div class="flex gap-1 p-1 bg-black/5 rounded-lg">
        <button v-for="z in ['日','周','月','季']" :key="z"
                @click="zoom = z"
                :class="['px-3 py-1 text-xs rounded-md',
                         zoom === z ? 'bg-white shadow font-semibold' : 'text-gray-500']">
          {{ z }}
        </button>
      </div>
    </div>

    <div v-if="projects.currentId" class="flex items-center gap-2 mb-3">
      <select v-model="selectedProjectId" @change="onProjectChange"
              class="px-3 py-1.5 rounded-lg bg-white/70 border border-black/5 text-sm font-semibold">
        <option v-for="p in projects.projects" :key="p.id" :value="p.id">
          {{ p.name }}
        </option>
      </select>
      <button @click="showNewProject = true"
              class="px-3 py-1.5 rounded-lg bg-apple-blue text-white text-sm font-semibold">
        + 新建项目
      </button>
    </div>

    <div v-if="!projects.currentId" class="text-center py-12 text-gray-500">
      还没有项目，点击"新建项目"开始
    </div>

    <div v-else class="flex">
      <!-- 左侧任务列表 -->
      <div class="w-72 border-r border-black/5">
        <div v-for="t in visibleTasks" :key="t.id"
             class="flex items-center gap-2 px-4 py-2 border-b border-black/5 text-sm cursor-pointer hover:bg-white/40"
             :class="{ 'bg-black/[0.03] font-bold': !t.parent_id }"
             @click="$router.push(`/gantt/${selectedProjectId}/task/${t.id}`)">
          <span class="flex-1 truncate">{{ t.name }}</span>
          <StatusBadge :status="t.status" />
        </div>
        <button @click="addTask" class="w-full p-3 text-sm text-apple-blue font-semibold hover:bg-white/40">
          + 添加任务
        </button>
      </div>

      <!-- 右侧 frappe-gantt 画布 -->
      <div class="flex-1 overflow-x-auto">
        <div ref="ganttRef"></div>
      </div>
    </div>

    <!-- 新建项目对话框 -->
    <div v-if="showNewProject" class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50"
         @click.self="showNewProject = false">
      <GlassCard class="p-6 w-96">
        <h3 class="text-lg font-bold mb-3">新建项目</h3>
        <input v-model="newProjectName" placeholder="项目名"
               class="w-full px-3 py-2 rounded-lg border border-black/10 mb-3" />
        <div class="flex gap-2 justify-end">
          <button @click="showNewProject = false" class="px-3 py-1.5 rounded-lg bg-black/5">取消</button>
          <button @click="confirmNewProject" class="px-3 py-1.5 rounded-lg bg-apple-blue text-white">创建</button>
        </div>
      </GlassCard>
    </div>
  </GlassCard>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick, onUnmounted } from 'vue'
import Gantt from 'frappe-gantt'
import GlassCard from '@/components/GlassCard.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useProjectsStore } from '@/stores/projects'
import { useTasksStore } from '@/stores/tasks'
import { addDays, format } from 'date-fns'

const projects = useProjectsStore()
const tasks = useTasksStore()
const ganttRef = ref<HTMLElement>()
let ganttInstance: any = null

const zoom = ref('月')
const showNewProject = ref(false)
const newProjectName = ref('')
const selectedProjectId = ref<number | null>(projects.currentId)
const cursor = ref(new Date())

const visibleTasks = computed(() =>
  tasks.tasks.filter(t => t.parent_id === null || tasks.byId.get(t.parent_id!)?.parent_id === null)
)

const periodLabel = computed(() => format(cursor.value, 'yyyy 年 M 月'))

function prevMonth() { cursor.value = addDays(cursor.value, -30); render() }
function nextMonth() { cursor.value = addDays(cursor.value, 30); render() }
function goToday() { cursor.value = new Date(); render() }

async function onProjectChange() {
  projects.select(selectedProjectId.value!)
  await tasks.fetchByProject(selectedProjectId.value!)
  render()
}

async function addTask() {
  const name = prompt('任务名')
  if (!name) return
  await tasks.create(selectedProjectId.value!, { name, start_date: format(new Date(), 'yyyy-MM-dd'), end_date: format(addDays(new Date(), 7), 'yyyy-MM-dd') })
  render()
}

async function confirmNewProject() {
  if (!newProjectName.value.trim()) return
  await projects.create({ name: newProjectName.value })
  newProjectName.value = ''
  showNewProject.value = false
  selectedProjectId.value = projects.currentId
  await onProjectChange()
}

function toGanttTasks() {
  return tasks.tasks
    .filter(t => t.start_date && t.end_date)
    .map(t => ({
      id: String(t.id),
      name: t.name,
      start: t.start_date!,
      end: t.end_date!,
      progress: t.progress,
      dependencies: tasks.dependencies
        .filter(d => d.successor_id === t.id)
        .map(d => String(d.predecessor_id))
        .join(','),
      custom_class: `gantt-${t.status}`
    }))
}

function render() {
  if (!ganttRef.value) return
  ganttRef.value.innerHTML = ''
  const data = toGanttTasks()
  if (data.length === 0) {
    ganttRef.value.innerHTML = '<div class="text-center py-12 text-gray-400">该项目暂无任务</div>'
    return
  }
  ganttInstance = new Gantt(ganttRef.value, data, {
    view_mode: 'Month',
    bar_height: 22,
    padding: 14,
    readonly: false,
    on_date_change: async (task: any, start: Date, end: Date) => {
      try {
        await tasks.move(Number(task.id), format(start, 'yyyy-MM-dd'), format(end, 'yyyy-MM-dd'))
      } catch (e) {
        console.error('Move failed', e)
      }
    }
  })
}

watch(() => tasks.tasks.length, () => nextTick(render))

onMounted(async () => {
  if (selectedProjectId.value) {
    await tasks.fetchByProject(selectedProjectId.value)
    await nextTick()
    render()
  }
})

onUnmounted(() => {
  if (ganttInstance) ganttInstance = null
})
</script>

<style>
/* frappe-gantt 默认样式覆盖，套用 Liquid Glass 主题 */
.gantt .bar-wrapper .bar {
  fill: url(#bar-gradient);
  stroke: rgba(0,0,0,0.1);
  rx: 6;
}
.gantt-todo       .bar { fill: #8e8e93 !important; }
.gantt-progress   .bar { fill: #0071e3 !important; }
.gantt-delayed    .bar { fill: #ff9500 !important; }
.gantt-done       .bar { fill: #34c759 !important; opacity: 0.85; }
.gantt-cancelled  .bar { fill: #af52de !important; opacity: 0.6; }
.gantt .bar-label {
  fill: white;
  font-weight: 600;
  font-size: 11px;
}
</style>
```

- [ ] **Step 2: 添加 frappe-gantt 的 CSS**

修改 `frontend/src/style.css`，在 `@layer components` 块里添加（用 `@import` 会比较麻烦，直接在 main.ts 引入更简单）：

修改 `frontend/src/main.ts`：

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import './style.css'
import 'frappe-gantt/dist/frappe-gantt.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- [ ] **Step 3: 安装 date-fns**

```bash
cd frontend
npm install date-fns
```

- [ ] **Step 4: 启动验证**

后端先启动：

```bash
cd backend && .venv\Scripts\activate && uvicorn app.main:app --port 8765
```

另开终端启动前端：

```bash
cd frontend && npm run dev
```

预期：
- 浏览器访问 `http://localhost:5173/gantt`
- 看到日期导航、缩放按钮、任务列表、甘特图区域
- 新建项目后能添加任务（带默认日期）
- 甘特图渲染任务条，5 种状态颜色正确（按 `.gantt-todo` 等 class）
- 拖拽任务条改日期后，刷新仍保留（持久化到 SQLite）

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): Gantt view with frappe-gantt integration + drag-to-move"
```

---

### Task 11: 任务详情页

**Files:**
- Modify: `frontend/src/views/TaskDetailView.vue`

- [ ] **Step 1: 创建 `frontend/src/views/TaskDetailView.vue` 完整版**

```vue
<template>
  <div class="text-sm text-gray-500 mb-2">
    <button @click="$router.back()" class="hover:underline">← 返回</button>
  </div>
  <GlassCard class="p-6" v-if="task">
    <div class="flex items-center gap-2 mb-4">
      <StatusBadge :status="task.status" />
      <span class="text-xs px-2 py-0.5 rounded bg-gray-100">{{ task.priority }}</span>
    </div>
    <h1 class="text-3xl font-bold mb-1">{{ task.name }}</h1>
    <p class="text-sm text-gray-500 mb-4">任务 #{{ task.id }} · 项目 #{{ task.project_id }}</p>

    <div class="mb-4">
      <div class="flex justify-between text-xs text-gray-500 mb-1">
        <span>进度</span><span class="text-apple-blue font-bold">{{ task.progress }}%</span>
      </div>
      <div class="h-2 bg-black/5 rounded-full overflow-hidden">
        <div class="h-full bg-gradient-to-r from-sky-400 to-apple-blue" :style="{ width: task.progress + '%' }"></div>
      </div>
    </div>

    <div class="grid grid-cols-4 gap-3 p-3 bg-black/[0.02] rounded-xl">
      <div>
        <div class="text-[10px] uppercase text-gray-500 mb-1">开始</div>
        <div class="text-sm font-semibold">{{ task.start_date || '—' }}</div>
      </div>
      <div>
        <div class="text-[10px] uppercase text-gray-500 mb-1">截止</div>
        <div class="text-sm font-semibold">{{ task.end_date || '—' }}</div>
      </div>
      <div>
        <div class="text-[10px] uppercase text-gray-500 mb-1">负责人</div>
        <div class="text-sm font-semibold">👤 你</div>
      </div>
      <div>
        <div class="text-[10px] uppercase text-gray-500 mb-1">工时</div>
        <div class="text-sm font-semibold">—</div>
      </div>
    </div>

    <div class="mt-4 text-sm leading-relaxed">
      {{ task.description || '暂无描述' }}
    </div>

    <div class="mt-6 flex gap-2 pt-4 border-t border-black/5">
      <button @click="markDone" class="bg-gradient-to-br from-apple-blue to-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-semibold">
        ✓ 标记完成
      </button>
      <button @click="cycleStatus" class="bg-black/5 px-4 py-2 rounded-lg text-sm">切换状态</button>
      <button @click="$router.push('/gantt')" class="bg-black/5 px-4 py-2 rounded-lg text-sm ml-auto">返回甘特图</button>
    </div>
  </GlassCard>
  <GlassCard v-else class="p-8 text-center text-gray-500">
    任务不存在或已删除
  </GlassCard>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import GlassCard from '@/components/GlassCard.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { tasksApi } from '@/api/client'
import type { Task, TaskStatus } from '@/api/types'

const route = useRoute()
const task = ref<Task | null>(null)

async function load() {
  const tid = Number(route.params.taskId)
  try {
    task.value = await tasksApi.get(tid)
  } catch {
    task.value = null
  }
}

async function markDone() {
  if (!task.value) return
  const updated = await tasksApi.update(task.value.id, { status: 'done', progress: 100 })
  task.value = updated
}

async function cycleStatus() {
  if (!task.value) return
  const order: TaskStatus[] = ['todo', 'progress', 'delayed', 'done', 'cancelled']
  const next = order[(order.indexOf(task.value.status) + 1) % order.length]
  const updated = await tasksApi.update(task.value.id, { status: next })
  task.value = updated
}

onMounted(load)
watch(() => route.params.taskId, load)
</script>
```

- [ ] **Step 2: 启动验证**

```bash
cd frontend && npm run dev
```

预期：
- 在甘特图点击某个任务 → 跳转到 `/gantt/{projectId}/task/{taskId}`
- 看到任务详情（标题、状态、进度、日期、操作按钮）
- 点"标记完成" → 状态变已完成，进度 100%

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/TaskDetailView.vue
git commit -m "feat(frontend): TaskDetailView with status cycle and mark-done"
```

---

### Task 12: 启动脚本（start.py + 启动.bat）

**Files:**
- Create: `start.py`
- Create: `启动.bat`

- [ ] **Step 1: 创建 `start.py`（仓库根目录）**

```python
"""
一键启动：拉起 FastAPI 后端 + Vite 前端 + 自动打开浏览器
使用：双击 启动.bat 或 python start.py
"""
import os
import sys
import time
import socket
import subprocess
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

PYTHON = sys.executable
NPM = "npm.cmd" if os.name == "nt" else "npm"


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for_port(port: int, timeout: float = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if port_in_use(port):
            return True
        time.sleep(0.5)
    return False


def init_backend():
    """首次启动时初始化 venv + 安装依赖"""
    venv = BACKEND_DIR / ".venv"
    if not venv.exists():
        print("→ 创建 Python 虚拟环境 ...")
        subprocess.check_call([PYTHON, "-m", "venv", str(venv)])
    pip = venv / "Scripts" / "pip.exe"
    print("→ 安装/更新后端依赖 ...")
    subprocess.check_call([str(pip), "install", "-e", ".[dev]"], cwd=BACKEND_DIR)


def init_frontend():
    """首次启动时 npm install"""
    if not (FRONTEND_DIR / "node_modules").exists():
        print("→ 安装前端依赖（首次需要 1-3 分钟）...")
        subprocess.check_call([NPM, "install"], cwd=FRONTEND_DIR, shell=True)


def main():
    print("🚀 个人 PM 启动器")
    print("─" * 40)

    # 1. 检查端口
    if port_in_use(8765):
        print("⚠  端口 8765 已占用，假设后端已在运行")
        backend_running = True
    else:
        backend_running = False
        init_backend()
        print("→ 启动后端 (FastAPI @ 8765) ...")
        venv_python = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
        subprocess.Popen(
            [str(venv_python), "-m", "uvicorn", "app.main:app", "--port", "8765"],
            cwd=BACKEND_DIR,
            creationflags=subprocess.DETACHED_PROCESS if os.name == "nt" else 0,
        )

    if port_in_use(5173):
        print("⚠  端口 5173 已占用，假设前端已在运行")
    else:
        init_frontend()
        print("→ 启动前端 (Vite @ 5173) ...")
        subprocess.Popen(
            [NPM, "run", "dev"],
            cwd=FRONTEND_DIR,
            shell=True,
            creationflags=subprocess.DETACHED_PROCESS if os.name == "nt" else 0,
        )

    # 2. 等待服务就绪
    if not backend_running:
        print("→ 等待后端就绪 ...")
        if not wait_for_port(8765):
            print("✗ 后端启动超时，请检查日志")
            return
    if not wait_for_port(5173, timeout=60):
        print("✗ 前端启动超时，请检查日志")
        return

    # 3. 打开浏览器
    print("✓ 服务就绪，打开浏览器 ...")
    time.sleep(1)
    webbrowser.open("http://localhost:5173")
    print("\n📌 关闭两个窗口可停止服务：")
    print("   - 任务管理器 → 结束 uvicorn.exe 和 node.exe")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已取消")
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        input("按 Enter 退出...")
```

- [ ] **Step 2: 创建 `启动.bat`**

```batch
@echo off
chcp 65001 >nul
cd /d "%~dp0"
python start.py
pause
```

- [ ] **Step 3: 验证启动脚本**

关闭所有正在运行的后端/前端进程，然后双击 `启动.bat` 或运行：

```bash
python start.py
```

预期：
1. 看到 "🚀 个人 PM 启动器"
2. 自动检测端口、安装依赖（如需要）、启动两个服务
3. 浏览器自动打开 `http://localhost:5173`
4. 能正常使用甘特图、创建任务、查看详情

- [ ] **Step 4: Commit**

```bash
git add start.py 启动.bat
git commit -m "feat: one-click startup script (start.py + 启动.bat)"
```

---

### Task 13: P1 端到端验收

- [ ] **Step 1: 启动服务**

```bash
python start.py
```

- [ ] **Step 2: 验收清单（来自 spec §9 P1）**

逐项手动验证：

- [ ] 浏览器自动打开 `http://localhost:5173`
- [ ] 左侧栏显示 5 个主功能图标 + ⚙ 系统管理占位
- [ ] 点击"📁 项目管理"或"📅 甘特图"里的"+ 新建项目"，创建"测试项目"
- [ ] 在甘特图页添加至少 3 个任务：
  - 任务1：开始今天，截止 +7 天
  - 任务2：开始 +5 天，截止 +12 天（依赖任务1）
  - 任务3：开始 +10 天，截止 +15 天
- [ ] 创建子任务：任务3 下嵌套"子任务 A"
- [ ] 5 种状态颜色都正确（默认全部 `todo` 灰；点详情页"切换状态"循环查看）
- [ ] 拖拽甘特图上的任务条，日期改变；刷新浏览器日期保留
- [ ] 依赖箭头连接任务1 → 任务2（创建时通过 API 添加）

手动创建依赖（在浏览器控制台 F12）：

```javascript
const tasks = await (await fetch('/api/projects/1/tasks')).json()
const t1 = tasks[0].id, t2 = tasks[1].id
await fetch(`/api/tasks/${t2}/dependencies`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({predecessor_id: t1})
})
location.reload()
```

依赖箭头应在甘特图上可见。

- [ ] **Step 3: 关闭所有进程**

任务管理器 → 结束 `uvicorn.exe` 和 `node.exe`。或运行：

```bash
taskkill /F /IM uvicorn.exe /IM node.exe
```

- [ ] **Step 4: 标记 P1 完成**

```bash
git tag p1-complete
git log --oneline | head -20
```

---

## P1 完成检查清单

- [ ] 后端 17 个 pytest 全部通过
- [ ] `npm run build` 无 TS 错误
- [ ] 双击 `启动.bat` 能启动并打开浏览器
- [ ] 能创建项目、多层级任务、依赖、详情页、拖拽改日期

## 下一步

P1 完成后告诉我，我开始创建 **P2 plan**（费用 + 附件 + 备份），预计 3-4 小时实施量。