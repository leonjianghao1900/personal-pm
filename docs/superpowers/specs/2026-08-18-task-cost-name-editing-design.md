# Task and Cost Name Editing Design

## Goal

Make task names and cost names directly editable, using the same clear save/cancel behavior across both screens. Costs gain a dedicated required name while retaining the existing optional description.

## Scope

- Add direct name editing to the task detail heading.
- Add a required `name` field to costs.
- Show and directly edit cost names in the cost table.
- Add the required name field to the create-cost form.
- Preserve existing cost data and compatibility with version 1 JSON backups.
- Do not add full task or cost edit panels and do not change unrelated fields.

## Interaction Design

Task and cost names use a shared lightweight inline editor:

- The displayed name is clickable and has a visible hover/focus treatment.
- Clicking switches the text to a focused input containing the current name.
- Enter or blur saves the trimmed value.
- Escape cancels and restores the previous value.
- An empty or whitespace-only name is not saved.
- An unchanged value exits edit mode without an API request.
- While a request is active, duplicate saves are prevented.
- On success, the returned entity immediately replaces the displayed data.
- On failure, the editor remains open and the existing API error handling displays the error.

The task detail page applies this behavior to its current `h1`. The costs table adds a `名称` column with the same behavior for each row. The existing `说明` column remains separate.

The create-cost form places a required `名称` input before the amount/date fields. Its save button is disabled, and submission is ignored, until the trimmed name is non-empty.

## Data Model and API

Add `Cost.name` as a non-null string with a maximum length of 200 characters.

- `CostCreate.name` is required with `min_length=1` and `max_length=200`.
- `CostUpdate.name` is optional for partial updates, but when supplied must satisfy the same length constraints.
- `CostRead` includes `name`.
- The existing cost update endpoint persists name-only updates.
- `TaskUpdate.name` gains the same `min_length=1`, `max_length=200` validation already used by `TaskCreate`.

The frontend `Cost` type, create payload, update payload, and local form state include `name`.

## Existing Database Migration

Startup runs an idempotent SQLite migration after table creation:

1. Inspect `costs` with `PRAGMA table_info`.
2. If `name` is absent, add it as a non-null string column with a temporary empty-string default compatible with SQLite `ALTER TABLE`.
3. Backfill every existing row.
4. Use the trimmed description when it is non-empty; otherwise use the category.
5. Truncate the derived value to 200 characters.

The migration is safe to run repeatedly and never overwrites a non-empty existing name.

Fresh databases receive the non-null column directly from SQLAlchemy metadata. Application-level schemas prevent newly created or updated costs from having blank names.

## Backup Compatibility

The exported backup version becomes version 2 because the cost row shape gains `name`.

- Version 2 restores require every cost row to contain `name`, consistent with the current complete-row validation.
- Version 1 backups remain accepted.
- Before destructive restore work, version 1 cost rows are normalized by deriving `name` from trimmed `description`, falling back to `category`, and truncating to 200 characters.
- After normalization, all existing type conversion, foreign-key validation, transaction, and rollback protections remain unchanged.
- New exports always include the stored cost name.

No other backup table or field changes.

## Components and Data Flow

`EditableName.vue` owns only editing state, keyboard handling, focus, basic trim/empty checks, and save-in-progress state. It accepts the current name and an async save callback. The parent remains responsible for API calls and replacing its entity with the returned value.

Task flow:

1. User clicks the task heading.
2. `EditableName` calls the parent save callback.
3. `TaskDetailView` calls the existing task store update with `{ name }`.
4. The returned task replaces the local task.

Cost flow:

1. User clicks a name in the cost table.
2. `EditableName` calls the row save callback.
3. `CostsView` calls `costsApi.update(id, { name })`.
4. The returned cost replaces that row in the local list without a full reload.

## Error Handling

- Backend validation returns 422 for blank or overlong names.
- Inline save failures preserve the draft and editing state so the user can retry or cancel.
- Migration and restore derive a non-empty fallback from category, which is already required.
- Restore normalization occurs before any deletes, preserving the existing all-or-nothing restore guarantee.

## Verification

Backend tests cover:

- Task rename accepts a valid name and rejects blank or overlong names.
- Cost create requires a valid name.
- Cost name-only update persists and returns the new name.
- Existing database migration derives names from description first and category second and is idempotent.
- Version 2 backup round trips cost names.
- Version 1 backup restoration derives names and preserves all relationships.
- Invalid version 2 cost names fail before destructive deletes.

Frontend verification covers:

- Type checking and production build.
- Task and cost inline editing by click, Enter, blur, and Escape.
- Cost creation cannot submit without a name.
- Successful edits update the visible task heading and cost row immediately.

The full backend test suite and a real backup/restore smoke test run after implementation.
