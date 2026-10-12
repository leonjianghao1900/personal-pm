import pytest


def _mk_project(client, name="P"):
    return client.post("/api/projects", json={"name": name}).json()["id"]


def _mk_cost(client, pid, category="material", amount=100.0, spent_at="2026-08-01", **kw):
    payload = {"name": "Cost", "category": category, "amount": amount, "spent_at": spent_at, **kw}
    r = client.post("/api/costs", json={**payload, "project_id": pid})
    assert r.status_code == 201, r.text
    return r.json()


def test_create_cost(client):
    pid = _mk_project(client)
    c = _mk_cost(client, pid, amount=88.5)
    assert c["project_id"] == pid
    assert c["category"] == "material"
    assert c["amount"] == 88.5


def test_create_cost_requires_name(client):
    pid = _mk_project(client)
    r = client.post("/api/costs", json={
        "project_id": pid, "category": "other", "amount": 10, "spent_at": "2026-08-01"
    })
    assert r.status_code == 422


@pytest.mark.parametrize("name", [None, "", "   ", "x" * 201])
def test_create_cost_rejects_invalid_name(client, name):
    pid = _mk_project(client)
    r = client.post("/api/costs", json={
        "project_id": pid, "name": name, "category": "other", "amount": 10,
        "spent_at": "2026-08-01",
    })
    assert r.status_code == 422


def test_create_cost_trims_name(client):
    pid = _mk_project(client)
    cost = _mk_cost(client, pid, name="  Padded cost  ")
    assert cost["name"] == "Padded cost"
    assert client.get(f"/api/projects/{pid}/costs").json()[0]["name"] == "Padded cost"


def test_create_cost_requires_existing_project(client):
    r = client.post("/api/costs", json={
        "project_id": 9999, "name": "Cost", "category": "other", "amount": 10,
        "spent_at": "2026-08-01",
    })
    assert r.status_code == 404


def test_create_cost_zero_amount_422(client):
    pid = _mk_project(client)
    r = client.post("/api/costs", json={
        "project_id": pid, "name": "Cost", "category": "other", "amount": 0,
        "spent_at": "2026-08-01",
    })
    assert r.status_code == 422


def test_list_project_costs(client):
    pid = _mk_project(client)
    _mk_cost(client, pid, amount=10)
    _mk_cost(client, pid, amount=20, category="labor")
    _mk_cost(client, pid, amount=30, category="travel", spent_at="2026-07-15")
    r = client.get(f"/api/projects/{pid}/costs")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_update_cost(client):
    pid = _mk_project(client)
    c = _mk_cost(client, pid, amount=50)
    r = client.patch(f"/api/costs/{c['id']}", json={"amount": 60.5, "category": "labor"})
    assert r.status_code == 200
    assert r.json()["amount"] == 60.5
    assert r.json()["category"] == "labor"


def test_update_cost_name(client):
    pid = _mk_project(client)
    c = _mk_cost(client, pid)
    r = client.patch(f"/api/costs/{c['id']}", json={"name": "  Renamed cost  "})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed cost"
    assert client.get(f"/api/projects/{pid}/costs").json()[0]["name"] == "Renamed cost"


@pytest.mark.parametrize("name", ["", "   ", None, "x" * 201])
def test_update_cost_rejects_invalid_name(client, name):
    pid = _mk_project(client)
    c = _mk_cost(client, pid)
    r = client.patch(f"/api/costs/{c['id']}", json={"name": name})
    assert r.status_code == 422


def test_update_missing_cost_404(client):
    r = client.patch("/api/costs/9999", json={"amount": 10})
    assert r.status_code == 404


def test_delete_cost(client):
    pid = _mk_project(client)
    c = _mk_cost(client, pid)
    r = client.delete(f"/api/costs/{c['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/projects/{pid}/costs").json() == []


def test_delete_project_cascades_costs(client, db_session):
    from app.models import Cost

    pid = _mk_project(client)
    c = _mk_cost(client, pid)
    r = client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204
    db_session.expire_all()
    assert db_session.get(Cost, c["id"]) is None


def test_cost_stats_all(client):
    pid = _mk_project(client)
    _mk_cost(client, pid, category="material", amount=100, spent_at="2026-08-01")
    _mk_cost(client, pid, category="material", amount=50, spent_at="2026-08-10")
    _mk_cost(client, pid, category="labor", amount=200, spent_at="2026-09-01")
    r = client.get("/api/stats/costs")
    assert r.status_code == 200
    s = r.json()
    assert s["total"] == 350.0
    assert s["count"] == 3
    assert s["by_category"]["material"] == 150.0
    assert s["by_category"]["labor"] == 200.0
    assert s["by_month"]["2026-08"] == 150.0
    assert s["by_month"]["2026-09"] == 200.0


def test_cost_stats_filtered_by_project(client):
    p1 = _mk_project(client, "P1")
    p2 = _mk_project(client, "P2")
    _mk_cost(client, p1, amount=10)
    _mk_cost(client, p2, amount=999)
    r = client.get(f"/api/stats/costs?project_id={p1}")
    assert r.status_code == 200
    assert r.json()["total"] == 10.0


def test_cost_stats_empty(client):
    pid = _mk_project(client)
    r = client.get(f"/api/stats/costs?project_id={pid}")
    assert r.json()["total"] == 0.0
    assert r.json()["count"] == 0


def test_create_cost_with_task(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    r = client.post("/api/costs", json={
        "project_id": pid, "name": "Cost", "category": "other", "amount": 10,
        "spent_at": "2026-08-01", "task_id": tid,
    })
    assert r.status_code == 201, r.text
    assert r.json()["task_id"] == tid


def test_cost_with_cross_project_task_400(client, db_session):
    p1 = client.post("/api/projects", json={"name": "P1"}).json()["id"]
    p2 = client.post("/api/projects", json={"name": "P2"}).json()["id"]
    t1 = client.post(f"/api/projects/{p1}/tasks", json={"name": "T"}).json()["id"]
    r = client.post("/api/costs", json={
        "project_id": p2, "name": "Cost", "category": "other", "amount": 10,
        "spent_at": "2026-08-01", "task_id": t1,
    })
    assert r.status_code == 400
    assert "任务不属于该项目" in r.json()["detail"]


def test_update_cost_task_id(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    t1 = client.post(f"/api/projects/{pid}/tasks", json={"name": "T1"}).json()["id"]
    t2 = client.post(f"/api/projects/{pid}/tasks", json={"name": "T2"}).json()["id"]
    cid = client.post("/api/costs", json={
        "project_id": pid, "name": "Cost", "category": "other", "amount": 10,
        "spent_at": "2026-08-01", "task_id": t1,
    }).json()["id"]
    r = client.patch(f"/api/costs/{cid}", json={"task_id": t2})
    assert r.status_code == 200
    assert r.json()["task_id"] == t2


def test_delete_task_sets_cost_task_id_null(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    cid = client.post("/api/costs", json={
        "project_id": pid, "name": "Cost", "category": "other", "amount": 10,
        "spent_at": "2026-08-01", "task_id": tid,
    }).json()["id"]
    client.delete(f"/api/tasks/{tid}")
    r = client.get(f"/api/projects/{pid}/costs")
    found = next(c for c in r.json() if c["id"] == cid)
    assert found["task_id"] is None


def test_cost_without_task_id_ok(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    r = client.post("/api/costs", json={
        "project_id": pid, "name": "Cost", "category": "other", "amount": 10,
        "spent_at": "2026-08-01",
    })
    assert r.status_code == 201
    assert r.json()["task_id"] is None


def test_update_cost_project_id(client):
    p1 = _mk_project(client, "P1")
    p2 = _mk_project(client, "P2")
    c = _mk_cost(client, p1, amount=50)
    r = client.patch(f"/api/costs/{c['id']}", json={"project_id": p2})
    assert r.status_code == 200, r.text
    assert r.json()["project_id"] == p2
    assert client.get(f"/api/projects/{p1}/costs").json() == []
    assert any(x["id"] == c["id"] for x in client.get(f"/api/projects/{p2}/costs").json())


def test_update_cost_project_id_clears_stale_task(client, db_session):
    p1 = _mk_project(client, "P1")
    p2 = _mk_project(client, "P2")
    tid = client.post(f"/api/projects/{p1}/tasks", json={"name": "T"}).json()["id"]
    cid = client.post("/api/costs", json={
        "project_id": p1, "name": "Cost", "category": "other", "amount": 10,
        "spent_at": "2026-08-01", "task_id": tid,
    }).json()["id"]
    r = client.patch(f"/api/costs/{cid}", json={"project_id": p2})
    assert r.status_code == 200, r.text
    assert r.json()["project_id"] == p2
    assert r.json()["task_id"] is None


def test_update_cost_project_id_with_new_task(client, db_session):
    p1 = _mk_project(client, "P1")
    p2 = _mk_project(client, "P2")
    t2 = client.post(f"/api/projects/{p2}/tasks", json={"name": "T2"}).json()["id"]
    cid = client.post("/api/costs", json={
        "project_id": p1, "name": "Cost", "category": "other", "amount": 10,
        "spent_at": "2026-08-01",
    }).json()["id"]
    r = client.patch(f"/api/costs/{cid}", json={"project_id": p2, "task_id": t2})
    assert r.status_code == 200, r.text
    assert r.json()["project_id"] == p2
    assert r.json()["task_id"] == t2
