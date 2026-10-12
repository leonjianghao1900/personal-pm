import json
from copy import deepcopy

import pytest

from app.services import backup_service


def _project_row(project_id=1, name="P"):
    return {
        "id": project_id,
        "name": name,
        "color": "#0071e3",
        "description": None,
        "start_date": None,
        "end_date": None,
        "status": "active",
        "created_at": "2026-08-01T00:00:00",
        "updated_at": "2026-08-01T00:00:00",
    }


def _cost_row(cost_id=1, project_id=1, **overrides):
    row = {
        "id": cost_id,
        "project_id": project_id,
        "task_id": None,
        "name": "Cost",
        "category": "other",
        "amount": 10,
        "description": None,
        "spent_at": "2026-08-01",
        "created_at": "2026-08-01T00:00:00",
    }
    row.update(overrides)
    return row


def _complete_payload(version=2, *, projects=None, costs=None, attachments=None):
    payload = {
        "version": version,
        "exported_at": "2026-08-01T00:00:00Z",
        "projects": [] if projects is None else projects,
        "tasks": [],
        "task_dependencies": [],
        "costs": [] if costs is None else costs,
        "cost_categories": [],
        "inbox_items": [],
    }
    if version >= 3:
        payload["attachments"] = [] if attachments is None else attachments
    return payload


def _restore(client, payload):
    files = {"file": ("backup.json", json.dumps(payload), "application/json")}
    return client.post("/api/admin/restore", files=files)


def test_backup_empty_db(client, db_session):
    r = client.get("/api/admin/backup")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == 3
    assert data["projects"] == []
    assert data["tasks"] == []
    assert data["costs"] == []
    assert data["cost_categories"] == []
    assert data["task_dependencies"] == []
    assert data["inbox_items"] == []
    assert data["attachments"] == []
    assert "exported_at" in data


def test_backup_returns_all_tables(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    predecessor_id = client.post(
        f"/api/projects/{pid}/tasks", json={"name": "A"}
    ).json()["id"]
    successor_id = client.post(
        f"/api/projects/{pid}/tasks", json={"name": "B"}
    ).json()["id"]
    client.post(
        f"/api/tasks/{successor_id}/dependencies",
        json={"predecessor_id": predecessor_id},
    )
    client.post("/api/cost-categories", json={"name": "x", "color": "#abcdef"})
    client.post(
        "/api/costs",
        json={
            "project_id": pid,
            "name": "Cost",
            "category": "x",
            "amount": 10,
            "spent_at": "2026-08-01",
        },
    )
    client.post("/api/inbox", json={"kind": "idea", "title": "I"})
    data = client.get("/api/admin/backup").json()
    assert len(data["projects"]) == 1
    assert data["projects"][0]["name"] == "P"
    assert len(data["tasks"]) == 2
    assert len(data["task_dependencies"]) == 1
    assert len(data["costs"]) == 1
    assert data["costs"][0]["name"] == "Cost"
    assert len(data["cost_categories"]) == 1
    assert len(data["inbox_items"]) == 1


def test_restore_overwrites_existing(client, db_session):
    client.post("/api/projects", json={"name": "OLD"})
    payload = {
        "version": 1,
        "exported_at": "2026-08-01T00:00:00Z",
        "projects": [
            {
                "id": 1,
                "name": "NEW",
                "color": "#0071e3",
                "description": None,
                "start_date": None,
                "end_date": None,
                "status": "active",
                "created_at": "2026-08-01T00:00:00",
                "updated_at": "2026-08-01T00:00:00",
            }
        ],
        "tasks": [],
        "task_dependencies": [],
        "costs": [],
        "cost_categories": [],
        "inbox_items": [],
    }
    files = {"file": ("backup.json", json.dumps(payload), "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 200, r.text
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


@pytest.mark.parametrize("version", [0, 4, 99, True, "2", None])
def test_restore_wrong_version_400(client, db_session, version):
    payload = {
        "version": version,
        "projects": [],
        "tasks": [],
        "task_dependencies": [],
        "costs": [],
        "cost_categories": [],
        "inbox_items": [],
    }
    files = {"file": ("backup.json", json.dumps(payload), "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 400
    assert "版本" in r.json()["detail"]


def test_backup_restore_round_trip_preserves_relationships(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    predecessor_id = client.post(
        f"/api/projects/{pid}/tasks", json={"name": "A"}
    ).json()["id"]
    successor_id = client.post(
        f"/api/projects/{pid}/tasks", json={"name": "B"}
    ).json()["id"]
    client.post(
        f"/api/tasks/{successor_id}/dependencies",
        json={"predecessor_id": predecessor_id},
    )
    client.post("/api/cost-categories", json={"name": "x", "color": "#abcdef"})
    client.post(
        "/api/costs",
        json={
            "project_id": pid,
            "name": "Cost",
            "task_id": predecessor_id,
            "category": "x",
            "amount": 5,
            "spent_at": "2026-08-01",
        },
    )
    backup = client.get("/api/admin/backup").json()
    client.post("/api/projects", json={"name": "EXTRA"})
    files = {"file": ("backup.json", json.dumps(backup), "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 200, r.text
    assert {p["name"] for p in client.get("/api/projects").json()} == {"P"}
    restored_costs = client.get(f"/api/projects/{pid}/costs").json()
    assert restored_costs[0]["task_id"] == predecessor_id
    assert restored_costs[0]["name"] == "Cost"
    restored_backup = client.get("/api/admin/backup").json()
    assert len(restored_backup["task_dependencies"]) == 1
    dependency = restored_backup["task_dependencies"][0]
    assert dependency["predecessor_id"] == predecessor_id
    assert dependency["successor_id"] == successor_id


def test_restore_v1_complete_backup_preserves_all_tables_and_relationships(
    client, db_session
):
    payload = {
        "version": 1,
        "exported_at": "2026-08-01T00:00:00Z",
        "projects": [_project_row(project_id=11, name="Legacy project")],
        "tasks": [
            {
                "id": task_id,
                "project_id": 11,
                "parent_id": None,
                "name": name,
                "description": None,
                "status": "todo",
                "priority": "normal",
                "start_date": None,
                "end_date": None,
                "progress": 0,
                "sort_order": sort_order,
                "is_milestone": False,
                "created_at": "2026-08-01T00:00:00",
                "updated_at": "2026-08-01T00:00:00",
            }
            for task_id, name, sort_order in [(21, "First", 0), (22, "Second", 1)]
        ],
        "task_dependencies": [
            {
                "id": 31,
                "predecessor_id": 21,
                "successor_id": 22,
                "dep_type": "FS",
                "created_at": "2026-08-01T00:00:00",
            }
        ],
        "costs": [
            {
                "id": 41,
                "project_id": 11,
                "task_id": 21,
                "category": "travel",
                "amount": 25,
                "description": "  Train ticket  ",
                "spent_at": "2026-08-02",
                "created_at": "2026-08-02T00:00:00",
            }
        ],
        "cost_categories": [
            {
                "id": 51,
                "name": "travel",
                "color": "#abcdef",
                "is_builtin": False,
                "sort_order": 2,
            }
        ],
        "inbox_items": [
            {
                "id": 61,
                "kind": "idea",
                "title": "Legacy idea",
                "notes": "Keep this",
                "priority": "high",
                "due_at": None,
                "project_id": 11,
                "promoted_task_id": 22,
                "status": "active",
                "created_at": "2026-08-03T00:00:00",
                "completed_at": None,
            }
        ],
    }

    response = _restore(client, payload)

    assert response.status_code == 200, response.text
    assert response.json() == {
        "status": "ok",
        "counts": {
            "projects": 1,
            "cost_categories": 1,
            "tasks": 2,
            "task_dependencies": 1,
            "costs": 1,
            "inbox_items": 1,
        },
    }
    restored = client.get("/api/admin/backup").json()
    assert [project["id"] for project in restored["projects"]] == [11]
    assert [task["id"] for task in restored["tasks"]] == [21, 22]
    assert restored["task_dependencies"] == [
        {
            "id": 31,
            "predecessor_id": 21,
            "successor_id": 22,
            "dep_type": "FS",
            "created_at": "2026-08-01T00:00:00",
        }
    ]
    cost = restored["costs"][0]
    assert cost["id"] == 41
    assert cost["task_id"] == 21
    assert cost["name"] == "Train ticket"
    assert cost["category"] == "travel"
    category = restored["cost_categories"][0]
    assert (category["id"], category["name"]) == (51, "travel")
    inbox_item = restored["inbox_items"][0]
    assert (inbox_item["id"], inbox_item["title"]) == (61, "Legacy idea")
    assert inbox_item["project_id"] == 11
    assert inbox_item["promoted_task_id"] == 22


def test_restore_missing_table_400_preserves_data(client, db_session):
    client.post("/api/projects", json={"name": "KEEP"})
    payload = {
        "version": 1,
        "projects": [],
        "task_dependencies": [],
        "costs": [],
        "cost_categories": [],
        "inbox_items": [],
    }
    files = {"file": ("backup.json", json.dumps(payload), "application/json")}

    r = client.post("/api/admin/restore", files=files)

    assert r.status_code == 400
    projects = client.get("/api/projects").json()
    assert len(projects) == 1
    assert projects[0]["name"] == "KEEP"


def test_restore_rejects_orphan_fk_and_preserves_data(client, db_session):
    client.post("/api/projects", json={"name": "OLD"})
    payload = {
        "version": 1,
        "exported_at": "2026-08-01T00:00:00Z",
        "projects": [],
        "tasks": [
            {
                "id": 1,
                "project_id": 999,
                "parent_id": None,
                "name": "ORPHAN",
                "description": None,
                "status": "todo",
                "priority": "normal",
                "start_date": None,
                "end_date": None,
                "progress": 0,
                "sort_order": 0,
                "is_milestone": False,
                "created_at": "2026-08-01T00:00:00",
                "updated_at": "2026-08-01T00:00:00",
            }
        ],
        "task_dependencies": [],
        "costs": [],
        "cost_categories": [],
        "inbox_items": [],
    }
    files = {"file": ("backup.json", json.dumps(payload), "application/json")}

    r = client.post("/api/admin/restore", files=files)

    assert r.status_code == 400
    assert "无效关联" in r.json()["detail"]
    projects = client.get("/api/projects").json()
    assert len(projects) == 1
    assert projects[0]["name"] == "OLD"


def test_restore_invalid_utf8_400(client, db_session):
    files = {"file": ("backup.json", b"\x80", "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 400


def test_restore_missing_record_fields_400_preserves_data(client, db_session):
    client.post("/api/projects", json={"name": "OLD"})
    payload = {
        "version": 1, "exported_at": "2026-08-01T00:00:00Z",
        "projects": [{}], "tasks": [], "task_dependencies": [],
        "costs": [], "cost_categories": [], "inbox_items": [],
    }
    files = {"file": ("backup.json", json.dumps(payload), "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 400
    assert [p["name"] for p in client.get("/api/projects").json()] == ["OLD"]


def test_restore_forces_builtin_false(client, db_session):
    payload = {
        "version": 1,
        "exported_at": "2026-08-01T00:00:00Z",
        "projects": [],
        "tasks": [],
        "task_dependencies": [],
        "costs": [],
        "cost_categories": [{
            "id": 1,
            "name": "legacy",
            "color": "#0071e3",
            "is_builtin": True,
            "sort_order": 0,
        }],
        "inbox_items": [],
    }
    files = {"file": ("backup.json", json.dumps(payload), "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 200
    assert client.get("/api/cost-categories").json()[0]["is_builtin"] is False


def test_restore_utf16_json_400(client, db_session):
    payload = {
        "version": 1, "projects": [], "tasks": [], "task_dependencies": [],
        "costs": [], "cost_categories": [], "inbox_items": [],
    }
    raw = json.dumps(payload).encode("utf-16")
    files = {"file": ("backup.json", raw, "application/json")}
    r = client.post("/api/admin/restore", files=files)
    assert r.status_code == 400


def test_restore_v1_derives_cost_names_without_mutating_payload(db_session):
    description_name = "D" * 201
    costs = [
        _cost_row(cost_id=1, description=f"  {description_name}  "),
        _cost_row(cost_id=2, category="  travel  ", description="   "),
    ]
    for cost in costs:
        cost.pop("name")
    payload = _complete_payload(
        version=1,
        projects=[_project_row()],
        costs=costs,
    )
    original = deepcopy(payload)

    backup_service.restore_data(db_session, payload)

    assert payload == original
    restored = backup_service.export_data(db_session)["costs"]
    assert [cost["name"] for cost in restored] == ["D" * 200, "travel"]


def test_restore_v1_rejects_cost_without_name_source_and_preserves_data(
    client, db_session
):
    client.post("/api/projects", json={"name": "KEEP"})
    cost = _cost_row(category="   ", description=None)
    cost.pop("name")
    payload = _complete_payload(
        version=1,
        projects=[_project_row()],
        costs=[cost],
    )

    response = _restore(client, payload)

    assert response.status_code == 400
    assert [p["name"] for p in client.get("/api/projects").json()] == ["KEEP"]


@pytest.mark.parametrize("name", [None, "   ", 123, "x" * 201])
def test_restore_v2_rejects_invalid_cost_name_and_preserves_data(
    client, db_session, name
):
    client.post("/api/projects", json={"name": "KEEP"})
    cost = _cost_row()
    if name is not None:
        cost["name"] = name
    else:
        cost.pop("name")
    payload = _complete_payload(
        projects=[_project_row()],
        costs=[cost],
    )

    response = _restore(client, payload)

    assert response.status_code == 400
    assert [p["name"] for p in client.get("/api/projects").json()] == ["KEEP"]


def test_restore_v2_trims_cost_name(client, db_session):
    payload = _complete_payload(
        projects=[_project_row()],
        costs=[_cost_row(name="  Travel  ")],
    )

    response = _restore(client, payload)

    assert response.status_code == 200, response.text
    restored = client.get("/api/projects/1/costs").json()
    assert restored[0]["name"] == "Travel"
