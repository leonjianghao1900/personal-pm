from datetime import date, timedelta

# 相对今天计算日期，避免测试随运行时间推移而失效。
TODAY = date.today()
THIS_MONTH = TODAY.replace(day=1)
PREV_MONTH = (THIS_MONTH - timedelta(days=1)).replace(day=1)


def iso(d: date) -> str:
    return d.isoformat()


def test_overview_empty(client, db_session):
    r = client.get("/api/stats/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["project_count"] == 0
    assert body["active_task_count"] == 0
    assert body["delayed_task_count"] == 0
    assert body["this_month_cost"] == 0.0
    assert body["projects"] == []


def test_overview_counts_and_progress(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    # 3 个叶子任务，1 个完成
    client.post(f"/api/projects/{pid}/tasks", json={"name": "A", "status": "done"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "B", "status": "progress"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "C", "status": "delayed"})
    # 本月一笔费用
    client.post("/api/costs", json={
        "project_id": pid, "name": "Cost", "category": "other", "amount": 100,
        "spent_at": iso(THIS_MONTH),
    })
    r = client.get("/api/stats/overview")
    body = r.json()
    assert body["project_count"] == 1
    assert body["active_task_count"] == 1
    assert body["delayed_task_count"] == 1
    assert body["this_month_cost"] == 100.0
    p = body["projects"][0]
    assert p["task_total"] == 3
    assert p["task_done"] == 1
    assert p["progress"] == 33


def test_overview_nested_progress(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    root = client.post(f"/api/projects/{pid}/tasks", json={"name": "根"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/tasks", json={"name": "A", "parent_id": root}).json()["id"]
    b = client.post(f"/api/projects/{pid}/tasks", json={"name": "B", "parent_id": root}).json()["id"]
    client.post(f"/api/projects/{pid}/tasks", json={"name": "A1", "parent_id": a, "status": "done"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "A2", "parent_id": a, "status": "done"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "B1", "parent_id": b})
    # 任务描述里写的"B 无子任务所以 B 是叶子"是错的 — B 有子任务 B1。
    # 实际权重：A1=1(done), A2=1(done), B1=1(todo)。叶子 = A1,A2,B1 = 3，
    # 完成权重 = 2 → round(2/3*100) = 67。
    r = client.get("/api/stats/overview")
    p = r.json()["projects"][0]
    assert p["progress"] == 67


def test_overview_next_due(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    client.post(f"/api/projects/{pid}/tasks", json={"name": "晚的", "end_date": iso(TODAY + timedelta(days=30))})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "早的", "end_date": iso(TODAY + timedelta(days=5))})
    r = client.get("/api/stats/overview")
    nd = r.json()["projects"][0]["next_due_task"]
    assert nd["name"] == "早的"
    assert nd["end_date"] == iso(TODAY + timedelta(days=5))


def test_overview_this_month_excludes_other_months(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    client.post("/api/costs", json={
        "project_id": pid, "name": "上月 cost", "category": "other", "amount": 200,
        "spent_at": iso(PREV_MONTH + timedelta(days=14)),
    })
    client.post("/api/costs", json={
        "project_id": pid, "name": "本月 cost", "category": "other", "amount": 50,
        "spent_at": iso(THIS_MONTH),
    })
    r = client.get("/api/stats/overview")
    assert r.json()["this_month_cost"] == 50.0


def test_overview_next_due_filters_done_cancelled_past(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    client.post(f"/api/projects/{pid}/tasks", json={"name": "已完成未来", "end_date": iso(TODAY + timedelta(days=60)), "status": "done"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "已取消未来", "end_date": iso(TODAY + timedelta(days=60)), "status": "cancelled"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "过期未完成", "end_date": iso(TODAY - timedelta(days=300)), "status": "progress"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "有效", "end_date": iso(TODAY + timedelta(days=5))})
    r = client.get("/api/stats/overview")
    p = r.json()["projects"][0]
    assert p["next_due_task"]["name"] == "有效"
    assert p["task_total"] == 4
    assert p["task_done"] == 1
    assert r.json()["active_task_count"] == 1
    assert r.json()["delayed_task_count"] == 0


def test_overview_progress_full_when_all_done(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    client.post(f"/api/projects/{pid}/tasks", json={"name": "A", "status": "done"})
    client.post(f"/api/projects/{pid}/tasks", json={"name": "B", "status": "done"})
    r = client.get("/api/stats/overview")
    assert r.json()["projects"][0]["progress"] == 100
