def test_create_project_with_description(client, db_session):
    r = client.post("/api/projects", json={"name": "P", "description": "一个测试项目"})
    assert r.status_code == 201, r.text
    assert r.json()["description"] == "一个测试项目"


def test_update_project_description(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    r = client.patch(f"/api/projects/{pid}", json={"description": "新描述"})
    assert r.status_code == 200
    assert r.json()["description"] == "新描述"


def test_project_description_null_by_default(client, db_session):
    r = client.post("/api/projects", json={"name": "P"})
    assert r.json()["description"] is None


def test_project_description_too_long_422(client, db_session):
    r = client.post("/api/projects", json={"name": "P", "description": "x" * 2001})
    assert r.status_code == 422


def test_project_description_in_list(client, db_session):
    pid = client.post("/api/projects", json={"name": "P", "description": "abc"}).json()["id"]
    r = client.get("/api/projects")
    assert r.json()[0]["description"] == "abc"
