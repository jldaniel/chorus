import pytest


@pytest.mark.asyncio
async def test_create_project(client):
    resp = await client.post("/projects", json={"name": "Test Project"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Project"
    assert data["description"] is None
    assert "id" in data


@pytest.mark.asyncio
async def test_create_project_with_description(client):
    resp = await client.post(
        "/projects", json={"name": "P2", "description": "A description"}
    )
    assert resp.status_code == 201
    assert resp.json()["description"] == "A description"


@pytest.mark.asyncio
async def test_list_projects(client):
    await client.post("/projects", json={"name": "P1"})
    await client.post("/projects", json={"name": "P2"})
    resp = await client.get("/projects")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_get_project_detail(client):
    create_resp = await client.post("/projects", json={"name": "Detail Project"})
    pid = create_resp.json()["id"]

    resp = await client.get(f"/projects/{pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Detail Project"
    assert data["task_count"] == 0
    assert data["points_total"] == 0
    assert data["points_completed"] == 0


@pytest.mark.asyncio
async def test_get_project_detail_with_tasks(client):
    create_resp = await client.post("/projects", json={"name": "Stats Project"})
    pid = create_resp.json()["id"]

    await client.post(
        f"/projects/{pid}/tasks",
        json={"name": "T1", "task_type": "feature"},
    )

    resp = await client.get(f"/projects/{pid}")
    data = resp.json()
    assert data["task_count"] == 1


@pytest.mark.asyncio
async def test_update_project(client):
    create_resp = await client.post("/projects", json={"name": "Old Name"})
    pid = create_resp.json()["id"]

    resp = await client.put(f"/projects/{pid}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_project(client):
    create_resp = await client.post("/projects", json={"name": "To Delete"})
    pid = create_resp.json()["id"]

    resp = await client.delete(f"/projects/{pid}")
    assert resp.status_code == 204

    resp = await client.get(f"/projects/{pid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_project_not_found(client):
    resp = await client.get("/projects/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_project_tasks(client):
    create_resp = await client.post("/projects", json={"name": "Task Project"})
    pid = create_resp.json()["id"]

    await client.post(
        f"/projects/{pid}/tasks",
        json={"name": "Task 1", "task_type": "feature"},
    )
    await client.post(
        f"/projects/{pid}/tasks",
        json={"name": "Task 2", "task_type": "bug"},
    )

    resp = await client.get(f"/projects/{pid}/tasks")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 2
    assert tasks[0]["name"] == "Task 1"
    assert tasks[1]["name"] == "Task 2"
