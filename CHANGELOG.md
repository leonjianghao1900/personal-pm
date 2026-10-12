# 更新日志

## v0.2.0 (2026-09-04)

### 新增
- **附件功能**：任务、费用记录、临时收件箱均可上传附件
  - 单文件上限 20 MB
  - 任务上限 10 个，费用 5 个，收件箱 5 个
  - 文件存到 `exe_data/attachments/<类型>/<ID>/<UUID>.<ext>`
  - 数据库只存元数据（避免 SQLite 膨胀）
  - 删除实体时附件自动级联清理
- **完整备份 (ZIP)**：备份脚本升级到 v3
  - `GET /api/admin/backup/full` 返回 zip（JSON + 附件文件）
  - `POST /api/admin/restore/full` 接受 zip 还原
- **InboxView 支持编辑**：每条 inbox 可点击"编辑"按钮，原先只能创建/删除
- **费用明细新增"附件"列**：直观显示每笔费用有几个附件，点击图标直接下载
- **安装器**：Inno Setup 6 单文件安装包，自动创建桌面/开始菜单快捷方式，无 UAC

### 修复
- 费用 `project_id` 修改后未生效（4 文件协同修复）
- 趋势图按日/按周显示时溢出，新增横向滚动条
- **附件下载路由 422 bug**：`/{aid}/download` 被 `/{entity_type}/{entity_id}` 遮蔽，路由重排序
- exe 数据目录从 `dist/data/` 改为项目根 `exe_data/`，与 dev server 数据分离

### 测试
- 后端 136 测试通过（4 个 pre-existing overview 测试失败与本次无关）
- 新增 `tests/test_attachments.py`，8 个附件相关测试

### 改动文件
- 后端：6 个新文件、12 个修改
- 前端：1 个新组件、4 个 view 修改
- 构建：`build.py` 加固（默认不再 rmtree `dist/`）
- 安装：`installer.iss` + 版本号 `PersonalPM-Setup-0.2.0.exe`

---

## v0.1.0 (历史版本)

首个可用版本。项目管理、任务（含依赖关系）、甘特图、费用记录与统计、临时收件箱、JSON 备份/恢复。
