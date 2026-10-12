import pytest


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


def test_update_task_name(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    r = client.patch(f"/api/tasks/{tid}", json={"name": "  Renamed task  "})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed task"
    assert client.get(f"/api/tasks/{tid}").json()["name"] == "Renamed task"


@pytest.mark.parametrize("name", ["", "   ", None, "x" * 201])
def test_update_task_rejects_invalid_name(client, name):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    r = client.patch(f"/api/tasks/{tid}", json={"name": name})
    assert r.status_code == 422


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


def test_create_task_with_nonexistent_parent_409(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    r = client.post(f"/api/projects/{pid}/tasks", json={"name": "T", "parent_id": 99999})
    assert r.status_code == 409


def test_create_task_with_cross_project_parent_409(client):
    p1 = client.post("/api/projects", json={"name": "P1"}).json()["id"]
    p2 = client.post("/api/projects", json={"name": "P2"}).json()["id"]
    parent = client.post(f"/api/projects/{p1}/tasks", json={"name": "A"}).json()["id"]
    r = client.post(f"/api/projects/{p2}/tasks", json={"name": "B", "parent_id": parent})
    assert r.status_code == 409


def test_update_task_self_parent_409(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    r = client.patch(f"/api/tasks/{tid}", json={"parent_id": tid})
    assert r.status_code == 409


def test_update_task_cycle_409(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    b = client.post(f"/api/projects/{pid}/tasks", json={"name": "B", "parent_id": a}).json()["id"]
    r = client.patch(f"/api/tasks/{a}", json={"parent_id": b})
    assert r.status_code == 409


def test_update_task_to_root_ok(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    client.post(f"/api/projects/{pid}/tasks", json={"name": "B", "parent_id": a})
    r = client.patch(f"/api/tasks/{a}", json={"parent_id": None})
    assert r.status_code == 200
    assert r.json()["parent_id"] is None


def test_get_missing_task_404(client):
    r = client.get("/api/tasks/99999")
    assert r.status_code == 404


def test_create_task_missing_project_404(client):
    r = client.post("/api/projects/99999/tasks", json={"name": "T"})
    assert r.status_code == 404


def test_delete_task_cascades_children(client, db_session):
    from app.models import Task

    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    child = Task(project_id=pid, parent_id=a, name="kid")
    grand = Task(project_id=pid, parent_id=None, name="grand")
    db_session.add_all([child, grand])
    db_session.commit()
    db_session.refresh(child)
    db_session.refresh(grand)
    grand.parent_id = child.id
    db_session.commit()

    r = client.delete(f"/api/tasks/{a}")
    assert r.status_code == 204

    db_session.expire_all()
    assert db_session.get(Task, child.id) is None
    assert db_session.get(Task, grand.id) is None
