import pytest


@pytest.mark.asyncio
async def test_404_returns_structured_error(client):
    resp = await client.get("/projects/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data
    err = data["error"]
    assert err["code"] == "NOT_FOUND"
    assert err["message"] == "Project not found"
    assert "details" in err
    assert "request_id" in err


@pytest.mark.asyncio
async def test_409_returns_structured_error(client):
    # Create project and task, acquire lock, try to acquire again
    proj = await client.post("/projects", json={"name": "P"})
    pid = proj.json()["id"]
    task_resp = await client.post(
        f"/projects/{pid}/tasks",
        json={"name": "T", "task_type": "feature"},
    )
    tid = task_resp.json()["id"]

    # Size the task first so we can lock for implementation
    # Actually just lock for refinement (no precondition)
    await client.post(
        f"/tasks/{tid}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "refinement"},
    )
    resp = await client.post(
        f"/tasks/{tid}/lock",
        json={"caller_label": "agent-2", "lock_purpose": "refinement"},
    )
    assert resp.status_code == 409
    data = resp.json()
    assert data["error"]["code"] == "LOCK_CONFLICT"
    assert "request_id" in data["error"]


@pytest.mark.asyncio
async def test_422_status_transition_returns_structured_error(client):
    proj = await client.post("/projects", json={"name": "P"})
    pid = proj.json()["id"]
    task_resp = await client.post(
        f"/projects/{pid}/tasks",
        json={"name": "T", "task_type": "feature"},
    )
    tid = task_resp.json()["id"]

    # todo -> done is invalid
    resp = await client.patch(f"/tasks/{tid}/status", json={"status": "done"})
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["code"] == "INVALID_STATUS_TRANSITION"
    assert data["error"]["details"]["from"] == "todo"
    assert data["error"]["details"]["to"] == "done"
    assert "request_id" in data["error"]


@pytest.mark.asyncio
async def test_validation_error_returns_structured_error(client):
    # Missing required field
    resp = await client.post("/projects", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "errors" in data["error"]["details"]
    assert "request_id" in data["error"]


@pytest.mark.asyncio
async def test_x_request_id_header_present(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert "x-request-id" in resp.headers
