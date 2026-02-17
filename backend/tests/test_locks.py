import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.lock import TaskLock
from app.models.task import Task


@pytest.fixture
async def project(client):
    resp = await client.post("/projects", json={"name": "Lock Test Project"})
    return resp.json()


async def make_task(client, session, project_id, points=None):
    """Create a task via API, optionally set points directly in DB."""
    resp = await client.post(
        f"/projects/{project_id}/tasks",
        json={"name": "Test Task", "task_type": "feature"},
    )
    task_data = resp.json()
    if points is not None:
        result = await session.execute(
            select(Task).where(Task.id == uuid.UUID(task_data["id"]))
        )
        task = result.scalar_one()
        task.points = points
        await session.flush()
    return task_data


# --- Acquire ---


@pytest.mark.asyncio
async def test_acquire_lock_sizing(client, project, session):
    task = await make_task(client, session, project["id"])
    resp = await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "sizing"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["task_id"] == task["id"]
    assert data["caller_label"] == "agent-1"
    assert data["lock_purpose"] == "sizing"
    assert data["expires_at"] is not None


@pytest.mark.asyncio
async def test_acquire_lock_refinement(client, project, session):
    task = await make_task(client, session, project["id"])
    resp = await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "refinement"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_acquire_lock_breakdown(client, project, session):
    task = await make_task(client, session, project["id"], points=8)
    resp = await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "breakdown"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_acquire_lock_implementation(client, project, session):
    task = await make_task(client, session, project["id"], points=3)
    resp = await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "implementation"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_acquire_lock_conflict(client, project, session):
    task = await make_task(client, session, project["id"])
    resp = await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "sizing"},
    )
    assert resp.status_code == 201

    resp = await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-2", "lock_purpose": "sizing"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_acquire_lock_expired_auto_released(client, project, session):
    task = await make_task(client, session, project["id"])
    resp = await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "sizing"},
    )
    assert resp.status_code == 201

    # Manually expire the lock
    result = await session.execute(
        select(TaskLock).where(TaskLock.task_id == uuid.UUID(task["id"]))
    )
    lock = result.scalar_one()
    lock.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await session.flush()

    resp = await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-2", "lock_purpose": "sizing"},
    )
    assert resp.status_code == 201
    assert resp.json()["caller_label"] == "agent-2"


# --- Precondition failures ---


@pytest.mark.asyncio
async def test_acquire_sizing_already_sized(client, project, session):
    task = await make_task(client, session, project["id"], points=3)
    resp = await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "sizing"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_acquire_breakdown_unsized_task(client, project, session):
    task = await make_task(client, session, project["id"])
    resp = await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "breakdown"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_acquire_implementation_not_ready(client, project, session):
    task = await make_task(client, session, project["id"])
    resp = await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "implementation"},
    )
    assert resp.status_code == 422


# --- Heartbeat ---


@pytest.mark.asyncio
async def test_heartbeat_extends_expiry(client, project, session):
    task = await make_task(client, session, project["id"])
    resp = await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "sizing"},
    )
    original_expires = resp.json()["expires_at"]

    resp = await client.patch(
        f"/tasks/{task['id']}/lock/heartbeat?caller_label=agent-1",
    )
    assert resp.status_code == 200
    assert resp.json()["expires_at"] >= original_expires
    assert resp.json()["last_heartbeat_at"] is not None


@pytest.mark.asyncio
async def test_heartbeat_wrong_caller(client, project, session):
    task = await make_task(client, session, project["id"])
    await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "sizing"},
    )
    resp = await client.patch(
        f"/tasks/{task['id']}/lock/heartbeat?caller_label=agent-2",
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_heartbeat_no_lock(client, project, session):
    task = await make_task(client, session, project["id"])
    resp = await client.patch(
        f"/tasks/{task['id']}/lock/heartbeat?caller_label=agent-1",
    )
    assert resp.status_code == 404


# --- Release ---


@pytest.mark.asyncio
async def test_release_lock(client, project, session):
    task = await make_task(client, session, project["id"])
    await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "sizing"},
    )
    resp = await client.delete(
        f"/tasks/{task['id']}/lock?caller_label=agent-1",
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_release_wrong_caller(client, project, session):
    task = await make_task(client, session, project["id"])
    await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "sizing"},
    )
    resp = await client.delete(
        f"/tasks/{task['id']}/lock?caller_label=agent-2",
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_force_release(client, project, session):
    task = await make_task(client, session, project["id"])
    await client.post(
        f"/tasks/{task['id']}/lock",
        json={"caller_label": "agent-1", "lock_purpose": "sizing"},
    )
    resp = await client.delete(
        f"/tasks/{task['id']}/lock?caller_label=other&force=true",
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_release_no_lock(client, project, session):
    task = await make_task(client, session, project["id"])
    resp = await client.delete(
        f"/tasks/{task['id']}/lock?caller_label=agent-1",
    )
    assert resp.status_code == 404
