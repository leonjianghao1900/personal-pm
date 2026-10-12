"""Seed demo data so the gantt view has something to show."""
import json
import urllib.request

BASE = "http://127.0.0.1:8765/api"


def req(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(
        BASE + path, method=method, data=data,
        headers={"Content-Type": "application/json; charset=utf-8"} if data else {},
    )
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read().decode("utf-8"))


req("POST", "/projects", {"name": "装修项目", "color": "#ff9500"})
p = req("GET", "/projects")[0]
pid = p["id"]

t1 = req("POST", f"/projects/{pid}/tasks", {"name": "设计方案确认", "start_date": "2026-08-10", "end_date": "2026-08-16", "status": "done", "progress": 100})
t2 = req("POST", f"/projects/{pid}/tasks", {"name": "拆改工程", "start_date": "2026-08-15", "end_date": "2026-08-20", "status": "done", "progress": 100})
t3 = req("POST", f"/projects/{pid}/tasks", {"name": "水电改造", "start_date": "2026-08-20", "end_date": "2026-09-02", "status": "progress", "progress": 55})
t3a = req("POST", f"/projects/{pid}/tasks", {"name": "布线开槽", "parent_id": t3["id"], "start_date": "2026-08-20", "end_date": "2026-08-26", "status": "done", "progress": 100})
t3b = req("POST", f"/projects/{pid}/tasks", {"name": "水管安装", "parent_id": t3["id"], "start_date": "2026-08-26", "end_date": "2026-09-01", "status": "delayed", "progress": 30})
t4 = req("POST", f"/projects/{pid}/tasks", {"name": "泥木工程", "start_date": "2026-09-02", "end_date": "2026-09-18", "status": "todo"})
t5 = req("POST", f"/projects/{pid}/tasks", {"name": "油漆工程", "start_date": "2026-09-15", "end_date": "2026-09-28", "status": "cancelled"})
t6 = req("POST", f"/projects/{pid}/tasks", {"name": "竣工验收", "start_date": "2026-09-28", "end_date": "2026-09-30", "status": "todo", "is_milestone": True})

req("POST", f"/tasks/{t2['id']}/dependencies", {"predecessor_id": t1["id"]})
req("POST", f"/tasks/{t3['id']}/dependencies", {"predecessor_id": t2["id"]})
req("POST", f"/tasks/{t4['id']}/dependencies", {"predecessor_id": t3["id"]})
req("POST", f"/tasks/{t6['id']}/dependencies", {"predecessor_id": t4["id"]})

tasks = req("GET", f"/projects/{pid}/tasks")
deps = req("GET", f"/projects/{pid}/dependencies")
print(f"seeded: project '{p['name']}' (id={pid}), {len(tasks)} tasks, {len(deps)} dependencies")