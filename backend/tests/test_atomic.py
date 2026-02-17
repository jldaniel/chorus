import pytest


@pytest.fixture
async def project(client):
    resp = await client.post("/projects", json={"name": "Atomic Test Project"})
    return resp.json()


@pytest.fixture
async def task(client, project):
    resp = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "Test Task", "task_type": "feature"},
    )
    return resp.json()


def _sizing_payload(**overrides):
    base = {
        "scope_clarity": {"score": 1, "reasoning": "moderate"},
        "decision_points": {"score": 2, "reasoning": "many"},
        "context_window_demand": {"score": 0, "reasoning": "low"},
        "verification_complexity": {"score": 1, "reasoning": "medium"},
        "domain_specificity": {"score": 1, "reasoning": "some"},
        "confidence": 4,
        "work_log_content": "Sized the task",
        "author": "agent-1",
    }
    base.update(overrides)
    return base


# --- Sizing ---


@pytest.mark.asyncio
async def test_size_task(client, task):
    resp = await client.post(f"/tasks/{task['id']}/size", json=_sizing_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["points"] == 5  # 1+2+0+1+1
    assert data["readiness"] == "ready"


@pytest.mark.asyncio
async def test_size_task_creates_work_log(client, task):
    await client.post(f"/tasks/{task['id']}/size", json=_sizing_payload())
    resp = await client.get(f"/tasks/{task['id']}/work-log")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 1
    assert entries[0]["operation"] == "sizing"
    assert entries[0]["author"] == "agent-1"


@pytest.mark.asyncio
async def test_size_task_invalid_dimension_score(client, task):
    payload = _sizing_payload()
    payload["scope_clarity"]["score"] = 3
    resp = await client.post(f"/tasks/{task['id']}/size", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_size_task_invalid_confidence(client, task):
    payload = _sizing_payload(confidence=6)
    resp = await client.post(f"/tasks/{task['id']}/size", json=payload)
    assert resp.status_code == 422


# --- Breakdown ---


@pytest.mark.asyncio
async def test_breakdown_task(client, task):
    resp = await client.post(
        f"/tasks/{task['id']}/breakdown",
        json={
            "subtasks": [
                {"name": "Sub 1", "task_type": "feature"},
                {"name": "Sub 2", "task_type": "bug"},
            ],
            "work_log_content": "Broke down the task",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["children_count"] == 2


@pytest.mark.asyncio
async def test_breakdown_updates_parent_description(client, task):
    resp = await client.post(
        f"/tasks/{task['id']}/breakdown",
        json={
            "subtasks": [{"name": "Sub 1", "task_type": "feature"}],
            "parent_description_update": "Updated parent desc",
            "work_log_content": "Broke it down",
        },
    )
    assert resp.status_code == 200
    # Re-fetch to check description
    resp = await client.get(f"/tasks/{task['id']}")
    assert resp.json()["description"] == "Updated parent desc"


@pytest.mark.asyncio
async def test_breakdown_auto_positions(client, task):
    await client.post(
        f"/tasks/{task['id']}/breakdown",
        json={
            "subtasks": [
                {"name": "Sub 1", "task_type": "feature"},
                {"name": "Sub 2", "task_type": "feature"},
            ],
            "work_log_content": "Breakdown",
        },
    )
    # Check subtask positions via tree
    resp = await client.get(f"/tasks/{task['id']}/tree")
    children = resp.json()["children"]
    positions = sorted([c["position"] for c in children])
    assert positions == [0, 1]


@pytest.mark.asyncio
async def test_breakdown_creates_work_log(client, task):
    await client.post(
        f"/tasks/{task['id']}/breakdown",
        json={
            "subtasks": [{"name": "Sub 1", "task_type": "feature"}],
            "work_log_content": "Breakdown log",
            "author": "agent-2",
        },
    )
    resp = await client.get(f"/tasks/{task['id']}/work-log")
    entries = resp.json()
    assert len(entries) == 1
    assert entries[0]["operation"] == "breakdown"


@pytest.mark.asyncio
async def test_breakdown_empty_subtasks(client, task):
    resp = await client.post(
        f"/tasks/{task['id']}/breakdown",
        json={
            "subtasks": [],
            "work_log_content": "Empty",
        },
    )
    assert resp.status_code == 422


# --- Refine ---


@pytest.mark.asyncio
async def test_refine_task(client, task):
    # First flag it
    await client.post(
        f"/tasks/{task['id']}/flag-refinement",
        json={"refinement_notes": "Needs more detail"},
    )
    resp = await client.get(f"/tasks/{task['id']}")
    assert resp.json()["readiness"] == "needs_refinement"

    # Now refine
    resp = await client.post(
        f"/tasks/{task['id']}/refine",
        json={
            "description": "Refined description",
            "context": "New context",
            "work_log_content": "Refined the task",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["readiness"] == "needs_sizing"  # no points, no children


@pytest.mark.asyncio
async def test_refine_creates_work_log(client, task):
    await client.post(
        f"/tasks/{task['id']}/refine",
        json={"work_log_content": "Refine log"},
    )
    resp = await client.get(f"/tasks/{task['id']}/work-log")
    entries = resp.json()
    assert any(e["operation"] == "refinement" for e in entries)


# --- Flag Refinement ---


@pytest.mark.asyncio
async def test_flag_refinement(client, task):
    resp = await client.post(
        f"/tasks/{task['id']}/flag-refinement",
        json={"refinement_notes": "Missing acceptance criteria"},
    )
    assert resp.status_code == 200
    assert resp.json()["readiness"] == "needs_refinement"


# --- Complete ---


@pytest.mark.asyncio
async def test_complete_task(client, task):
    # Move to doing first
    await client.patch(f"/tasks/{task['id']}/status", json={"status": "doing"})

    resp = await client.post(
        f"/tasks/{task['id']}/complete",
        json={
            "work_log_content": "Implemented the feature",
            "author": "agent-1",
            "commits": [
                {
                    "commit_hash": "abc1234567890123456789012345678901234567",
                    "message": "feat: implement feature",
                    "author": "agent-1",
                    "committed_at": "2026-01-15T10:00:00Z",
                }
            ],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


@pytest.mark.asyncio
async def test_complete_task_creates_work_log_and_commits(client, task):
    await client.patch(f"/tasks/{task['id']}/status", json={"status": "doing"})
    await client.post(
        f"/tasks/{task['id']}/complete",
        json={
            "work_log_content": "Done",
            "commits": [
                {
                    "commit_hash": "abc1234567890123456789012345678901234567",
                    "message": "done",
                    "committed_at": "2026-01-15T10:00:00Z",
                }
            ],
        },
    )

    log_resp = await client.get(f"/tasks/{task['id']}/work-log")
    assert any(e["operation"] == "implementation" for e in log_resp.json())

    commits_resp = await client.get(f"/tasks/{task['id']}/commits")
    assert len(commits_resp.json()) == 1


@pytest.mark.asyncio
async def test_complete_task_children_must_be_terminal(client, project):
    parent = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "Parent", "task_type": "feature"},
    )
    parent_id = parent.json()["id"]

    await client.post(
        f"/tasks/{parent_id}/subtasks",
        json={"name": "Child", "task_type": "feature"},
    )

    await client.patch(f"/tasks/{parent_id}/status", json={"status": "doing"})

    resp = await client.post(
        f"/tasks/{parent_id}/complete",
        json={"work_log_content": "Trying to complete"},
    )
    assert resp.status_code == 422


# --- Work Log CRUD ---


@pytest.mark.asyncio
async def test_work_log_crud(client, task):
    resp = await client.post(
        f"/tasks/{task['id']}/work-log",
        json={"operation": "note", "content": "A note", "author": "human"},
    )
    assert resp.status_code == 201
    assert resp.json()["operation"] == "note"

    resp = await client.get(f"/tasks/{task['id']}/work-log")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# --- Commit CRUD ---


@pytest.mark.asyncio
async def test_commit_crud(client, task):
    resp = await client.post(
        f"/tasks/{task['id']}/commits",
        json={
            "commit_hash": "deadbeef12345678901234567890123456789012",
            "message": "fix: stuff",
            "committed_at": "2026-01-15T12:00:00Z",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["commit_hash"] == "deadbeef12345678901234567890123456789012"

    resp = await client.get(f"/tasks/{task['id']}/commits")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
