import pytest


@pytest.fixture
async def project(client):
    resp = await client.post("/projects", json={"name": "Discovery Test Project"})
    return resp.json()


def _dim(score=1):
    return {"score": score, "reasoning": "test"}


async def _create_task(client, project_id, name="Task", task_type="feature", **kwargs):
    resp = await client.post(
        f"/projects/{project_id}/tasks",
        json={"name": name, "task_type": task_type, **kwargs},
    )
    assert resp.status_code == 201
    return resp.json()


async def _size_task(client, task_id, confidence=4):
    resp = await client.post(
        f"/tasks/{task_id}/size",
        json={
            "scope_clarity": _dim(),
            "decision_points": _dim(),
            "context_window_demand": _dim(),
            "verification_complexity": _dim(),
            "domain_specificity": _dim(),
            "confidence": confidence,
            "work_log_content": "sized",
        },
    )
    assert resp.status_code == 200
    return resp.json()


async def _lock_task(client, task_id, purpose="implementation"):
    resp = await client.post(
        f"/tasks/{task_id}/lock",
        json={"caller_label": "agent-1", "lock_purpose": purpose},
    )
    assert resp.status_code == 201
    return resp.json()


async def _start_task(client, task_id):
    resp = await client.patch(f"/tasks/{task_id}/status", json={"status": "doing"})
    assert resp.status_code == 200
    return resp.json()


# --- /projects/{id}/backlog ---


@pytest.mark.asyncio
async def test_backlog_returns_ready_todo_tasks(client, project):
    pid = project["id"]
    t = await _create_task(client, pid, "Ready Task")
    await _size_task(client, t["id"])

    resp = await client.get(f"/projects/{pid}/backlog")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Ready Task"
    assert data[0]["readiness"] == "ready"


@pytest.mark.asyncio
async def test_backlog_excludes_unsized_tasks(client, project):
    pid = project["id"]
    await _create_task(client, pid, "Unsized")

    resp = await client.get(f"/projects/{pid}/backlog")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_backlog_excludes_doing_tasks(client, project):
    pid = project["id"]
    t = await _create_task(client, pid, "Doing Task")
    await _size_task(client, t["id"])
    await _start_task(client, t["id"])

    resp = await client.get(f"/projects/{pid}/backlog")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_backlog_404_nonexistent_project(client):
    resp = await client.get("/projects/00000000-0000-0000-0000-000000000000/backlog")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_backlog_pagination(client, project):
    pid = project["id"]
    for i in range(3):
        t = await _create_task(client, pid, f"Task {i}")
        await _size_task(client, t["id"])

    resp = await client.get(f"/projects/{pid}/backlog?limit=2&offset=0")
    assert len(resp.json()) == 2

    resp = await client.get(f"/projects/{pid}/backlog?limit=2&offset=2")
    assert len(resp.json()) == 1


# --- /projects/{id}/in-progress ---


@pytest.mark.asyncio
async def test_in_progress_returns_doing_tasks(client, project):
    pid = project["id"]
    t = await _create_task(client, pid, "In Progress")
    await _size_task(client, t["id"])
    await _start_task(client, t["id"])

    resp = await client.get(f"/projects/{pid}/in-progress")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "In Progress"


@pytest.mark.asyncio
async def test_in_progress_includes_lock_info(client, project):
    pid = project["id"]
    t = await _create_task(client, pid, "Locked")
    await _size_task(client, t["id"])
    await _start_task(client, t["id"])
    await _lock_task(client, t["id"])

    resp = await client.get(f"/projects/{pid}/in-progress")
    data = resp.json()
    assert data[0]["lock_caller_label"] == "agent-1"
    assert data[0]["lock_purpose"] == "implementation"
    assert data[0]["lock_expires_at"] is not None


@pytest.mark.asyncio
async def test_in_progress_no_lock_info_when_unlocked(client, project):
    pid = project["id"]
    t = await _create_task(client, pid, "Unlocked")
    await _size_task(client, t["id"])
    await _start_task(client, t["id"])

    resp = await client.get(f"/projects/{pid}/in-progress")
    data = resp.json()
    assert data[0]["lock_caller_label"] is None


@pytest.mark.asyncio
async def test_in_progress_404_nonexistent_project(client):
    resp = await client.get("/projects/00000000-0000-0000-0000-000000000000/in-progress")
    assert resp.status_code == 404


# --- /projects/{id}/needs-refinement ---


@pytest.mark.asyncio
async def test_needs_refinement_returns_flagged_tasks(client, project):
    pid = project["id"]
    t = await _create_task(client, pid, "Needs Refine")
    resp = await client.post(
        f"/tasks/{t['id']}/flag-refinement",
        json={"refinement_notes": "unclear"},
    )
    assert resp.status_code == 200

    resp = await client.get(f"/projects/{pid}/needs-refinement")
    assert resp.status_code == 200
    data = resp.json()
    assert any(d["name"] == "Needs Refine" for d in data)


@pytest.mark.asyncio
async def test_needs_refinement_returns_low_confidence(client, project):
    pid = project["id"]
    t = await _create_task(client, pid, "Low Confidence")
    await _size_task(client, t["id"], confidence=1)

    resp = await client.get(f"/projects/{pid}/needs-refinement")
    assert resp.status_code == 200
    data = resp.json()
    assert any(d["name"] == "Low Confidence" for d in data)


@pytest.mark.asyncio
async def test_needs_refinement_excludes_high_confidence(client, project):
    pid = project["id"]
    t = await _create_task(client, pid, "High Confidence")
    await _size_task(client, t["id"], confidence=4)

    resp = await client.get(f"/projects/{pid}/needs-refinement")
    data = resp.json()
    assert not any(d["name"] == "High Confidence" for d in data)


@pytest.mark.asyncio
async def test_needs_refinement_404(client):
    resp = await client.get("/projects/00000000-0000-0000-0000-000000000000/needs-refinement")
    assert resp.status_code == 404


# --- /tasks/available ---


@pytest.mark.asyncio
async def test_available_sizing(client, project):
    pid = project["id"]
    await _create_task(client, pid, "Unsized")

    resp = await client.get(f"/tasks/available?operation=sizing&project_id={pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Unsized"


@pytest.mark.asyncio
async def test_available_sizing_excludes_sized(client, project):
    pid = project["id"]
    t = await _create_task(client, pid, "Sized")
    await _size_task(client, t["id"])

    resp = await client.get(f"/tasks/available?operation=sizing&project_id={pid}")
    data = resp.json()
    assert not any(d["name"] == "Sized" for d in data)


@pytest.mark.asyncio
async def test_available_implementation(client, project):
    pid = project["id"]
    t = await _create_task(client, pid, "Ready")
    await _size_task(client, t["id"])

    resp = await client.get(f"/tasks/available?operation=implementation&project_id={pid}")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Ready"


@pytest.mark.asyncio
async def test_available_excludes_locked(client, project):
    pid = project["id"]
    t = await _create_task(client, pid, "Locked")
    await _size_task(client, t["id"])
    await _lock_task(client, t["id"])

    resp = await client.get(f"/tasks/available?operation=implementation&project_id={pid}")
    data = resp.json()
    assert not any(d["name"] == "Locked" for d in data)


@pytest.mark.asyncio
async def test_available_breakdown(client, project):
    pid = project["id"]
    t = await _create_task(client, pid, "Big Task")
    # Size with high points so it needs breakdown (>6)
    # The sizing endpoint computes points from dimensions, so we need to check what points it gets
    await _size_task(client, t["id"])
    # If points <= 6, manually check — the dimension scores of 1 each sum to 5, which maps to points
    # Let's just check the endpoint returns tasks that need breakdown
    # A task with points > 6 needs breakdown, but sizing computes from dimensions
    # Instead, create a parent with an unsized child
    await _create_task(client, pid, "Child of Big")
    # Create subtask under the big task
    resp = await client.post(
        f"/tasks/{t['id']}/subtasks",
        json={"name": "Unsized Child", "task_type": "feature"},
    )
    assert resp.status_code == 201

    resp = await client.get(f"/tasks/available?operation=breakdown&project_id={pid}")
    data = resp.json()
    # The parent task should need breakdown because it has unsized children
    assert any(d["name"] == "Big Task" for d in data)


@pytest.mark.asyncio
async def test_available_filter_by_task_type(client, project):
    pid = project["id"]
    await _create_task(client, pid, "Feature", task_type="feature")
    await _create_task(client, pid, "Bug", task_type="bug")

    resp = await client.get(f"/tasks/available?operation=sizing&project_id={pid}&task_type=feature")
    data = resp.json()
    assert len(data) >= 1
    assert all(d["task_type"] == "feature" for d in data)


@pytest.mark.asyncio
async def test_available_filter_by_points(client, project):
    pid = project["id"]
    t1 = await _create_task(client, pid, "Small")
    sized1 = await _size_task(client, t1["id"])
    t2 = await _create_task(client, pid, "Medium")
    await _size_task(client, t2["id"])
    # Both get same points from sizing, so let's test with effective_points filter
    ep = sized1["effective_points"]

    resp = await client.get(
        f"/tasks/available?operation=implementation&project_id={pid}&min_points={ep}&max_points={ep}"
    )
    data = resp.json()
    assert len(data) >= 1
    assert all(d["effective_points"] == ep for d in data)


@pytest.mark.asyncio
async def test_available_requires_operation(client):
    resp = await client.get("/tasks/available")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_available_pagination(client, project):
    pid = project["id"]
    for i in range(3):
        await _create_task(client, pid, f"Unsized {i}")

    resp = await client.get(f"/tasks/available?operation=sizing&project_id={pid}&limit=2")
    assert len(resp.json()) == 2

    resp = await client.get(f"/tasks/available?operation=sizing&project_id={pid}&limit=2&offset=2")
    assert len(resp.json()) == 1
