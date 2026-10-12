"""P1 acceptance: end-to-end backend exercise via Python urllib (UTF-8 safe)."""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8765/api"


def req(method: str, path: str, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(
        BASE + path,
        method=method,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"} if data else {},
    )
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def main():
    # 1. Health
    code, body = req("GET", "/health")
    assert code == 200 and body == {"status": "ok"}, f"health failed: {code} {body}"
    print("[OK] 1. /api/health returns ok")

    # 2. Create 3 projects (spec: 至少 3 个项目)
    p1, p2, p3 = (req("POST", "/projects", {"name": "装修项目"})[1] for _ in range(3))
    assert all("id" in x for x in [p1, p2, p3]), f"project create failed: {p1} {p2} {p3}"
    print(f"[OK] 2. 3 projects created: ids={[p1['id'], p2['id'], p3['id']]}, names={[p1['name'], p2['name'], p3['name']]}")

    # 3. Multi-level nested tasks (project 1: 3 levels deep)
    t_root = req("POST", f"/projects/{p1['id']}/tasks", {
        "name": "水电", "start_date": "2026-08-17", "end_date": "2026-08-30",
        "status": "progress", "progress": 50
    })[1]
    t_child = req("POST", f"/projects/{p1['id']}/tasks", {
        "name": "布线", "parent_id": t_root["id"],
        "start_date": "2026-08-17", "end_date": "2026-08-22",
        "status": "done", "progress": 100
    })[1]
    t_grand = req("POST", f"/projects/{p1['id']}/tasks", {
        "name": "开槽", "parent_id": t_child["id"],
        "start_date": "2026-08-17", "end_date": "2026-08-19",
        "status": "done", "progress": 100
    })[1]
    assert t_grand["parent_id"] == t_child["id"]
    print(f"[OK] 3. 3-level nesting: root({t_root['id']}) → child({t_child['id']}) → grand({t_grand['id']})")

    # 4. Add tasks for 5 status colors
    statuses = ["todo", "progress", "delayed", "done", "cancelled"]
    task_ids_by_status = {}
    for st in statuses:
        if st == "done":
            continue  # already added as t_child
        if st == "progress":
            continue  # already added as t_root
        t = req("POST", f"/projects/{p1['id']}/tasks", {
            "name": f"task-{st}",
            "start_date": "2026-08-20", "end_date": "2026-08-25",
            "status": st
        })[1]
        task_ids_by_status[st] = t["id"]
    task_ids_by_status["progress"] = t_root["id"]
    task_ids_by_status["done"] = t_child["id"]
    all_statuses = req("GET", f"/projects/{p1['id']}/tasks")[1]
    distinct = {t["status"] for t in all_statuses}
    assert distinct == set(statuses), f"expected all 5 statuses, got {distinct}"
    print(f"[OK] 4. 5 status colors represented in tasks: {sorted(distinct)}")

    # 5. Drag-to-move (move endpoint changes dates)
    code, moved = req("POST", f"/tasks/{task_ids_by_status['todo']}/move",
                      {"start_date": "2026-08-22", "end_date": "2026-08-28"})
    assert code == 200 and moved["start_date"] == "2026-08-22" and moved["end_date"] == "2026-08-28"
    print(f"[OK] 5. move task {task_ids_by_status['todo']} to 2026-08-22..2026-08-28 (drag-to-move equivalent)")

    # 6. Dependency (chain: root → child → grand, plus an extra edge)
    code, d1 = req("POST", f"/tasks/{task_ids_by_status['delayed']}/dependencies",
                    {"predecessor_id": t_root["id"]})
    assert code == 201 and d1["predecessor_id"] == t_root["id"]
    code, d2 = req("POST", f"/tasks/{t_grand['id']}/dependencies",
                    {"predecessor_id": t_child["id"]})
    assert code == 201
    code, deps = req("GET", f"/projects/{p1['id']}/dependencies")
    assert code == 200 and len(deps) == 2
    print(f"[OK] 6. 2 dependencies persisted; reload returns same edges")

    # 7. Detail page data available (GET single task)
    code, detail = req("GET", f"/tasks/{t_grand['id']}")
    assert code == 200 and detail["parent_id"] == t_child["id"]
    print(f"[OK] 7. /api/tasks/{t_grand['id']} returns full record for detail page")

    # 8. Cycle detection: A→B exists, adding B→A must fail
    code, _ = req("POST", f"/tasks/{t_root['id']}/dependencies",
                  {"predecessor_id": task_ids_by_status['delayed']})
    # t_root already depends (transitively) on delayed via root→delayed;
    # adding the reverse would close a 2-node cycle.
    assert code == 400, f"cycle should be 400, got {code}"
    print(f"[OK] 8. 2-node cycle rejected with 400 (defense-in-depth)")

    # 9. List all projects
    code, projects = req("GET", "/projects")
    assert code == 200 and len(projects) == 3
    print(f"[OK] 9. {len(projects)} projects listed via /api/projects")

    print()
    print("=" * 50)
    print("P1 BACKEND ACCEPTANCE: ALL 9 CHECKS PASS")
    print("=" * 50)


if __name__ == "__main__":
    main()