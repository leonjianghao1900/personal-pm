# Task and Cost Name Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add direct task-name editing and a dedicated required, editable name for every cost while preserving existing databases and version 1 backups.

**Architecture:** Add the cost field through an idempotent startup migration, expose it through the existing FastAPI/SQLAlchemy layers, and upgrade backup exports to version 2 with explicit version 1 normalization. A focused Vue `EditableName` component provides identical inline editing behavior in the task detail and cost table.

**Tech Stack:** Python 3.13, FastAPI, Pydantic 2, SQLAlchemy 2, SQLite, pytest, Vue 3 Composition API, TypeScript, Axios, Tailwind CSS, Vite.

---

## File Map

- Create `backend/scripts/migrate_add_cost_name.py`: idempotently add and backfill `costs.name` for existing SQLite databases.
- Create `backend/tests/test_migrate_add_cost_name.py`: verify description/category backfill, truncation, and idempotency.
- Modify `backend/app/main.py`: run the new migration during startup.
- Modify `backend/app/models/cost.py`: declare the required cost name column.
- Modify `backend/app/schemas/cost.py`: validate cost names on create/update/read.
- Modify `backend/app/schemas/task.py`: apply create-equivalent validation to task rename.
- Modify `backend/tests/test_costs.py`: make fixtures name-aware and cover create/update validation.
- Modify `backend/tests/test_tasks.py`: cover valid and invalid task renames.
- Modify `backend/app/services/backup_service.py`: export version 2 and normalize accepted version 1 cost rows before strict validation.
- Modify `backend/tests/test_backup.py`: cover v2 round trips, v1 compatibility, and non-destructive invalid-name rejection.
- Create `frontend/src/components/EditableName.vue`: own inline edit, keyboard, focus, validation, and pending state.
- Modify `frontend/src/views/TaskDetailView.vue`: use inline editing for the task heading.
- Modify `frontend/src/api/types.ts`: add `Cost.name`.
- Modify `frontend/src/api/client.ts`: add explicit cost create/update payload types.
- Modify `frontend/src/views/CostsView.vue`: collect, display, and directly edit cost names.

### Task 1: Existing Database Migration

**Files:**
- Create: `backend/scripts/migrate_add_cost_name.py`
- Create: `backend/tests/test_migrate_add_cost_name.py`
- Modify: `backend/app/main.py:22-27`
- Modify: `backend/app/models/cost.py:19-22`

- [ ] **Step 1: Write failing migration tests**

Create a temporary legacy `costs` table with three rows and assert that migration uses a trimmed description first, falls back to category, truncates to 200 characters, and can run twice:

```python
from sqlalchemy import create_engine, inspect, text

from scripts.migrate_add_cost_name import migrate


def test_migrate_adds_and_backfills_cost_name(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE costs ("
            "id INTEGER PRIMARY KEY, category VARCHAR(20) NOT NULL, "
            "description VARCHAR)"
        ))
        conn.execute(text(
            "INSERT INTO costs (id, category, description) VALUES "
            "(1, '材料', '  购买瓷砖  '), (2, '人工', '   '), "
            "(3, '差旅', :long_description)"
        ), {"long_description": "x" * 250})

    migrate(engine)
    migrate(engine)

    assert "name" in {c["name"] for c in inspect(engine).get_columns("costs")}
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, name FROM costs ORDER BY id")).all()
    assert rows == [(1, "购买瓷砖"), (2, "人工"), (3, "x" * 200)]
```

- [ ] **Step 2: Run the migration test and verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_migrate_add_cost_name.py -q`

Expected: FAIL because `scripts.migrate_add_cost_name` does not exist.

- [ ] **Step 3: Implement the migration and model column**

Implement `migrate(engine)` with `inspect(engine).has_table("costs")`, column inspection, and these operations inside `engine.begin()`:

```python
if "name" not in columns:
    conn.execute(text(
        "ALTER TABLE costs ADD COLUMN name VARCHAR(200) NOT NULL DEFAULT ''"
    ))
conn.execute(text(
    "UPDATE costs SET name = substr("
    "CASE WHEN description IS NOT NULL AND trim(description) <> '' "
    "THEN trim(description) ELSE category END, 1, 200) "
    "WHERE trim(name) = ''"
))
```

Declare the fresh-database model field before `category`:

```python
name: Mapped[str] = mapped_column(String(200), nullable=False)
```

Register it after the existing startup migrations:

```python
from scripts.migrate_add_cost_name import migrate as add_cost_name
add_cost_name(engine)
```

- [ ] **Step 4: Run migration tests and the current backend suite**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_migrate_add_cost_name.py -q`

Expected: `1 passed`.

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`

Expected: existing cost tests fail because API-created costs do not yet provide the new required name; no migration test fails.

- [ ] **Step 5: Commit the migration**

```powershell
git add backend/scripts/migrate_add_cost_name.py backend/tests/test_migrate_add_cost_name.py backend/app/main.py backend/app/models/cost.py
git commit -m "feat: migrate existing costs to required names"
```

### Task 2: Cost and Task Name API Validation

**Files:**
- Modify: `backend/app/schemas/cost.py:6-31`
- Modify: `backend/app/schemas/task.py:23-33`
- Modify: `backend/tests/test_costs.py`
- Modify: `backend/tests/test_tasks.py`
- Modify: `backend/tests/test_backup.py` cost creation payloads only

- [ ] **Step 1: Write failing API tests and update test setup payloads**

Change `_mk_cost` so unrelated cost tests create valid named costs:

```python
def _mk_cost(client, pid, category="material", amount=100.0,
             spent_at="2026-08-01", name="测试费用", **kw):
    payload = {
        "name": name, "category": category, "amount": amount,
        "spent_at": spent_at, **kw,
    }
    r = client.post("/api/costs", json={**payload, "project_id": pid})
    assert r.status_code == 201, r.text
    return r.json()
```

Add `"name": "测试费用"` to direct valid cost creation payloads throughout `test_costs.py` and `test_backup.py`, then add:

```python
def test_create_cost_requires_name(client):
    pid = _mk_project(client)
    r = client.post("/api/costs", json={
        "project_id": pid, "category": "other", "amount": 10,
        "spent_at": "2026-08-01",
    })
    assert r.status_code == 422


def test_update_cost_name(client):
    pid = _mk_project(client)
    cost = _mk_cost(client, pid, name="旧名称")
    r = client.patch(f"/api/costs/{cost['id']}", json={"name": "新名称"})
    assert r.status_code == 200
    assert r.json()["name"] == "新名称"


def test_update_cost_rejects_blank_name(client):
    pid = _mk_project(client)
    cost = _mk_cost(client, pid)
    assert client.patch(f"/api/costs/{cost['id']}", json={"name": ""}).status_code == 422
    assert client.patch(f"/api/costs/{cost['id']}", json={"name": "   "}).status_code == 422
    assert client.patch(f"/api/costs/{cost['id']}", json={"name": None}).status_code == 422
```

In `test_tasks.py`, add:

```python
def test_update_task_name_validation(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    task = client.post(f"/api/projects/{pid}/tasks", json={"name": "旧名称"}).json()
    renamed = client.patch(f"/api/tasks/{task['id']}", json={"name": "新名称"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "新名称"
    assert client.patch(f"/api/tasks/{task['id']}", json={"name": ""}).status_code == 422
    assert client.patch(f"/api/tasks/{task['id']}", json={"name": "   "}).status_code == 422
    assert client.patch(f"/api/tasks/{task['id']}", json={"name": None}).status_code == 422
    assert client.patch(
        f"/api/tasks/{task['id']}", json={"name": "x" * 201}
    ).status_code == 422
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_costs.py backend/tests/test_tasks.py -q`

Expected: new cost-name response/validation tests and task update validation fail.

- [ ] **Step 3: Implement schema validation**

Import `field_validator`. Add the field and explicit whitespace/null validation to the shared cost schema and update schema:

```python
class CostBase(BaseModel):
    name: str = Field(max_length=200)
    category: str = Field("other", max_length=20)
    # existing fields remain unchanged

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("费用名称不能为空")
        return value


class CostUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    # existing fields remain unchanged

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("费用名称不能为空")
        return value.strip()
```

Strengthen task updates with the same supplied-value rule:

```python
name: str | None = Field(default=None, max_length=200)

@field_validator("name")
@classmethod
def validate_name(cls, value: str | None) -> str:
    if value is None or not value.strip():
        raise ValueError("任务名称不能为空")
    return value.strip()
```

The existing generic service update loops already persist both names, so no service changes are needed.

- [ ] **Step 4: Run focused and full backend tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_costs.py backend/tests/test_tasks.py -q`

Expected: all focused tests pass.

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`

Expected: backup version assertions may remain failing until Task 3; all cost/task API tests pass.

- [ ] **Step 5: Commit the API contract**

```powershell
git add backend/app/schemas/cost.py backend/app/schemas/task.py backend/tests/test_costs.py backend/tests/test_tasks.py backend/tests/test_backup.py
git commit -m "feat: expose validated task and cost names"
```

### Task 3: Version 2 Backup and Version 1 Compatibility

**Files:**
- Modify: `backend/app/services/backup_service.py:17-89`
- Modify: `backend/tests/test_backup.py`

- [ ] **Step 1: Write failing backup compatibility tests**

Change the empty-backup assertion to `version == 2` and assert exported costs contain their name. Add these exact local helpers before the restore tests:

```python
def make_complete_backup_payload(version=2):
    return {
        "version": version,
        "exported_at": "2026-08-01T00:00:00Z",
        "projects": [],
        "tasks": [],
        "task_dependencies": [],
        "costs": [],
        "cost_categories": [],
        "inbox_items": [],
    }


def complete_project_row(id, name):
    return {
        "id": id,
        "name": name,
        "color": "#0071e3",
        "description": None,
        "start_date": None,
        "end_date": None,
        "status": "active",
        "created_at": "2026-08-01T00:00:00",
        "updated_at": "2026-08-01T00:00:00",
    }
```

Then add a version 1 restore containing complete legacy cost fields except `name`:

```python
def test_restore_version_1_derives_cost_name(client, db_session):
    payload = make_complete_backup_payload(version=1)
    payload["projects"] = [complete_project_row(id=1, name="P")]
    payload["costs"] = [{
        "id": 1,
        "project_id": 1,
        "task_id": None,
        "category": "材料",
        "amount": 12.5,
        "description": "  购买瓷砖  ",
        "spent_at": "2026-08-01",
        "created_at": "2026-08-01T00:00:00",
    }]
    files = {"file": ("backup.json", json.dumps(payload), "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 200, r.text
    restored = client.get("/api/projects/1/costs").json()
    assert restored[0]["name"] == "购买瓷砖"
```

Add a second v1 row with `description=None` and assert its name falls back to category.

Add a non-destructive v2 validation test:

```python
def test_restore_version_2_blank_cost_name_preserves_data(client, db_session):
    kept_id = client.post("/api/projects", json={"name": "KEEP"}).json()["id"]
    payload = make_complete_backup_payload(version=2)
    payload["costs"] = [{"name": ""}]
    files = {"file": ("backup.json", json.dumps(payload), "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 400
    assert client.get(f"/api/projects/{kept_id}").json()["name"] == "KEEP"
```

- [ ] **Step 2: Run backup tests and verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_backup.py -q`

Expected: FAIL because exports still report version 1, v1 rows lack the new model field, and v2 is rejected.

- [ ] **Step 3: Implement normalization before destructive work**

Set:

```python
EXPORT_VERSION = 2
SUPPORTED_VERSIONS = (1, 2)
```

Change version validation to accept only supported versions. Add a normalization function that runs after envelope validation and before `_prepare_rows`:

```python
def _normalize_payload(payload: dict) -> dict:
    normalized = deepcopy(payload)
    version = normalized["version"]
    for index, row in enumerate(normalized["costs"]):
        if version == 1:
            description = row.get("description")
            category = row.get("category")
            source = description.strip() if isinstance(description, str) else ""
            if not source:
                source = category.strip() if isinstance(category, str) else ""
            row["name"] = source[:200]
        name = row.get("name")
        if not isinstance(name, str) or not name.strip() or len(name) > 200:
            raise ValueError(f"备份表 costs 第 {index + 1} 条记录名称无效")
        row["name"] = name.strip()
    normalized["version"] = EXPORT_VERSION
    return normalized
```

Import `deepcopy` from `copy`. In `restore_data`, call `_validate_payload(payload)`, then `normalized = _normalize_payload(payload)`, then `_prepare_rows(normalized)`. Do not mutate the caller payload and do not delete rows before these calls finish.

- [ ] **Step 4: Run backup and full backend tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_backup.py -q`

Expected: all backup tests pass, including v1 compatibility and v2 non-destructive rejection.

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`

Expected: all backend tests pass.

- [ ] **Step 5: Commit backup compatibility**

```powershell
git add backend/app/services/backup_service.py backend/tests/test_backup.py
git commit -m "feat: preserve cost names in version 2 backups"
```

### Task 4: Shared Inline Name Editor

**Files:**
- Create: `frontend/src/components/EditableName.vue`

- [ ] **Step 1: Define the component contract**

Create a component with these typed props:

```ts
const props = withDefaults(defineProps<{
  modelValue: string
  textClass?: string
  inputClass?: string
  save: (name: string) => Promise<void>
}>(), {
  textClass: '',
  inputClass: ''
})
```

Its template must expose a semantic button while idle and an input while editing. Add `aria-label="修改名称"` to the button and input.

- [ ] **Step 2: Implement edit state and keyboard behavior**

Use `editing`, `draft`, `saving`, and `input` refs. Implement these exact state transitions:

```ts
function start() {
  draft.value = props.modelValue
  editing.value = true
  nextTick(() => input.value?.focus())
}

function cancel() {
  draft.value = props.modelValue
  editing.value = false
}

async function commit() {
  if (saving.value) return
  const name = draft.value.trim()
  if (!name) return
  if (name === props.modelValue) {
    editing.value = false
    return
  }
  saving.value = true
  try {
    await props.save(name)
    editing.value = false
  } catch {
    await nextTick()
    input.value?.focus()
  } finally {
    saving.value = false
  }
}
```

Bind Enter and blur to `commit`, Escape to `cancel`, `maxlength="200"`, and `disabled` to `saving`. Prevent an Escape-triggered blur from saving by setting editing false before blur and returning from `commit` when not editing.

- [ ] **Step 3: Add focused visual states**

Use the existing flat button/input language: transparent idle button with subtle rounded hover background and a white/70 input with `border-black/10` and `focus:border-apple-blue`. Apply `textClass` and `inputClass` so task heading and table row can retain their typography.

- [ ] **Step 4: Run the compiler/build check**

Run: `npm.cmd run build` from `frontend`.

Expected: build passes and the new standalone component has no TypeScript or template errors.

- [ ] **Step 5: Commit the component**

```powershell
git add frontend/src/components/EditableName.vue
git commit -m "feat: add reusable inline name editor"
```

### Task 5: Task Heading Editing

**Files:**
- Modify: `frontend/src/views/TaskDetailView.vue:21,108-170`

- [ ] **Step 1: Wire the component into the task heading**

Import `EditableName` and replace the read-only heading with:

```vue
<EditableName
  :model-value="task.name"
  text-class="text-3xl font-bold tracking-tight"
  input-class="text-3xl font-bold tracking-tight"
  :save="saveTaskName"
  class="mb-1"
/>
```

- [ ] **Step 2: Add the parent save callback**

Keep API ownership in the view:

```ts
async function saveTaskName(name: string) {
  if (!task.value) return
  task.value = await tasksStore.update(task.value.id, { name })
}
```

- [ ] **Step 3: Build and manually verify task interactions**

Run: `npm.cmd run build` from `frontend`.

Expected: build passes.

With current dev servers running, open a task detail page and verify click focuses the title, Enter saves and updates the title, Escape restores the old title, blur saves, and blank text remains in edit mode without sending a request.

- [ ] **Step 4: Verify persistence**

Reload the task page after a successful rename.

Expected: the renamed value remains and is also visible in the Gantt task list.

- [ ] **Step 5: Commit task editing**

```powershell
git add frontend/src/views/TaskDetailView.vue
git commit -m "feat: edit task names from task details"
```

### Task 6: Cost Creation, Display, and Name Editing

**Files:**
- Modify: `frontend/src/api/types.ts:45-54`
- Modify: `frontend/src/api/client.ts:59-70`
- Modify: `frontend/src/views/CostsView.vue:97-169,175-337`

- [ ] **Step 1: Strengthen frontend cost types**

Add `name: string` to `Cost`. Replace the partial create input with explicit contracts:

```ts
export type CostCreateInput =
  Pick<Cost, 'name' | 'category' | 'amount' | 'spent_at'> &
  Partial<Pick<Cost, 'description' | 'task_id'>>

export type CostUpdateInput = Partial<
  Pick<Cost, 'name' | 'category' | 'amount' | 'description' | 'spent_at' | 'task_id'>
>
```

Use `CostCreateInput` for `costsApi.create` and `CostUpdateInput` for `costsApi.update`.

- [ ] **Step 2: Add the required name to cost creation**

Add `name: string` to the form type and initialize it to `''` in both initial and `openCreate` state. Add this field before amount/date:

```vue
<label class="block text-xs text-gray-500 mb-1">名称</label>
<input v-model="form.name" maxlength="200" placeholder="如：客厅瓷砖"
       class="w-full px-3 py-2 rounded-lg border border-black/10 mb-3 bg-white/70" />
```

Trim it in the create payload and require it in `submitForm`:

```ts
const name = form.value.name.trim()
if (!name || !form.value.project_id || !form.value.amount || form.value.amount <= 0) return
await costsApi.create(form.value.project_id, { ...form.value, name })
```

Disable the save button with `:disabled="!form.name.trim() || form.amount <= 0"` and existing disabled visual classes.

- [ ] **Step 3: Display and edit names in the table**

Import `EditableName`, add a `名称` header before `类别`, and render:

```vue
<td class="py-2.5 pr-3 min-w-36">
  <EditableName
    :model-value="c.name"
    text-class="font-medium"
    :save="name => saveCostName(c.id, name)"
  />
</td>
```

Keep the existing `说明` column. Update a single local row from the PATCH response:

```ts
async function saveCostName(id: number, name: string) {
  const saved = await costsApi.update(id, { name })
  const index = costs.value.findIndex(cost => cost.id === id)
  if (index !== -1) costs.value[index] = saved
}
```

- [ ] **Step 4: Build and manually verify cost behavior**

Run: `npm.cmd run build` from `frontend`.

Expected: build passes.

Open Costs and verify a cost cannot be created without a name, a valid named cost appears with separate name/description columns, Enter and blur persist edits, Escape cancels, and a page reload preserves the edited name.

- [ ] **Step 5: Commit cost UI changes**

```powershell
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/views/CostsView.vue
git commit -m "feat: create and edit named costs"
```

### Task 7: Final Regression and Live Upgrade Verification

**Files:**
- Verify all files changed in Tasks 1-6.

- [ ] **Step 1: Run the complete backend suite**

Run from the repository root:

`backend\.venv\Scripts\python.exe -m pytest backend/tests -q`

Expected: all tests pass with only existing deprecation warnings.

- [ ] **Step 2: Run the production frontend build**

Run: `npm.cmd run build` from `frontend`.

Expected: `vue-tsc` and Vite complete successfully; only existing dependency deprecation warnings may remain.

- [ ] **Step 3: Verify the real database migration**

Restart the backend so the new startup migration runs. Query the real database and assert `costs.name` exists, no row has a blank name, and description/category-derived names match the agreed rule.

Expected SQL checks:

```sql
PRAGMA table_info(costs);
SELECT COUNT(*) FROM costs WHERE name IS NULL OR trim(name) = '';
SELECT id, name, description, category FROM costs ORDER BY id;
```

The blank-name count must be `0`.

- [ ] **Step 4: Verify live version 2 and legacy version 1 restoration**

Download a live backup and assert `version` is `2` and every cost has a non-empty `name`. Restore it unchanged and verify counts. Then restore a temporary version 1 copy with each cost `name` removed and verify names are re-derived without losing projects, tasks, dependencies, categories, costs, or inbox items.

- [ ] **Step 5: Review the diff and commit any verification-only fixes**

Run:

```powershell
git status --short
git diff --check
git diff HEAD~6 --stat
```

Expected: no whitespace errors and no unrelated files. If verification required a correction, stage only the relevant files and create a new focused commit; do not amend earlier commits.
