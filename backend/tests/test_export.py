import pytest


@pytest.fixture
async def project(client):
    resp = await client.post("/projects", json={"name": "Export Project"})
    return resp.json()


@pytest.mark.asyncio
async def test_export_project_with_tasks(client, project):
    pid = project["id"]

    # Create task
    task_resp = await client.post(
        f"/projects/{pid}/tasks",
        json={"name": "Task 1", "task_type": "feature"},
    )
    tid = task_resp.json()["id"]

    # Add work log
    await client.post(
        f"/tasks/{tid}/work-log",
        json={"operation": "note", "content": "A note", "author": "human"},
    )

    # Add commit
    await client.post(
        f"/tasks/{tid}/commits",
        json={
            "commit_hash": "abc1234567890123456789012345678901234567",
            "message": "feat: stuff",
            "committed_at": "2026-01-15T10:00:00Z",
        },
    )

    resp = await client.get(f"/projects/{pid}/export")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == pid
    assert data["name"] == "Export Project"
    assert "exported_at" in data
    assert len(data["tasks"]) == 1

    task = data["tasks"][0]
    assert task["name"] == "Task 1"
    assert task["parent_task_id"] is None
    assert len(task["work_log_entries"]) == 1
    assert len(task["commits"]) == 1
    assert task["commits"][0]["commit_hash"] == "abc1234567890123456789012345678901234567"


@pytest.mark.asyncio
async def test_export_empty_project(client, project):
    resp = await client.get(f"/projects/{project['id']}/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tasks"] == []


@pytest.mark.asyncio
async def test_export_nonexistent_project(client):
    resp = await client.get("/projects/00000000-0000-0000-0000-000000000000/export")
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"]["code"] == "NOT_FOUND"
