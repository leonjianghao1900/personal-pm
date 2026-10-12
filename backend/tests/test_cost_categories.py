from app.models import CostCategory


def _mk_cat(client, name="新类别", color="#123456"):
    r = client.post("/api/cost-categories", json={"name": name, "color": color})
    assert r.status_code == 201, r.text
    return r.json()


def _mk_legacy_builtin(db_session, name="material", color="#0071e3"):
    c = CostCategory(name=name, color=color, is_builtin=True, sort_order=0)
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def test_list_empty_by_default(client, db_session):
    r = client.get("/api/cost-categories")
    assert r.status_code == 200
    assert r.json() == []


def test_create_category(client, db_session):
    c = _mk_cat(client)
    assert c["name"] == "新类别"
    assert c["is_builtin"] is False


def test_duplicate_name_409(client, db_session):
    _mk_cat(client, "material", "#0071e3")
    r = client.post("/api/cost-categories", json={"name": "material", "color": "#111111"})
    assert r.status_code == 409


def test_update_category_name_and_color(client, db_session):
    c = _mk_cat(client)
    r = client.patch(f"/api/cost-categories/{c['id']}", json={"name": "改名", "color": "#abcdef"})
    assert r.status_code == 200
    assert r.json()["name"] == "改名"
    assert r.json()["color"] == "#abcdef"


def test_update_duplicate_name_409(client, db_session):
    _mk_cat(client, "类别A")
    c = _mk_cat(client, "类别B")
    r = client.patch(f"/api/cost-categories/{c['id']}", json={"name": "类别A"})
    assert r.status_code == 409


def test_legacy_builtin_can_be_renamed(client, db_session):
    builtin = _mk_legacy_builtin(db_session)
    r = client.patch(f"/api/cost-categories/{builtin.id}", json={"name": "材料", "color": "#fedcba"})
    assert r.status_code == 200
    assert r.json()["name"] == "材料"
    assert r.json()["color"] == "#fedcba"


def test_delete_category(client, db_session):
    c = _mk_cat(client)
    r = client.delete(f"/api/cost-categories/{c['id']}")
    assert r.status_code == 204
    assert client.get("/api/cost-categories").json() == []


def test_legacy_builtin_can_be_deleted(client, db_session):
    builtin = _mk_legacy_builtin(db_session)
    r = client.delete(f"/api/cost-categories/{builtin.id}")
    assert r.status_code == 204
    assert client.get("/api/cost-categories").json() == []


def test_delete_referenced_409(client, db_session):
    _mk_cat(client, "material", "#0071e3")
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    r = client.post("/api/costs", json={
        "project_id": pid, "name": "Cost", "category": "material", "amount": 10,
        "spent_at": "2026-08-01",
    })
    assert r.status_code == 201
    cat_id = [c for c in client.get("/api/cost-categories").json() if c["name"] == "material"][0]["id"]
    r = client.delete(f"/api/cost-categories/{cat_id}")
    assert r.status_code == 409


def test_rename_referenced_category_updates_cost_and_still_blocks_delete(client, db_session):
    c = _mk_cat(client, "material", "#0071e3")
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    cost = client.post("/api/costs", json={
        "project_id": pid, "name": "Cost", "category": "material", "amount": 10,
        "spent_at": "2026-08-01",
    })
    assert cost.status_code == 201
    renamed = client.patch(f"/api/cost-categories/{c['id']}", json={"name": "材料"})
    assert renamed.status_code == 200
    costs = client.get(f"/api/projects/{pid}/costs").json()
    assert costs[0]["category"] == "材料"
    deleted = client.delete(f"/api/cost-categories/{c['id']}")
    assert deleted.status_code == 409


def test_delete_missing_404(client, db_session):
    r = client.delete("/api/cost-categories/9999")
    assert r.status_code == 404


def test_update_missing_404(client, db_session):
    r = client.patch("/api/cost-categories/9999", json={"name": "x"})
    assert r.status_code == 404
