def _mk_item(client, kind="idea", title="T", **kw):
    payload = {"kind": kind, "title": title, **kw}
    r = client.post("/api/inbox", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_idea(client):
    item = _mk_item(client, kind="idea", title="做个小工具")
    assert item["kind"] == "idea"
    assert item["status"] == "active"
    assert item["priority"] == "normal"


def test_create_interrupt(client):
    item = _mk_item(client, kind="interrupt", title="妈妈打电话", priority="urgent")
    assert item["kind"] == "interrupt"
    assert item["priority"] == "urgent"


def test_invalid_kind_422(client):
    r = client.post("/api/inbox", json={"kind": "other", "title": "x"})
    assert r.status_code == 422


def test_list_inbox(client):
    _mk_item(client, kind="idea", title="a")
    _mk_item(client, kind="interrupt", title="b")
    items = client.get("/api/inbox").json()
    assert len(items) == 2
    ideas = client.get("/api/inbox?kind=idea").json()
    assert len(ideas) == 1
    assert ideas[0]["title"] == "a"


def test_update_status_completed_sets_completed_at(client):
    item = _mk_item(client)
    r = client.patch(f"/api/inbox/{item['id']}", json={"status": "completed"})
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    assert r.json()["completed_at"] is not None


def test_update_title(client):
    item = _mk_item(client)
    r = client.patch(f"/api/inbox/{item['id']}", json={"title": "改标题"})
    assert r.json()["title"] == "改标题"


def test_update_invalid_status_422(client):
    item = _mk_item(client)
    r = client.patch(f"/api/inbox/{item['id']}", json={"status": "nope"})
    assert r.status_code == 422


def test_missing_item_404(client):
    assert client.patch("/api/inbox/9999", json={"title": "x"}).status_code == 404
    assert client.delete("/api/inbox/9999").status_code == 404


def test_promote_idea_creates_task(client):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    item = _mk_item(client, kind="idea", title="转正测试")
    r = client.post(f"/api/inbox/{item['id']}/promote", json={"project_id": pid})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "archived"
    assert body["promoted_task_id"] is not None
    tasks = client.get(f"/api/projects/{pid}/tasks").json()
    assert any(t["id"] == body["promoted_task_id"] and t["name"] == "转正测试" for t in tasks)


def test_promote_without_project_400(client):
    item = _mk_item(client)
    r = client.post(f"/api/inbox/{item['id']}/promote", json={})
    assert r.status_code == 400


def test_promote_missing_item_404(client):
    r = client.post("/api/inbox/9999/promote", json={"project_id": 1})
    assert r.status_code == 404


def test_delete_item(client):
    item = _mk_item(client)
    r = client.delete(f"/api/inbox/{item['id']}")
    assert r.status_code == 204
    assert client.get("/api/inbox").json() == []