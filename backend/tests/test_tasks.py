import pytest


@pytest.fixture
async def project(client):
    resp = await client.post("/projects", json={"name": "Task Test Project"})
    return resp.json()


@pytest.mark.asyncio
async def test_create_task(client, project):
    resp = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "My Task", "task_type": "feature"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Task"
    assert data["task_type"] == "feature"
    assert data["parent_task_id"] is None
    assert data["position"] == 0
    assert data["readiness"] == "needs_sizing"


@pytest.mark.asyncio
async def test_create_subtask(client, project):
    parent_resp = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "Parent", "task_type": "feature"},
    )
    parent_id = parent_resp.json()["id"]

    resp = await client.post(
        f"/tasks/{parent_id}/subtasks",
        json={"name": "Child", "task_type": "feature"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["parent_task_id"] == parent_id
    assert data["project_id"] == project["id"]
    assert data["position"] == 0


@pytest.mark.asyncio
async def test_get_task(client, project):
    create_resp = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "Get Me", "task_type": "bug"},
    )
    task_id = create_resp.json()["id"]

    resp = await client.get(f"/tasks/{task_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Get Me"
    assert data["children_count"] == 0
    assert data["is_locked"] is False


@pytest.mark.asyncio
async def test_update_task(client, project):
    create_resp = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "Old", "task_type": "feature"},
    )
    task_id = create_resp.json()["id"]

    resp = await client.put(
        f"/tasks/{task_id}", json={"name": "Updated", "task_type": "bug"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"
    assert resp.json()["task_type"] == "bug"


@pytest.mark.asyncio
async def test_delete_task(client, project):
    create_resp = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "Delete Me", "task_type": "feature"},
    )
    task_id = create_resp.json()["id"]

    resp = await client.delete(f"/tasks/{task_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/tasks/{task_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_task_not_found(client):
    resp = await client.get("/tasks/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_auto_position(client, project):
    r1 = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "T1", "task_type": "feature"},
    )
    r2 = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "T2", "task_type": "feature"},
    )
    assert r1.json()["position"] == 0
    assert r2.json()["position"] == 1


@pytest.mark.asyncio
async def test_computed_fields_needs_refinement(client, project, session):
    """Task with needs_refinement=true should show needs_refinement readiness."""
    from app.models.task import Task

    task = Task(
        project_id=project["id"],
        name="Refine me",
        task_type="feature",
        needs_refinement=True,
        position=0,
    )
    session.add(task)
    await session.flush()

    resp = await client.get(f"/tasks/{task.id}")
    assert resp.json()["readiness"] == "needs_refinement"


@pytest.mark.asyncio
async def test_computed_fields_ready(client, project, session):
    """Leaf task with points set should be ready."""
    from app.models.task import Task

    task = Task(
        project_id=project["id"],
        name="Ready task",
        task_type="feature",
        points=3,
        position=0,
    )
    session.add(task)
    await session.flush()

    resp = await client.get(f"/tasks/{task.id}")
    data = resp.json()
    assert data["readiness"] == "ready"
    assert data["effective_points"] == 3
    assert data["rolled_up_points"] is None


@pytest.mark.asyncio
async def test_computed_fields_needs_breakdown(client, project, session):
    """Task with effective_points > 6 should need breakdown."""
    from app.models.task import Task

    task = Task(
        project_id=project["id"],
        name="Big task",
        task_type="feature",
        points=8,
        position=0,
    )
    session.add(task)
    await session.flush()

    resp = await client.get(f"/tasks/{task.id}")
    assert resp.json()["readiness"] == "needs_breakdown"


@pytest.mark.asyncio
async def test_computed_fields_rolled_up_points(client, project, session):
    """Parent with sized children should show rolled-up points."""
    from app.models.task import Task

    parent = Task(
        project_id=project["id"],
        name="Parent",
        task_type="feature",
        points=5,
        position=0,
    )
    session.add(parent)
    await session.flush()

    child1 = Task(
        project_id=project["id"],
        parent_task_id=parent.id,
        name="Child 1",
        task_type="feature",
        points=2,
        position=0,
    )
    child2 = Task(
        project_id=project["id"],
        parent_task_id=parent.id,
        name="Child 2",
        task_type="feature",
        points=3,
        position=1,
    )
    session.add_all([child1, child2])
    await session.flush()

    resp = await client.get(f"/tasks/{parent.id}")
    data = resp.json()
    assert data["rolled_up_points"] == 5
    assert data["effective_points"] == 5
    assert data["children_count"] == 2
    assert data["unsized_children"] == 0


@pytest.mark.asyncio
async def test_computed_fields_unsized_children(client, project, session):
    """Parent with unsized children should report unsized count and needs_breakdown."""
    from app.models.task import Task

    parent = Task(
        project_id=project["id"],
        name="Parent",
        task_type="feature",
        points=5,
        position=0,
    )
    session.add(parent)
    await session.flush()

    child1 = Task(
        project_id=project["id"],
        parent_task_id=parent.id,
        name="Sized",
        task_type="feature",
        points=2,
        position=0,
    )
    child2 = Task(
        project_id=project["id"],
        parent_task_id=parent.id,
        name="Unsized",
        task_type="feature",
        position=1,
    )
    session.add_all([child1, child2])
    await session.flush()

    resp = await client.get(f"/tasks/{parent.id}")
    data = resp.json()
    assert data["unsized_children"] == 1
    assert data["readiness"] == "needs_breakdown"


@pytest.mark.asyncio
async def test_blocked_by_children(client, project, session):
    """Parent with all-sized children (total <= 6) should be blocked_by_children."""
    from app.models.task import Task

    parent = Task(
        project_id=project["id"],
        name="Parent",
        task_type="feature",
        points=5,
        position=0,
    )
    session.add(parent)
    await session.flush()

    child = Task(
        project_id=project["id"],
        parent_task_id=parent.id,
        name="Child",
        task_type="feature",
        points=2,
        position=0,
    )
    session.add(child)
    await session.flush()

    resp = await client.get(f"/tasks/{parent.id}")
    assert resp.json()["readiness"] == "blocked_by_children"


@pytest.mark.asyncio
async def test_delete_task_cascades(client, project):
    parent_resp = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "Parent", "task_type": "feature"},
    )
    parent_id = parent_resp.json()["id"]

    child_resp = await client.post(
        f"/tasks/{parent_id}/subtasks",
        json={"name": "Child", "task_type": "feature"},
    )
    child_id = child_resp.json()["id"]

    await client.delete(f"/tasks/{parent_id}")

    resp = await client.get(f"/tasks/{child_id}")
    assert resp.status_code == 404


# --- Phase 3: Tree, Ancestry, Context, Status, Reorder ---


async def _create_hierarchy(client, project):
    """Create a 3-level hierarchy: root -> mid -> leaf."""
    root = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "Root", "task_type": "feature"},
    )
    root_id = root.json()["id"]

    mid = await client.post(
        f"/tasks/{root_id}/subtasks",
        json={"name": "Mid", "task_type": "feature"},
    )
    mid_id = mid.json()["id"]

    leaf = await client.post(
        f"/tasks/{mid_id}/subtasks",
        json={"name": "Leaf", "task_type": "feature"},
    )
    leaf_id = leaf.json()["id"]

    return root_id, mid_id, leaf_id


@pytest.mark.asyncio
async def test_tree(client, project):
    root_id, mid_id, leaf_id = await _create_hierarchy(client, project)

    resp = await client.get(f"/tasks/{root_id}/tree")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == root_id
    assert data["name"] == "Root"
    assert len(data["children"]) == 1
    mid_node = data["children"][0]
    assert mid_node["id"] == mid_id
    assert len(mid_node["children"]) == 1
    assert mid_node["children"][0]["id"] == leaf_id


@pytest.mark.asyncio
async def test_tree_not_found(client):
    resp = await client.get("/tasks/00000000-0000-0000-0000-000000000000/tree")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ancestry(client, project):
    root_id, mid_id, leaf_id = await _create_hierarchy(client, project)

    resp = await client.get(f"/tasks/{leaf_id}/ancestry")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["id"] == root_id
    assert data[1]["id"] == mid_id
    assert data[2]["id"] == leaf_id


@pytest.mark.asyncio
async def test_context_fresh(client, project, session):
    """Task with context_captured_at after all ancestors' updated_at is fresh."""
    from datetime import datetime, timezone

    from app.models.task import Task

    root_id, mid_id, leaf_id = await _create_hierarchy(client, project)

    # Set context_captured_at in the future to ensure freshness
    result = await session.execute(
        __import__("sqlalchemy").select(Task).where(Task.id.__eq__(leaf_id))
    )
    leaf_task = result.scalar_one()
    leaf_task.context_captured_at = datetime(2099, 1, 1, tzinfo=timezone.utc)
    await session.flush()

    resp = await client.get(f"/tasks/{leaf_id}/context")
    assert resp.status_code == 200
    data = resp.json()
    assert data["context_freshness"] == "fresh"
    assert data["stale_reasons"] == []
    assert data["commits"] is None  # not requested


@pytest.mark.asyncio
async def test_context_stale_never_captured(client, project):
    """Task without context_captured_at is stale."""
    root_id, _, _ = await _create_hierarchy(client, project)

    resp = await client.get(f"/tasks/{root_id}/context")
    assert resp.status_code == 200
    data = resp.json()
    assert data["context_freshness"] == "stale"


@pytest.mark.asyncio
async def test_context_include_commits(client, project):
    """include_commits=true returns commits list."""
    root_id, _, _ = await _create_hierarchy(client, project)

    resp = await client.get(f"/tasks/{root_id}/context?include_commits=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["commits"] is not None
    assert isinstance(data["commits"], list)


@pytest.mark.asyncio
async def test_status_valid_transitions(client, project):
    """Standard flow: todo -> doing -> done."""
    resp = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "Flow Task", "task_type": "feature"},
    )
    task_id = resp.json()["id"]

    # todo -> doing
    resp = await client.patch(f"/tasks/{task_id}/status", json={"status": "doing"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "doing"

    # doing -> done (leaf, no children)
    resp = await client.patch(f"/tasks/{task_id}/status", json={"status": "done"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


@pytest.mark.asyncio
async def test_status_invalid_transition(client, project):
    """todo -> done is not valid."""
    resp = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "Bad Flow", "task_type": "feature"},
    )
    task_id = resp.json()["id"]

    resp = await client.patch(f"/tasks/{task_id}/status", json={"status": "done"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_status_parent_cannot_complete_with_active_children(client, project):
    """Parent can't go to done if children are still active."""
    root_id, mid_id, leaf_id = await _create_hierarchy(client, project)

    # Move root to doing
    await client.patch(f"/tasks/{root_id}/status", json={"status": "doing"})

    # Try to complete root — children are still todo
    resp = await client.patch(f"/tasks/{root_id}/status", json={"status": "done"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_status_parent_reopens_when_child_reopens(client, project):
    """When a done child is reopened, done parent should reopen to todo."""
    resp = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "Parent", "task_type": "feature"},
    )
    parent_id = resp.json()["id"]

    child_resp = await client.post(
        f"/tasks/{parent_id}/subtasks",
        json={"name": "Child", "task_type": "feature"},
    )
    child_id = child_resp.json()["id"]

    # Complete child: todo -> doing -> done
    await client.patch(f"/tasks/{child_id}/status", json={"status": "doing"})
    await client.patch(f"/tasks/{child_id}/status", json={"status": "done"})

    # Complete parent: todo -> doing -> done
    await client.patch(f"/tasks/{parent_id}/status", json={"status": "doing"})
    await client.patch(f"/tasks/{parent_id}/status", json={"status": "done"})

    # Reopen child
    await client.patch(f"/tasks/{child_id}/status", json={"status": "todo"})

    # Parent should have reopened
    resp = await client.get(f"/tasks/{parent_id}")
    assert resp.json()["status"] == "todo"


@pytest.mark.asyncio
async def test_status_wont_do_from_any(client, project):
    """Any task can be moved to wont_do."""
    resp = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "Cancel Me", "task_type": "feature"},
    )
    task_id = resp.json()["id"]

    resp = await client.patch(f"/tasks/{task_id}/status", json={"status": "wont_do"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "wont_do"


@pytest.mark.asyncio
async def test_reorder(client, project):
    """Reordering a task shifts siblings."""
    t1 = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "T1", "task_type": "feature"},
    )
    await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "T2", "task_type": "feature"},
    )
    t3 = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"name": "T3", "task_type": "feature"},
    )
    t3_id = t3.json()["id"]
    t1_id = t1.json()["id"]

    # Move T3 to position 0
    resp = await client.patch(f"/tasks/{t3_id}/reorder", json={"position": 0})
    assert resp.status_code == 200
    assert resp.json()["position"] == 0

    # T1 should have shifted to position 1
    resp = await client.get(f"/tasks/{t1_id}")
    assert resp.json()["position"] == 1
