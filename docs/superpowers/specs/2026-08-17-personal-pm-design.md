# 个人项目管理小软件 · 设计文档

**日期**：2026-08-17
**作者**：opencode (brainstorming session)
**状态**：待用户审阅

---

## 1. 项目概述

### 1.1 一句话定位
**单人本地使用的项目管理小工具**：以甘特图为视觉中心，附带费用统计与临时任务收件箱。

### 1.2 用户原始需求
1. 甘特计划图（日历方式展示）
2. 任务标签管理（未开始 / 已完成 / 延期等）
3. 项目费用记录与统计
4. 临时任务记录与提醒

### 1.3 隐藏需求（brainstorm 阶段补充确认）
| # | 需求点 | 说明 |
|---|---|---|
| H1 | 多项目并行 + 总览仪表盘 | 同时跟踪多个项目，有统一总览 |
| H2 | 任务依赖关系（前置任务） | A 必须先完成 B 才能开始；甘特图自动连箭头 |
| H3 | 多层级任务嵌套 | 任务可建子任务，递归深度不限 |
| H4 | 5 种内置状态 | 未开始 / 进行中 / 延期 / 已完成 / 已取消 |
| H5 | 临时任务细分为两类 | 插队任务（绑定时间） + 点子收件箱（无时间） |
| H6 | 提醒触发三种时机 | 到期提醒 + 提前预警（默认1 天） + 延期警告 |
| H7 | 费用多维度统计 | 按项目 / 按类别 / 按月份 |
| H8 | 附件上传 | 费用挂发票照片、任务挂文档 |
| H9 | Apple Liquid Glass 视觉风格 + 亮色 | 用户明确指定 |
| H10 | 全局搜索 + 多条件筛选 | 任务多了能搜 |
| H11 | 手动 JSON 备份/导入 | 含 SQLite 数据 + 附件 zip |
| H12 | 双击桌面图标启动 | 生成 `启动.bat` 一键启动后端 + 前端 + 浏览器 |

### 1.4 明确不做（YAGNI）
- ❌ 用户登录与权限（单人本地）
- ❌ 多人协作
- ❌ 云同步
- ❌ 邮件/SMS 提醒
- ❌ 报销流程
- ❌ 移动端

---

## 2. 技术栈

| 层 | 选型 | 理由 |
|---|---|---|
| 前端框架 | Vue 3 + Vite | 甘特图库 Vue 生态最丰富 |
| 前端 UI | Tailwind CSS + 自定义 Liquid Glass 组件 | 实现 Apple 风格 |
| 前端图表 | frappe-gantt | 成熟的甘特图组件，支持依赖关系 |
| 前端状态 | Pinia | Vue 3 官方推荐 |
| 前端路由 | Vue Router | 标准方案 |
| 后端框架 | FastAPI | 异步、自动 OpenAPI 文档 |
| 后端 ORM | SQLAlchemy 2.0 + Alembic | Python 生态最成熟 |
| 数据库 | SQLite | 单文件、易备份、适合单机 |
| 后台调度 | APScheduler | 每 60 秒扫描到期任务 |
| 实时推送 | WebSocket（FastAPI 内置） | 提醒实时推送到前端 |
| 浏览器通知 | Notification API | 原生桌面通知 |
| 启动脚本 | Python `start.py` + Windows `.bat` | 一键启动 |

---

## 3. 系统架构

```
┌────────────────────────────────────────────────────────┐
│ 浏览器（Vue 3 SPA）                                    │
│  · Pinia / Vue Router / Tailwind                       │
│  · frappe-gantt（甘特图）                              │
│  · Notification API（提醒）                            │
│  · WebSocket 客户端                                    │
└────────────────────────────────────────────────────────┘ ↑ HTTP / WebSocket (localhost)
              ↓
┌────────────────────────────────────────────────────────┐
│ FastAPI（Uvicorn @ 127.0.0.1:8765）                     │
│  · REST API（项目 / 任务 / 费用 / 附件 / 备份）        │
│  · WebSocket /ws/alerts                                │
│  · APScheduler（每 60 秒扫描）                         │
│  · 服务层 TaskService / CostService / AlertService     │
│  · 数据层 SQLAlchemy ORM                               │
└────────────────────────────────────────────────────────┘
              ↓
┌────────────────────────────────────────────────────────┐
│ data/                                                  │
│  ├── pm.db                  ← SQLite 主库              │
│  ├── attachments/           ← 附件原文件               │
│  └── backups/               ← 导出 JSON 快照           │
└────────────────────────────────────────────────────────┘

启动：双击 启动.bat → start.py 拉起 uvicorn + vite dev → 自动开浏览器
```

### 3.1 端口分配
- 后端 FastAPI: `127.0.0.1:8765`
- 前端 Vite dev: `127.0.0.1:5173`（Vite 代理 `/api` 和 `/ws` 到 8765）

### 3.2 启动脚本
`启动.bat` 内部调用 `start.py`，后者：
1. 检查 `data/` 目录是否存在，不存在则创建
2. 检查 `pm.db` 是否存在，不存在则初始化 schema
3. 启动 uvicorn（后台进程）
4. 启动 vite dev（后台进程）
5. 等待 3 秒后用 `webbrowser.open` 打开 `http://localhost:5173`
6. 关闭脚本主进程，两个子进程继续运行

---

## 4. 数据模型

### 4.1 表结构

#### `projects`（项目）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT NOT NULL | 项目名 |
| color | TEXT | 标识色 hex（如 `#0071e3`） |
| start_date | DATE | 项目起始日 |
| end_date | DATE | 项目截止日 |
| status | TEXT | active / archived |
| created_at | DATETIME | |
| updated_at | DATETIME | |

#### `tasks`（任务，多层级）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | |
| project_id | INTEGER FK → projects.id | 所属项目 |
| parent_id | INTEGER FK → tasks.id NULL | 父任务（多层级） |
| name | TEXT NOT NULL | 任务名 |
| description | TEXT | 富文本描述 |
| status | TEXT NOT NULL | todo / progress / delayed / done / cancelled |
| priority | TEXT | low / normal / high / urgent |
| start_date | DATE | |
| end_date | DATE | |
| progress | INTEGER 0-100 | 进度百分比 |
| sort_order | INTEGER | 同级排序 |
| is_milestone | BOOLEAN | 是否里程碑 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

索引：`idx_tasks_project` (project_id), `idx_tasks_parent` (parent_id), `idx_tasks_status` (status)

#### `task_dependencies`（任务依赖关系）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | |
| predecessor_id | INTEGER FK → tasks.id | 前置任务 |
| successor_id | INTEGER FK → tasks.id | 后继任务 |
| type | TEXT | FS（完成-开始）/ SS / FF / SF，默认 FS |

#### `costs`（费用）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | |
| project_id | INTEGER FK → projects.id | 所属项目 |
| category | TEXT NOT NULL | material / labor / travel / other |
| amount | REAL NOT NULL | 金额（元） |
| description | TEXT | 备注 |
| spent_at | DATE NOT NULL | 支出日期 |
| created_at | DATETIME | |

索引：`idx_costs_project_spent` (project_id, spent_at)

#### `attachments`（附件）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | |
| filename | TEXT | 磁盘文件名（UUID） |
| original_name | TEXT | 原始文件名 |
| mime_type | TEXT | |
| size | INTEGER | 字节 |
| ref_type | TEXT | task / cost |
| ref_id | INTEGER | 关联的任务或费用 ID |
| uploaded_at | DATETIME | |

物理路径：`data/attachments/{uuid}.{ext}`

#### `inbox_items`（收件箱：插队 + 点子）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | |
| kind | TEXT NOT NULL | interrupt（插队） / idea（点子） |
| title | TEXT NOT NULL | |
| notes | TEXT | |
| priority | TEXT | low / normal / high / urgent |
| due_at | DATETIME | 仅插队任务有 |
| project_id | INTEGER FK NULL | 插队任务可关联项目 |
| promoted_task_id | INTEGER FK NULL | 转正后指向生成的 task.id |
| status | TEXT | active / completed / archived |
| created_at | DATETIME | |
| completed_at | DATETIME NULL | |

### 4.2 触发器 / 计算字段
- **延期状态**：每日 00:00 扫描，end_date < today 且 status != done/cancelled → 自动改为 `delayed`
- **项目进度**：SUM(task.progress * weight) / SUM(weight)，叶子任务权重为 1
- **依赖检查**：当任务 B 依赖 A，A 未完成时 B 不能进入 `progress`

---

## 5. API 设计

### 5.1 REST 端点（前缀 `/api`）

```
GET    /projects                      # 列出所有项目
POST   /projects                      # 创建项目
GET    /projects/{id}                 # 项目详情 + 进度汇总
PATCH  /projects/{id}                 # 更新项目
DELETE /projects/{id}                 # 删除项目（级联删除任务/费用）

GET    /projects/{id}/tasks           # 项目所有任务（含层级）
POST   /projects/{id}/tasks           # 创建任务
PATCH  /tasks/{id}                    # 更新任务（名称/日期/状态/进度）
DELETE /tasks/{id}                    # 删除任务
POST   /tasks/{id}/move               # 拖拽改日期（开始/结束）

POST   /tasks/{id}/dependencies       # 添加依赖
DELETE /dependencies/{id}             # 删除依赖

GET    /projects/{id}/costs           # 列出费用
POST   /costs                         # 创建费用
PATCH  /costs/{id}                    # 更新
DELETE /costs/{id}                    # 删除
GET    /stats/costs                   # 费用统计聚合（按项目/类别/月份）

POST   /attachments                   # 上传附件（multipart）
GET    /attachments/{id}              # 下载
DELETE /attachments/{id}              # 删除

GET    /inbox                         # 收件箱（按 kind 筛选）
POST   /inbox                         # 快速添加
PATCH  /inbox/{id}                    # 更新 / 转正 / 归档
POST   /inbox/{id}/promote            # 点子转正为任务

GET    /search?q=                     # 全局搜索（项目/任务/费用/点子）
GET    /search/filter?status=&project_id=&date_from=&date_to=

POST   /backup/export                 # 导出 JSON 备份（含附件 zip）
POST   /backup/import                 # 导入 JSON 备份（multipart）
GET    /backup/list                   # 列出历史备份

GET    /settings                      # 获取全局设置
PATCH  /settings                      # 更新全局设置
```

### 5.2 WebSocket `/ws/alerts`
- 连接时发送当前活跃提醒列表
- 后端定时器检测到新提醒时推送 `{type: "alert", task_id, title, alert_type}`

---

## 6. UI 设计

### 6.1 视觉风格
- **主题**：亮色（默认）/ 暗色（可切）。当前展示版为亮色，背景用蓝粉柔光渐变 + Apple 经典银白
- **质感**：Liquid Glass（`backdrop-filter: blur(30px) saturate(180%) + rgba(255,255,255,0.55)`）
- **字体**：`-apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC"`
- **圆角**：大圆角（14-22px），所有面板/按钮/输入框

### 6.2 状态色（统一）
| 状态 | 颜色 | 用途 |
|---|---|---|
| 未开始 | `#8e8e93` 灰渐变 | 任务条/徽章 |
| 进行中 | `#0071e3` 蓝渐变 | 任务条/徽章 |
| 延期 | `#ff9500` 橙渐变 + ⚠ 图标 | 任务条/徽章 |
| 已完成 | `#34c759` 绿渐变 + ✓ 图标 | 任务条/徽章 |
| 已取消 | `#af52de` 紫渐变 | 任务条/徽章 |
| 紧急 | `#ff3b30` 红 | 优先级标签 |
| 里程碑 | `#af52de` 紫菱形 | 关键节点 |

### 6.3 主布局（所有页面共享）
```
┌────────────────────────────────────────────────┐
│ ◉ │ [主内容区]                                │
│ │ ┌──────────────────────────────────────┐    │
│ 📊 │ │ 顶栏：Logo + 主导航 + 操作按钮       │    │
│ 📅 │ ├──────────────────────────────────────┤    │
│ ✅ │ │ 内容区（页面特定）                   │    │
│ 💰 │ │                                      │    │
│ 📥 │ │                                      │    │
│ ── │ │                                      │    │
│ ⚙ │ └──────────────────────────────────────┘    │
└────────────────────────────────────────────────┘
   ↑
 72px 玻璃侧栏
```

### 6.4 5 个核心页面

#### P1 · 总览仪表盘
- 顶部 KPI 行：项目数 / 已完成任务数 / 延期任务数 / 本月支出
- 月度费用趋势柱状图（可切月份）
- 项目卡片网格：每个项目显示进度条 + 状态 + 下个截止任务
- 即将到期列表（7 天内）

#### P2 · 甘特图日历（核心）
- 子栏：项目选择器 + 日期导航（◀ 今天 ▶ + 月份）+ 缩放（日/周/月/季）
- 左侧任务列表（280px）：层级缩进 + 状态徽章 + 进度百分比
- 右侧日历网格：31 天列 + 周末底色 + 今天高亮 + 今天线（蓝色光晕）
- 任务条：5 种状态渐变 + 内部进度填充 + 悬停浮起
- 依赖箭头：虚线 + 箭头（蓝色=正常 / 橙色=受延期影响）
- 里程碑：紫色菱形
- 交互：拖拽改日期（左右拖移动 / 边缘拉伸改时长）+ 点击进详情

#### P3 · 任务详情（点甘特条进入）
- 面包屑：项目 > 子项目 > 当前任务
- 标题 + 状态徽章组（状态/优先级/延期三色）
- 进度条 + 4 列信息（开始/截止/负责人/工时）
- 富文本描述区
- 依赖区：前置（蓝色边）+ 后继（橙色边）
- 附件区（图片/PDF/DOC 缩略 + 下载按钮）
- 右侧栏：子任务清单 + 标签 + 最近活动
- 底部操作：标记完成 / 切换状态 / 延期 / 编辑 / 删除

#### P4 · 费用记录
- 顶栏项目选择器（按项目筛）
- 3 张统计卡：本月支出 + 同比 + 笔数 + 平均
- 饼图：4 类费用占比（中心显示总额）
- 柱状图：周/月度趋势
- 列表：分类筛选 Tab + 添加按钮 + 卡片式记录（带附件徽章）

#### P5 · 临时收件箱
- 3 Tab：**🔥 插队任务(3)** / 💡 点子收件箱(7) / ✓ 已归档(12)
- 快速输入框（回车即添）
- 三段分级：**🔥 紧急（红边）/ ⚡ 高优（橙边）/ 📌 普通**
- 每条："转正" + "✓ 完成" 两个操作
- 转正：插队任务生成对应任务到指定项目；点子转正为正式任务

#### 系统管理弹窗（点 ⚙️ 弹出）
- 模态：720px 宽 + backdrop blur 40px
- 左侧 5 项子菜单：**备份与恢复 / 提醒设置 / 外观 / 数据维护 / 关于**
- **备份与恢复**：导出/导入卡片 + 最近备份历史（带恢复按钮）
- **提醒设置**：提前天数步进器 + 桌面通知开关 + 声音开关 + 静默时段
- **外观**：主题三选一（自动/亮/暗）+ 默认项目颜色 6 色圆点

---

## 7. 实施路线（3 阶段）

### P1 · 核心骨架（约 4-5 小时）
**目标**：能跑起来，能看到甘特图
- 项目初始化：FastAPI 骨架、SQLite + SQLAlchemy、Vite + Vue 3 + Tailwind
- 数据模型：`projects` / `tasks`（含 parent_id 多层级） / `task_dependencies`
- API：项目的 CRUD + 任务 CRUD + 依赖管理
- 前端 4 屏：总览仪表盘（基础版） + 甘特图（含 frappe-gantt 集成） + 任务详情 + 项目侧栏导航
- 启动脚本 `启动.bat` + `start.py`
- **验收**：能创建项目、创建多层级任务、拖拽改日期、看依赖箭头、点击进详情

### P2 · 费用 + 附件 + 备份（约 3-4 小时）
**目标**：能记账、能上传附件、能备份
- 数据模型：`costs` / `attachments` / `inbox_items`
- API：费用 CRUD + 附件上传/下载 + 备份导出/导入
- 前端 1 屏：费用记录（统计 + 饼图 + 柱图 + 列表）
- 系统管理弹窗基础版：备份区
- **验收**：能记费用、看分类饼图和月度柱图、上传发票照片、一键导出 JSON 备份并恢复

### P3 · 收件箱 + 提醒 + 搜索 + 视觉打磨（约 3-4 小时）
**目标**：临时任务系统化，提醒能用，整体漂亮
- API：收件箱 CRUD + 转正 + 全局搜索 + 全局设置
- 前端 2 屏：临时收件箱（含插队 vs 点子） + 系统管理弹窗完整版（含设置项）
- APScheduler 后台：每 60 秒扫描到期任务 / 提前预警 / 延期警告
- WebSocket `/ws/alerts`：实时推送提醒
- 浏览器原生 Notification 集成（首次访问请求权限）
- 全局搜索框（顶栏 🔍）+ 多条件筛选
- 暗色模式实现（CSS 变量切换）
- 视觉打磨：所有面板 Liquid Glass、动画、过渡
- **验收**：能快速记点子和插队任务、到期能收到浏览器通知、全局搜索能找到东西、明暗切换顺滑

---

## 8. 风险与备选

| 风险 | 影响 | 备选方案 |
|---|---|---|
| frappe-gantt 不支持拖拽改日期 | P1 阻塞 | 改用 dhtmlx-gantt（更重但功能全）或自研 SVG 甘特图 |
| WebSocket 在某些浏览器被防火墙拦 | P3 提醒延迟 | 后备：前端每 60 秒轮询 `/api/alerts` |
| 附件上传体积过大 | 备份文件膨胀 | 备份时跳过超过 10MB 的附件，提示用户 |
| SQLite 单文件并发写入慢 | 多任务同时编辑卡 | 启用 WAL 模式 + busy_timeout 5000ms |
| Notification API 用户拒绝授权 | 收不到桌面通知 | 退化为页面顶部红点 + 铃声（不依赖权限） |
| Liquid Glass 性能差（旧设备） | 滚动掉帧 | 检测设备能力，自动降级为 `blur(10px)` 或纯色 |

---

## 9. 验收标准

### P1 完成后
- [ ] 双击 `启动.bat` 能自动打开浏览器到 localhost:5173
- [ ] 能创建至少 3 个项目
- [ ] 在项目中能创建多层嵌套任务
- [ ] 甘特图能展示任务条，5 种状态颜色正确
- [ ] 能拖拽任务条改日期
- [ ] 任务之间能添加依赖，箭头正确显示
- [ ] 点击任务条能进入详情页

### P2 完成后
- [ ] 能记录费用，4 个类别
- [ ] 费用统计饼图和柱图数据正确
- [ ] 能上传发票图片到费用记录
- [ ] 能导出备份文件（zip 格式，内含 data.json + attachments/ 目录）
- [ ] 清空数据库后能从备份文件完全恢复（含附件）

### P3 完成后
- [ ] 能快速添加点子和插队任务
- [ ] 插队任务到期时浏览器弹出桌面通知
- [ ] 顶栏搜索能搜到项目/任务/费用/点子
- [ ] 主题能切换亮/暗，刷新后保持
- [ ] 系统管理弹窗中所有设置项可调并持久化

---

## 10. 仓库约定

```
.
├── backend/                  # FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── models/           # SQLAlchemy
│   │   ├── schemas/          # Pydantic
│   │   ├── api/              # REST 路由
│   │   ├── services/         # 业务逻辑
│   │   └── scheduler.py      # APScheduler
│   ├── alembic/              # 迁移
│   └── pyproject.toml
├── frontend/                 # Vue 3
│   ├── src/
│   │   ├── views/            # 5 个页面
│   │   ├── components/       # Liquid Glass 组件
│   │   ├── stores/           # Pinia
│   │   ├── router.ts
│   │   └── main.ts
│   ├── package.json
│   └── vite.config.ts
├── data/                     # 运行时数据（gitignore）
├── 启动.bat                  # 桌面图标入口
├── start.py                  # 一键启动
└── docs/superpowers/specs/   # 设计文档
```

`.gitignore` 必须包含：`data/`、`.superpowers/`、`node_modules/`、`__pycache__/`、`*.pyc`、`.venv/`

---

## 11. 备份文件格式

导出文件名为 `pm-backup-{YYYYMMDD}-{HHMMSS}.zip`，结构如下：

```
pm-backup-20260817-143200.zip
├── manifest.json           # 版本号、导出时间、数据条数统计
├── data.json               # 所有表数据（projects / tasks / deps / costs / inbox / settings）
└── attachments/
    ├── {uuid1}.jpg         # 附件原文件（按 ID 命名）
    ├── {uuid2}.pdf
    └── ...
```

导入时校验 `manifest.json` 版本兼容性，确认后事务性写入数据库，附件复制到 `data/attachments/`。若已有同名 UUID 附件则跳过（避免重复占用空间）。

---

## 12. 变更日志

- **2026-08-17**：初稿。所有需求通过 brainstorming 确认，UI 通过 5 屏高保真 mockup 确认（保存在 `.superpowers/brainstorm/session-001/content/`）。等待用户最终审阅。