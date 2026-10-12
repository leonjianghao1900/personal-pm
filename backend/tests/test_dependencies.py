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
    client.post(f"/api/tasks/{b}/dependencies", json={"predecessor_id": a})
    r = client.post(f"/api/tasks/{a}/dependencies", json={"predecessor_id": b})
    assert r.status_code == 400


def test_delete_dependency(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    b = client.post(f"/api/projects/{pid}/tasks", json={"name": "B"}).json()["id"]
    dep = client.post(f"/api/tasks/{b}/dependencies", json={"predecessor_id": a}).json()["id"]
    r = client.delete(f"/api/dependencies/{dep}")
    assert r.status_code == 204


def test_add_dependency_non_int_payload_422(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    t1 = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    t2 = client.post(f"/api/projects/{pid}/tasks", json={"name": "B"}).json()["id"]
    r = client.post(f"/api/tasks/{t2}/dependencies", json={"predecessor_id": [t1]})
    assert r.status_code == 422


def test_missing_successor_404(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    t1 = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    r = client.post(f"/api/tasks/99999/dependencies", json={"predecessor_id": t1})
    assert r.status_code == 404


def test_cross_project_dependency_400(client):
    p1 = client.post("/api/projects", json={"name": "P1"}).json()["id"]
    p2 = client.post("/api/projects", json={"name": "P2"}).json()["id"]
    a = client.post(f"/api/projects/{p1}/tasks", json={"name": "A"}).json()["id"]
    b = client.post(f"/api/projects/{p2}/tasks", json={"name": "B"}).json()["id"]
    r = client.post(f"/api/tasks/{b}/dependencies", json={"predecessor_id": a})
    assert r.status_code == 400


def test_duplicate_add_returns_200_with_existing(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    b = client.post(f"/api/projects/{pid}/tasks", json={"name": "B"}).json()["id"]
    first = client.post(f"/api/tasks/{b}/dependencies", json={"predecessor_id": a})
    assert first.status_code == 201
    second = client.post(f"/api/tasks/{b}/dependencies", json={"predecessor_id": a})
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_list_project_dependencies(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    b = client.post(f"/api/projects/{pid}/tasks", json={"name": "B"}).json()["id"]
    c = client.post(f"/api/projects/{pid}/tasks", json={"name": "C"}).json()["id"]
    client.post(f"/api/tasks/{b}/dependencies", json={"predecessor_id": a})
    client.post(f"/api/tasks/{c}/dependencies", json={"predecessor_id": b})
    r = client.get(f"/api/projects/{pid}/dependencies")
    assert r.status_code == 200
    deps = r.json()
    assert len(deps) == 2
    pairs = {(d["predecessor_id"], d["successor_id"]) for d in deps}
    assert (a, b) in pairs
    assert (b, c) in pairs


def test_three_node_cycle_rejected(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    b = client.post(f"/api/projects/{pid}/tasks", json={"name": "B"}).json()["id"]
    c = client.post(f"/api/projects/{pid}/tasks", json={"name": "C"}).json()["id"]
    client.post(f"/api/tasks/{b}/dependencies", json={"predecessor_id": a})
    client.post(f"/api/tasks/{c}/dependencies", json={"predecessor_id": b})
    r = client.post(f"/api/tasks/{a}/dependencies", json={"predecessor_id": c})
    assert r.status_code == 400


def test_delete_task_cascades_dependencies(client, db_session):
    from app.models import TaskDependency

    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/tasks", json={"name": "A"}).json()["id"]
    b = client.post(f"/api/projects/{pid}/tasks", json={"name": "B"}).json()["id"]
    dep = client.post(f"/api/tasks/{b}/dependencies", json={"predecessor_id": a}).json()
    dep_id = dep["id"]

    r = client.delete(f"/api/tasks/{a}")
    assert r.status_code == 204

    db_session.expire_all()
    assert db_session.get(TaskDependency, dep_id) is None
