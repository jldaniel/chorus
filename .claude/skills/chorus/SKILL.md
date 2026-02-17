---
name: chorus
description: Interact with the Chorus project management API for task creation, sizing, breakdown, and implementation workflows.
---

# Chorus — Agent Skill

## Overview

Chorus is a hierarchical task management system designed for AI coding agents. Rather than estimating tasks in time, Chorus scores complexity across five dimensions calibrated to how LLMs actually fail, then uses those scores to decide whether a task is ready for implementation or needs further breakdown.

**Task pipeline:** Creation → Sizing → Breakdown (if needed) → Implementation

**Base URL:** `http://localhost:8000` (configurable)

All requests and responses use JSON. Dates are ISO 8601 UTC. IDs are UUIDs.

---

## API Reference

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns service health status |

---

### Projects

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/projects` | 201 | Create a project |
| GET | `/projects` | 200 | List all projects |
| GET | `/projects/{project_id}` | 200 | Project detail with task counts and point totals |
| PUT | `/projects/{project_id}` | 200 | Update project name/description |
| DELETE | `/projects/{project_id}` | 204 | Delete project and all tasks |
| GET | `/projects/{project_id}/export` | 200 | Full project snapshot with all tasks, work logs, and commits |
| GET | `/projects/{project_id}/tasks` | 200 | Top-level tasks for a project |

**Create project:**
```json
POST /projects
{ "name": "My Project", "description": "Optional description" }
```

---

### Tasks

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/projects/{project_id}/tasks` | 201 | Create a top-level task |
| POST | `/tasks/{task_id}/subtasks` | 201 | Create a subtask under a parent |
| GET | `/tasks/{task_id}` | 200 | Get task with computed fields |
| PUT | `/tasks/{task_id}` | 200 | Update task name/description/context/type |
| DELETE | `/tasks/{task_id}` | 204 | Delete task and all descendants |
| GET | `/tasks/{task_id}/tree` | 200 | Full subtree (recursive) |
| GET | `/tasks/{task_id}/ancestry` | 200 | Chain from root to this task |
| GET | `/tasks/{task_id}/context` | 200 | Synthesized context with freshness metadata |
| PATCH | `/tasks/{task_id}/status` | 200 | Explicit status transition |
| PATCH | `/tasks/{task_id}/reorder` | 200 | Change position among siblings |

**Create task:**
```json
POST /projects/{project_id}/tasks
{
  "name": "Add user authentication",
  "description": "Implement OAuth2 login flow",
  "task_type": "feature"
}
```
`task_type` must be one of: `feature`, `bug`, `tech_debt`.

**Task response fields:**
- `id`, `project_id`, `parent_task_id` — identity
- `name`, `description`, `context` — content
- `task_type`, `status` — classification (`status`: `todo` | `doing` | `done` | `wont_do`)
- `points` — direct complexity score (set by sizing)
- `effective_points` — canonical size: `rolled_up_points` if children are sized, else `points`
- `rolled_up_points` — recursive sum of descendant effective sizes
- `unsized_children` — count of children without points
- `readiness` — computed: `needs_refinement` | `needs_sizing` | `needs_breakdown` | `blocked_by_children` | `ready`
- `children_count`, `is_locked`, `position`, `created_at`, `updated_at`

**Context endpoint** (`GET /tasks/{task_id}/context?include_commits=true`):

Returns `task`, `ancestors` (root→task chain with name/description/context), `work_log`, optionally `commits`, plus `context_freshness` (`fresh`/`stale`) and `stale_reasons`.

---

### Locks

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/tasks/{task_id}/lock` | 201 | Acquire exclusive lock |
| PATCH | `/tasks/{task_id}/lock/heartbeat?caller_label=X` | 200 | Extend lock TTL |
| DELETE | `/tasks/{task_id}/lock?caller_label=X` | 204 | Release lock |

**Lock TTLs by purpose:**

| Purpose | TTL |
|---------|-----|
| `sizing` | 15 minutes |
| `breakdown` | 30 minutes |
| `refinement` | 30 minutes |
| `implementation` | 1 hour |

**Lock preconditions (enforced at acquire time):**

| Purpose | Requirement |
|---------|-------------|
| `sizing` | Task must not already be sized (`points` is null) |
| `breakdown` | Task must be sized AND (score > 6 OR has unsized children) |
| `refinement` | No precondition |
| `implementation` | Task readiness must be `ready` |

**Acquire lock:**
```json
POST /tasks/{task_id}/lock
{
  "caller_label": "agent-claude-1",
  "lock_purpose": "sizing"
}
```
Response:
```json
{
  "id": "...",
  "task_id": "...",
  "caller_label": "agent-claude-1",
  "lock_purpose": "sizing",
  "acquired_at": "2026-02-16T10:00:00Z",
  "last_heartbeat_at": null,
  "expires_at": "2026-02-16T10:15:00Z"
}
```

Errors: `409 LOCK_CONFLICT` if already locked; `422 INVALID_READINESS_STATE` if precondition fails.

---

### Atomic Operations

All atomic operations require a held lock on the task. Include `work_log_content` in every request — it is written transactionally with the operation.

Use `Idempotency-Key` header on size, breakdown, refine, and complete to prevent duplicate processing. Keys expire after 24 hours.

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/tasks/{task_id}/size` | 200 | Submit complexity scoring |
| POST | `/tasks/{task_id}/breakdown` | 200 | Decompose into subtasks |
| POST | `/tasks/{task_id}/refine` | 200 | Update description/context, clear refinement flag |
| POST | `/tasks/{task_id}/flag-refinement` | 200 | Flag task as needing refinement |
| POST | `/tasks/{task_id}/complete` | 200 | Mark done, write log, attach commits |

**Size a task:**
```json
POST /tasks/{task_id}/size
Idempotency-Key: size-abc123

{
  "scope_clarity":            { "score": 1, "reasoning": "Requirements mostly clear, minor ambiguity on error states" },
  "decision_points":          { "score": 0, "reasoning": "Straightforward implementation, no design choices" },
  "context_window_demand":    { "score": 1, "reasoning": "Touches 3 files with moderate cross-referencing" },
  "verification_complexity":  { "score": 0, "reasoning": "Existing test patterns cover this" },
  "domain_specificity":       { "score": 1, "reasoning": "Standard REST patterns, well-documented" },
  "confidence": 4,
  "scored_by": "agent-claude-1",
  "work_log_content": "Sized task at 3 points. Low complexity, standard CRUD pattern.",
  "author": "agent-claude-1"
}
```
Sets `points` to the sum of all dimension scores (0–10).

**Break down a task:**
```json
POST /tasks/{task_id}/breakdown
Idempotency-Key: bkdn-abc123

{
  "subtasks": [
    { "name": "Design database schema", "task_type": "feature", "description": "..." },
    { "name": "Implement API endpoints", "task_type": "feature", "description": "..." },
    { "name": "Write integration tests", "task_type": "feature", "description": "..." }
  ],
  "parent_description_update": "Updated to reflect decomposition",
  "work_log_content": "Broke task into 3 subtasks covering schema, API, and tests.",
  "author": "agent-claude-1"
}
```

**Complete a task:**
```json
POST /tasks/{task_id}/complete
Idempotency-Key: done-abc123

{
  "work_log_content": "Implemented OAuth2 login flow with Google provider. All tests passing.",
  "author": "agent-claude-1",
  "commits": [
    {
      "commit_hash": "a1b2c3d",
      "message": "feat: add OAuth2 login flow",
      "author": "agent-claude-1",
      "committed_at": "2026-02-16T12:30:00Z"
    }
  ]
}
```

---

### Work Log & Commits

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/tasks/{task_id}/work-log` | 201 | Append a standalone work log entry |
| GET | `/tasks/{task_id}/work-log` | 200 | Get chronological work log |
| POST | `/tasks/{task_id}/commits` | 201 | Record a standalone git commit |
| GET | `/tasks/{task_id}/commits` | 200 | Get all commits for a task |

Work log `operation` values: `sizing`, `breakdown`, `refinement`, `implementation`, `note`.

---

### Discovery & Queue

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/projects/{project_id}/backlog` | 200 | Ready + todo tasks (implementation queue) |
| GET | `/projects/{project_id}/in-progress` | 200 | Doing tasks with lock info |
| GET | `/projects/{project_id}/needs-refinement` | 200 | Flagged or low-confidence tasks |
| GET | `/tasks/available?operation=X` | 200 | Unlocked tasks eligible for an operation |

**Available tasks** accepts query parameters: `operation` (required: `sizing` | `breakdown` | `implementation`), `project_id`, `task_type`, `min_points`, `max_points`, `limit`, `offset`.

---

## Sizing Rubric

### Dimensions (each scored 0–2)

| Dimension | 0 | 1 | 2 |
|-----------|---|---|---|
| **Scope Clarity** | Requirements explicit with clear acceptance criteria | Mostly clear, minor ambiguity | Vague, subjective, or open-ended |
| **Decision Points** | Zero or one trivial decision | A few decisions with constrained options | Many sequential decisions requiring judgment |
| **Context Window Demand** | Single file, self-contained | 2–4 files, moderate cross-referencing | Many files, multiple systems, large context |
| **Verification Complexity** | Automated tests or obvious correctness | Testable but needs new test cases | Subjective verification, no clear success criteria |
| **Domain Specificity** | Standard patterns, well-documented | Some specialized knowledge, good references | Novel domain, sparse docs, expert knowledge needed |

### Scoring rules

| Condition | Action |
|-----------|--------|
| Total ≤ 6 | Task is ready for implementation |
| Total ≥ 7 | Task must be broken down before implementation |
| Confidence ≤ 2 | Flag for human review or further refinement |

Confidence is 0–5 (0–2 = low/uncertain, 3–5 = sufficient).

---

## Workflow Patterns

### Sizing workflow

1. `GET /tasks/available?operation=sizing` — find an unsized task
2. `POST /tasks/{id}/lock` — acquire lock with `lock_purpose: "sizing"`
3. `GET /tasks/{id}/context` — read task context, ancestors, and work log
4. Evaluate the task against the five sizing dimensions
5. `POST /tasks/{id}/size` — submit scores with `work_log_content`
6. `DELETE /tasks/{id}/lock?caller_label=X` — release lock

### Breakdown workflow

1. `GET /tasks/available?operation=breakdown` — find a task needing breakdown
2. `POST /tasks/{id}/lock` — acquire lock with `lock_purpose: "breakdown"`
3. `GET /tasks/{id}/context` — read full context
4. Design subtasks that decompose the work into implementable pieces
5. `POST /tasks/{id}/breakdown` — submit subtasks with `work_log_content`
6. `DELETE /tasks/{id}/lock?caller_label=X` — release lock

### Implementation workflow

1. `GET /tasks/available?operation=implementation` — find a ready task
2. `POST /tasks/{id}/lock` — acquire lock with `lock_purpose: "implementation"`
3. `GET /tasks/{id}/context` — read full context including ancestry
4. Do the coding work
5. Send heartbeats (`PATCH /tasks/{id}/lock/heartbeat?caller_label=X`) during long operations
6. `POST /tasks/{id}/complete` — mark done with work log and commits
7. `DELETE /tasks/{id}/lock?caller_label=X` — release lock

### Refinement workflow

1. If a task is unclear: `POST /tasks/{id}/flag-refinement` with `refinement_notes`
2. To refine: `POST /tasks/{id}/lock` with `lock_purpose: "refinement"`
3. `GET /tasks/{id}/context` — read context
4. `POST /tasks/{id}/refine` — update description/context with `work_log_content`
5. `DELETE /tasks/{id}/lock?caller_label=X` — release lock

---

## Conventions

### Work logs

Every atomic operation (`size`, `breakdown`, `refine`, `complete`) requires `work_log_content` explaining your reasoning. This creates an auditable trail of decisions. For standalone notes, use `POST /tasks/{id}/work-log` with operation `note`.

### Commit tracking

Record git commits via the `complete` endpoint (preferred — atomic with status change) or standalone via `POST /tasks/{id}/commits`. Include `commit_hash`, `message`, `author`, and `committed_at`.

### Lock hygiene

- Always release locks when done, even on failure.
- Send heartbeats during long operations to prevent TTL expiry.
- If your lock expires, stop work and re-acquire before continuing.
- Handle `409 LOCK_CONFLICT` by backing off — another agent holds the lock.

### Scope discipline

- Only modify the task you hold a lock on.
- Work on one task at a time.
- If you discover new work during implementation, create a new task rather than expanding scope.

### Error handling

| Status | Meaning | Action |
|--------|---------|--------|
| 409 | Lock conflict or concurrent modification | Back off with exponential delay, re-query available tasks |
| 422 | Business rule violation (wrong state, invalid transition) | Log the reason, release your lock, move on |
| 500 | Server error | Retry with bounded backoff and jitter (max 3 attempts) |

### Idempotency keys

Use the `Idempotency-Key` header on `size`, `breakdown`, `refine`, and `complete` requests to safely retry without duplicate side effects. Keys are scoped per operation and expire after 24 hours. Use a unique value per logical attempt (e.g., `size-{task_id}-{timestamp}`).

### Error response format

All errors follow this structure:
```json
{
  "error": {
    "code": "LOCK_CONFLICT",
    "message": "Task is already locked by another caller",
    "details": {},
    "request_id": "..."
  }
}
```

Error codes: `LOCK_CONFLICT`, `INVALID_READINESS_STATE`, `INVALID_STATUS_TRANSITION`, `CONTEXT_STALE`, `VALIDATION_ERROR`.
