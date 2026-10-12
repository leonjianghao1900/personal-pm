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


def test_delete_project_cascades_tasks(client, db_session):
    from app.models import Task

    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]

    task = Task(project_id=pid, name="T1")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    task_id = task.id

    assert db_session.get(Task, task_id) is not None

    r = client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204

    db_session.expire_all()
    assert db_session.get(Task, task_id) is None
