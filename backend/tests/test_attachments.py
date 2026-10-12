"""Attachment API integration tests."""

import io


def _png_bytes() -> bytes:
    # 1x1 transparent PNG
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
        b"\x89\x00\x00\x00\rIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_upload_list_download_delete(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]

    r = client.post(
        f"/api/attachments/task/{tid}",
        files={"file": ("hello.txt", io.BytesIO(b"hi"), "text/plain")},
    )
    assert r.status_code == 201, r.text
    att = r.json()
    assert att["original_name"] == "hello.txt"
    assert att["size"] == 2
    aid = att["id"]

    listed = client.get(f"/api/attachments/task/{tid}").json()
    assert len(listed) == 1
    assert listed[0]["id"] == aid

    # download must work (regression: was shadowed by /{entity_type}/{entity_id})
    r = client.get(f"/api/attachments/{aid}/download")
    assert r.status_code == 200
    assert r.content == b"hi"
    assert r.headers["content-disposition"].startswith("attachment;")

    client.delete(f"/api/attachments/{aid}")
    assert client.get(f"/api/attachments/task/{tid}").json() == []


def test_upload_rejects_oversize(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    big = b"x" * (20 * 1024 * 1024 + 1)
    r = client.post(
        f"/api/attachments/task/{tid}",
        files={"file": ("big.bin", io.BytesIO(big), "application/octet-stream")},
    )
    assert r.status_code == 413


def test_upload_respects_count_limit(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    for i in range(10):
        r = client.post(
            f"/api/attachments/task/{tid}",
            files={"file": (f"f{i}.txt", io.BytesIO(b"x"), "text/plain")},
        )
        assert r.status_code == 201
    r = client.post(
        f"/api/attachments/task/{tid}",
        files={"file": ("over.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert r.status_code == 400
    assert "上限" in r.json()["detail"]


def test_upload_to_missing_entity_404(client, db_session):
    r = client.post(
        "/api/attachments/task/9999",
        files={"file": ("x.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert r.status_code == 404


def test_invalid_entity_type_rejected(client, db_session):
    # /{entity_type}/{entity_id} with bogus type must NOT shadow /{aid}/download.
    r = client.get("/api/attachments/bogus/9")
    assert r.status_code == 422

    r = client.post("/api/attachments/bogus/9")
    assert r.status_code == 405 or r.status_code == 422


def test_cost_attachment_count_limit(client, db_session):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    cid = client.post(
        "/api/costs",
        json={
            "project_id": pid,
            "name": "C",
            "category": "other",
            "amount": 1,
            "spent_at": "2026-01-01",
        },
    ).json()["id"]
    for i in range(5):
        r = client.post(
            f"/api/attachments/cost/{cid}",
            files={"file": (f"f{i}.txt", io.BytesIO(b"x"), "text/plain")},
        )
        assert r.status_code == 201
    r = client.post(
        f"/api/attachments/cost/{cid}",
        files={"file": ("over.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert r.status_code == 400


def test_inbox_attachment_count_limit(client, db_session):
    iid = client.post("/api/inbox", json={"kind": "idea", "title": "I"}).json()["id"]
    for i in range(5):
        r = client.post(
            f"/api/attachments/inbox/{iid}",
            files={"file": (f"f{i}.txt", io.BytesIO(b"x"), "text/plain")},
        )
        assert r.status_code == 201
    r = client.post(
        f"/api/attachments/inbox/{iid}",
        files={"file": ("over.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert r.status_code == 400


def test_deleting_task_cascades_attachments(client, db_session, tmp_path):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    tid = client.post(f"/api/projects/{pid}/tasks", json={"name": "T"}).json()["id"]
    aid = client.post(
        f"/api/attachments/task/{tid}",
        files={"file": ("x.txt", io.BytesIO(b"x"), "text/plain")},
    ).json()["id"]

    # File should exist on disk (we can't check directly, but we can try delete + fetch)
    r = client.delete(f"/api/tasks/{tid}")
    assert r.status_code == 204
    # Attachment metadata row gone
    r = client.get(f"/api/attachments/{aid}")
    assert r.status_code == 404
