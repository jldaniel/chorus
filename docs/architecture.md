# Chorus

**Agent-Native Project Management System**

## Table of Contents

- [Executive Summary](#executive-summary)
- [Core Concepts](#core-concepts)
- [Complexity Scoring Framework](#complexity-scoring-framework)
- [Agent Interaction Model](#agent-interaction-model)
- [Task Lifecycle](#task-lifecycle)
- [Data Model](#data-model)
- [System Architecture](#system-architecture)
- [Deployment Trust Model](#deployment-trust-model)
- [API Design](#api-design)
- [Agent Skill Design](#agent-skill-design)
- [Non-Functional Requirements](#non-functional-requirements)
- [Frontend Design](#frontend-design)
- [Project Structure](#project-structure)

## Executive Summary

Chorus is a project management system intended for working with AI agents on more complicated tasks. The project focuses on letting agents help break down and define tasks to then work on those tasks when sufficiently defined. The system provides hierarchical task management with infinite nesting, a complexity scoring framework, and basic locking for multi-agent concurrency. Tasks flow through a pipeline of atomic operations — sizing, breakdown, refinement, and implementation — each performed by a single agent in a single session.

Chorus exposes a REST API backed by PostgreSQL, agent skill files that teach coding agents like Claude Code and Cursor how to interact with the system, and a React frontend for human oversight and project management.

## Core Concepts

### Hierarchical Task Structure

Tasks are the central entity in Chorus. Every task can have any number of subtasks, forming an infinitely nestable hierarchy where each task references its parent. This enables progressive decomposition: a high-level feature like "Implement Frontend" can be broken into pages, then components, then individual implementation units — each small enough for an agent to execute in a single session.

Each task carries two text fields that serve distinct purposes. The **description** defines what the task is: its goal, requirements, and acceptance criteria. The **context** field explains how the task fits into the larger picture, capturing relevant information from parent tasks and cross-cutting concerns. When an agent breaks down a parent task, it writes context on each child summarizing the relevant parts of the parent, effectively pre-computing the context traversal so implementation agents have everything they need without walking the tree.

### Task Types

Every task is classified as one of three types:

| Type | Description | Examples |
|---|---|---|
| Feature | New functionality or capability | Add user authentication, build dashboard view |
| Bug | Defect in existing functionality | Fix login timeout, correct calculation error |
| Tech Debt | Internal improvement with no user-visible change | Refactor database layer, add test coverage |

### Task Status

Tasks have a simple four-state lifecycle. Status tracks execution state only — it does not encode whether a task has been sized, reviewed, or is ready for work. That information is derived from the task's actual data.

| Status | Meaning |
|---|---|
| To Do | Task exists but work has not started |
| Doing | An agent is actively working on an operation (sizing, breakdown, refinement, or implementation) |
| Done | Implementation is complete |
| Won't Do | Task has been cancelled or determined unnecessary |

### Task Readiness

The system computes readiness from task data using deterministic rules. This is evaluated in order:

1. If `needs_refinement = true`: **Needs Refinement**
2. Else if `points` is null: **Needs Sizing**
3. Else if task has children and `unsized_children > 0`: **Needs Breakdown** (breakdown in progress)
4. Else if `effective_points > 6`: **Needs Breakdown**
5. Else if task has children: **Blocked by Children** (parent is coordination-only, not directly implementable)
6. Else: **Ready**

Computed states:

| Computed State | Condition | What It Means |
|---|---|---|
| Needs Refinement | `needs_refinement` is true | Task definition is insufficient. `refinement_notes` explains what is missing. |
| Needs Sizing | `points` is null | Task has not been assessed for complexity. |
| Needs Breakdown | `effective_points > 6`, or children exist but are not fully sized | Task is too complex or decomposition is incomplete. |
| Blocked by Children | Children exist and `effective_points <= 6` | Parent is not directly implementable; execute leaf tasks. |
| Ready | Leaf task with `effective_points <= 6` and no higher-priority blockers | Task is implementation-ready. |

There is no `needs_breakdown` field. Breakdown eligibility is purely computed from sizing and child completeness data.

The `needs_refinement` boolean is the only stored readiness flag because refinement is a judgment call that cannot be inferred from structure alone.

### Projects

Projects are organizational containers for tasks. Each project has a name and description that provides high-level context about the project's goals, constraints, and architecture. Top-level tasks belong to a project, and all descendants inherit that project association through the hierarchy.

### Parent-Child Execution Rules

Once a task has children, it becomes a coordination node and is not directly implementable. Implementation is leaf-only.

Parent status is still explicit (not auto-derived by a background job), but transitions are constrained:

- Parent can move to `done` only when all descendants are in terminal states (`done` or `wont_do`) and at least one descendant is `done`.
- Parent should move to `doing` only for parent-scoped operations (for example refinement or breakdown), not coding implementation.
- If any child is reopened from `done` to `todo/doing`, the parent must be reopened to `todo`.

## Complexity Scoring Framework

Traditional task estimation is based on human time, which is irrelevant for AI agents. An agent might complete routine work in seconds but fail completely on a task a human finds straightforward. Chorus uses a five-dimension complexity scoring system calibrated to how LLMs actually fail.

### Scoring Dimensions

Each dimension is scored 0–2, for a maximum total of 10 points. The dimensions capture the specific factors that determine whether an AI agent can successfully complete a task.

| Dimension | Score 0 | Score 1 | Score 2 |
|---|---|---|---|
| Scope Clarity | Requirements are explicit with clear acceptance criteria | Requirements are mostly clear with minor ambiguity | Requirements are vague, subjective, or open-ended |
| Decision Points | Zero or one trivial decision | A few decisions with constrained options | Many sequential decisions requiring judgment |
| Context Window Demand | Single file, self-contained change | 2–4 files, moderate cross-referencing | Many files, multiple systems, large context required |
| Verification Complexity | Automated tests or obvious correctness | Testable but requires writing new test cases | Subjective verification or no clear success criteria |
| Domain Specificity | Standard patterns, well-documented domain | Some specialized knowledge, good references available | Novel domain, sparse documentation, expert knowledge required |

### Scoring Rules and Thresholds

| Condition | Action |
|---|---|
| Total <= 6 | Task is appropriately sized for agent execution. Mark as sized and move to ready. |
| Total >= 7 | Task is too complex. Must be broken down into subtasks before implementation. |
| Confidence <= 2 | Sizing agent is uncertain about its assessment. Flag for human review or further refinement before proceeding. |

### Sizing Data Model

The total score is stored as a top-level integer field (`points`) for efficient querying. The full dimensional breakdown, reasoning, risk factors, and breakdown suggestions are stored as a JSON object (`points_breakdown`) for detailed inspection. A separate `sizing_confidence` integer enables filtering on confidence without parsing JSON.

The `points_breakdown` JSON structure:

```json
{
  "scope_clarity": { "score": 1, "reasoning": "..." },
  "decision_points": { "score": 2, "reasoning": "..." },
  "context_window_demand": { "score": 1, "reasoning": "..." },
  "verification_complexity": { "score": 0, "reasoning": "..." },
  "domain_specificity": { "score": 1, "reasoning": "..." },
  "total": 5,
  "confidence": 4,
  "risk_factors": ["Cache invalidation edge cases"],
  "breakdown_suggestions": null,
  "scored_by": "agent-abc",
  "scored_at": "2026-02-10T14:30:00Z"
}
```

### Point Rollup (Replacement Model)

A task's effective size follows a replacement model. If a task has subtasks with sizes assigned, the effective size is the sum of the children's effective sizes (computed recursively). The parent's own `points` value is preserved as the original estimate but is superseded by the rollup. This means the breakdown is the source of truth for sizing once it exists.

The API returns three related values for every task with children:

| Field | Meaning |
|---|---|
| `points` | The direct estimate assigned to this task (the original assessment) |
| `rolled_up_points` | The recursive sum of all descendant effective sizes. Null if no children have been sized. |
| `effective_points` | `rolled_up_points` if children are sized, otherwise `points`. This is the canonical size. |
| `unsized_children` | Count of child tasks without sizes. A nonzero value signals that the breakdown is incomplete. |

## Agent Interaction Model

### Atomic Operations

Every interaction an agent has with a task is an atomic operation: a single, self-contained action with clear inputs, outputs, and exit conditions. An agent takes a task, performs exactly one type of operation, logs what it did, and releases the task. This keeps context contained, enables clean handoffs, and allows a human or PM agent to review between each step.

| Operation | Purpose | Input | Output |
|---|---|---|---|
| Sizing | Assess task complexity | Task with description | `points_breakdown` populated, readiness updated |
| Breakdown | Decompose a complex task | Sized task with total >= 7 | Child tasks created with descriptions and context |
| Refinement | Improve task definition | Task flagged for refinement | Updated description, context, or acceptance criteria |
| Implementation | Execute the coding work | Task in ready state | Code commits, status change to done |

### Task Locking

Chorus uses pessimistic locking to ensure only one agent operates on a task at a time. When an agent takes a task, it acquires an exclusive lock specifying the operation purpose and a `caller_label` identifying who is holding the lock. Other agents see the task as locked and skip it. Locks have a TTL-based expiration computed from `MAX(acquired_at, last_heartbeat_at) + TTL`. The TTL is set automatically based on the lock purpose.

TTL per lock purpose:

| Lock Purpose | TTL |
|---|---|
| sizing | 15 minutes |
| breakdown | 30 minutes |
| refinement | 30 minutes |
| implementation | 1 hour |

When a lock is acquired, the server computes `expires_at` from the purpose-based TTL. If an existing lock has expired at the time a new acquisition is attempted, the server releases the stale lock and grants the new request. A background cleanup task also periodically sweeps expired locks. Anyone can force-release any lock via `DELETE /tasks/{id}/lock?force=true`.

For long-running operations, lock holders can send heartbeats via `PATCH /tasks/{id}/lock/heartbeat` to extend the lock. Each heartbeat resets `last_heartbeat_at` and recomputes `expires_at` from that timestamp plus the purpose-based TTL.

The locking protocol:

| Step | Action | Details |
|---|---|---|
| 1 | Acquire | Agent requests a lock with a purpose (sizing, breakdown, refinement, implementation) and a `caller_label`. The server validates that the task is in an appropriate state for the requested operation and that no unexpired lock is held. If an expired lock exists, it is released automatically. |
| 2 | Operate | Agent performs its atomic operation. The lock purpose constrains what operations are valid. |
| 3 | Log | Agent writes a work log entry describing what it did, decisions it made, and any issues encountered. |
| 4 | Release | Agent explicitly releases the lock. If the agent crashes, the TTL expiry handles cleanup. |

Lock validation rules enforced by the API:

| Lock Purpose | Precondition |
|---|---|
| sizing | Task must not already be sized (`points` is null) |
| breakdown | Task must be sized and either `effective_points > 6` or have children with `unsized_children > 0` |
| refinement | No specific precondition — any task can be refined |
| implementation | Task must be in computed `Ready` state (leaf-only, no blockers) |

### Work Logs

Work logs are the continuity mechanism between agents. Since each operation is atomic and agents have no memory between sessions, the work log provides the full history of what has been done to a task. Every atomic operation must leave a work log entry. When a new agent picks up a task, it reads the description (the spec), the sizing breakdown (the complexity assessment), and the work log (the operational history) to get complete context.

Work log entries are immutable and append-only. Each entry records the author, the operation type, a timestamp, and freeform content describing what was done.

Every operation log entry should include:

- Decision made
- Changes applied
- Blockers or risks
- Next handoff note

### Commit Tracking

Commits are tracked as metadata on tasks, decoupled from task status. An agent can work on a task, make several commits, and release the lock without completing the task. The next agent sees the commit history and can pick up where the previous agent left off. Each commit records the hash, message, the author that made it, and a timestamp.

### Context Traversal

Agents need to understand how their task fits into the broader project. The API provides endpoints for traversing the task hierarchy: ancestry (the chain from a task up to the project root) and tree (a task and all its descendants). A dedicated context endpoint synthesizes the full picture — the task's description, all ancestor descriptions, and the work log — into a single response optimized for an LLM's context window. An optional `?include_commits=true` parameter adds commit history to the response.

The context endpoint also returns freshness metadata:

- `context_captured_at`: when this task's context field was last authored or confirmed
- `context_freshness`: `fresh` or `stale`
- `stale_reasons`: list of ancestor tasks updated after `context_captured_at`

Freshness is evaluated at read time. Stale context is warning-level in v1 (does not block lock acquisition), but agents should log when proceeding with stale context.

### Parent-Child Consistency

When breaking down tasks, agents may arrive at conclusions that diverge from the parent task's original description. Chorus addresses this with two conventions. First, parent descriptions should be summaries of goals and scope, not implementation details — the subtasks are where specifics live. Second, when a breakdown changes the parent's intent, the agent updates the parent description and explicitly documents the change in the work log. The context field on child tasks captures relevant parent information at the time of breakdown, and the system can flag when a parent has been modified after its children's context was written.

## Task Lifecycle

A task moves through a pipeline of atomic operations. The pipeline is not a rigid state machine — tasks can be refined at any point and sizing can be revised.

### Standard Flow

The typical lifecycle of a task from creation to completion:

| Phase | Actor | What Happens |
|---|---|---|
| 1. Creation | Human / PM Agent | A task is created with a name and description. May include a gut-feel size estimate. The task enters the system as To Do with computed readiness of Needs Sizing (if unsized) or Needs Breakdown (if sized > 6). |
| 2. Sizing | Sizing Agent | Agent locks the task for sizing. Reads the description. Scores each of the five complexity dimensions with reasoning. If total <= 6, the task is marked as sized. If total >= 7, it is flagged for breakdown. Agent releases the lock. |
| 3. Breakdown | Breakdown Agent | For tasks scoring >= 7: agent locks the parent, creates subtasks with descriptions and context, optionally updates the parent description, logs decisions. Each subtask starts the pipeline from the beginning. |
| 4. Implementation | Implementation Agent | Agent locks a ready leaf task for implementation. Reads the description, context, sizing, and work log. Performs the coding work. Makes commits (tracked as metadata). Completes task via atomic completion endpoint that writes work log and marks Done together. Releases the lock. |

### Flexible Workflows

The pipeline is not strictly linear. A task can be refined at any point — before or after sizing. A human can provide an initial gut-feel size, have the task refined for better definition, and then have it re-sized with more accurate scoring. Sizing can be revised if new information emerges. What matters is that the data on the task accurately reflects its current state, and the computed readiness derives the correct next action from that data.

## Data Model

### Entity Relationship Overview

The data model consists of five entities. Projects contain Tasks in a hierarchy. Tasks are operated on via Locks. Work done on tasks is recorded in WorkLogEntries and TaskCommits.

### Projects

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | Unique identifier |
| name | VARCHAR(255) | NOT NULL | Project name |
| description | TEXT | NULLABLE | Project goals, architecture, constraints |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW | Last modification timestamp |

### Tasks

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | Unique identifier |
| project_id | UUID | FK -> Projects, NOT NULL | Owning project |
| parent_task_id | UUID | FK -> Tasks, NULLABLE | Parent task. Null = top-level task |
| name | VARCHAR(500) | NOT NULL | Task name / title |
| description | TEXT | NULLABLE | The spec: goal, requirements, acceptance criteria |
| context | TEXT | NULLABLE | How this task fits in the larger picture |
| task_type | ENUM | NOT NULL | feature, bug, tech_debt |
| status | ENUM | NOT NULL, DEFAULT todo | todo, doing, done, wont_do |
| points | INTEGER | NULLABLE | Total complexity score (0-10) |
| points_breakdown | JSONB | NULLABLE | Full dimensional scoring with reasoning |
| sizing_confidence | INTEGER | NULLABLE | Agent confidence in sizing (0-5) |
| needs_refinement | BOOLEAN | NOT NULL, DEFAULT FALSE | Flag for insufficient definition |
| refinement_notes | TEXT | NULLABLE | Explanation of what needs refinement |
| context_captured_at | TIMESTAMP | NULLABLE | When `context` was last authored or explicitly confirmed |
| position | INTEGER | NOT NULL, DEFAULT 0 | Ordering among siblings |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW | Last modification timestamp |

### Task Locks

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | Unique identifier |
| task_id | UUID | FK -> Tasks, UNIQUE | One lock per task |
| caller_label | VARCHAR(255) | NOT NULL | Freeform label identifying who holds the lock |
| lock_purpose | ENUM | NOT NULL | sizing, breakdown, refinement, implementation |
| acquired_at | TIMESTAMP | NOT NULL, DEFAULT NOW | When the lock was acquired |
| last_heartbeat_at | TIMESTAMP | NULLABLE | Last heartbeat timestamp. Null if no heartbeat sent. |
| expires_at | TIMESTAMP | NOT NULL | Auto-release time: MAX(acquired_at, last_heartbeat_at) + TTL |

### Task Commits

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | Unique identifier |
| task_id | UUID | FK -> Tasks, NOT NULL | Associated task |
| author | VARCHAR(255) | NULLABLE | Who made the commit |
| commit_hash | VARCHAR(40) | NOT NULL | Git commit SHA |
| message | TEXT | NULLABLE | Commit message |
| committed_at | TIMESTAMP | NOT NULL | When the commit was made |

### Work Log Entries

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | Unique identifier |
| task_id | UUID | FK -> Tasks, NOT NULL | Associated task |
| author | VARCHAR(255) | NULLABLE | Who created the entry |
| operation | ENUM | NOT NULL | sizing, breakdown, refinement, implementation, note |
| content | TEXT | NOT NULL | What was done, decisions made, issues encountered |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW | Entry timestamp |

### Key Indexes

| Index | Table | Columns | Purpose |
|---|---|---|---|
| idx_tasks_project | Tasks | project_id | Filter tasks by project |
| idx_tasks_parent | Tasks | parent_task_id | Tree traversal, find children |
| idx_tasks_status | Tasks | status | Filter by execution state |
| idx_tasks_points | Tasks | points | Find unsized or oversized tasks |
| idx_locks_task | TaskLocks | task_id (UNIQUE) | Lock lookup and enforcement |
| idx_locks_expiry | TaskLocks | expires_at | Cleanup expired locks |
| idx_commits_task | TaskCommits | task_id | Find commits for a task |
| idx_worklog_task | WorkLogEntries | task_id, created_at | Chronological work history |

### Data Integrity Constraints

Invariants are enforced in both the database and service layer:

- Parent/child must share `project_id` (enforced on create/update).
- Cycles in the task tree are disallowed (validated before parent change).
- `points` must be between 0 and 10.
- `sizing_confidence` must be between 0 and 5.
- Sibling ordering uses unique `(parent_task_id, position)` to keep deterministic ordering.
- Timestamps are stored in UTC and serialized as ISO-8601.

## System Architecture

### Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Database | PostgreSQL 16 | ACID transactions for locking, concurrent multi-agent writes, JSONB for flexible scoring data, recursive CTEs for tree operations. Runs in Docker for local development. |
| ORM | SQLAlchemy (async) | Database abstraction with AsyncSession for non-blocking concurrent request handling. Alembic for schema migrations. |
| Backend API | FastAPI | Automatic OpenAPI spec generation (agents can read the spec), async support, Pydantic validation for request/response schemas, dependency injection. |
| Frontend | React + Vite | Lightweight SPA. No SSR needed (this is a dashboard app, not a content site). Fast dev experience. Tree view as the primary interaction surface. |
| Agent Integration | Skill Files | Markdown skill files that teach coding agents (Claude Code, Cursor) how to interact with the REST API directly. Encodes workflow patterns, sizing rubric, and API usage. No intermediary process required. |
| Containerization | Docker Compose | Single docker-compose.yml runs Postgres, the API, and the frontend. Skill files live in the repository alongside the code. |

### Component Architecture

The system is composed of three runtime components and a set of static skill files:

**PostgreSQL Database** — The source of truth for all project and task data. Handles concurrent access through database-level locking (SELECT FOR UPDATE) and ACID transactions. All computed properties (effective points, readiness, ancestry) are derived at query time via SQL.

**FastAPI Backend** — The REST API service. Handles all CRUD operations, enforces business rules (lock validation, state transitions, sizing validation), computes derived fields for API responses, and manages the lock lifecycle including expiry cleanup. Organized into routes (HTTP layer), services (business logic), and models (data layer).

**React Frontend** — The human interface. Provides a tree view of the task hierarchy, a task detail panel with sizing breakdown visualization, and a kanban-style board for tracking execution status. Communicates exclusively through the REST API.

**Agent Skill Files** — Markdown documentation that teaches coding agents how to interact with Chorus. Agents read the skill file to learn API endpoints, workflow patterns, and the sizing rubric, then make HTTP calls directly against the REST API. No intermediary process is needed — the skill file is the agent interface.

## Deployment Trust Model

Chorus v1 intentionally runs without authentication and authorization. It is designed for trusted, single-tenant homelab use and private network access.

Guardrails for this model:

- Do not expose the API directly to the public internet.
- Treat `caller_label` and `author` fields as coordination metadata, not identity proof.
- `force=true` lock release remains available for operator recovery.
- Heartbeat/release still require matching `caller_label` for normal flows, with `force=true` as a manual override.

Recommended deployment boundary:

- Private LAN only, or VPN-only access (for example Tailscale/WireGuard).
- Optional reverse proxy IP allowlist if external access is needed.

## API Design

### Project Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /projects | Create a new project |
| GET | /projects | List all projects |
| GET | /projects/{id} | Get project details with summary statistics |
| PUT | /projects/{id} | Update project name or description |
| GET | /projects/{id}/export | Export full project snapshot (tasks, work logs, commits) for backup/audit |
| DELETE | /projects/{id} | Hard delete project and all associated tasks. Caller should export first if retention is needed. |
| GET | /projects/{id}/tasks | Get top-level tasks for a project |

### Task Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /projects/{id}/tasks | Create a top-level task in a project |
| POST | /tasks/{id}/subtasks | Create a subtask under a parent |
| GET | /tasks/{id} | Get task with computed fields (effective points, readiness, children summary) |
| PUT | /tasks/{id} | Update task fields (name, description, context, type) |
| DELETE | /tasks/{id} | Hard delete task and descendants. Prefer parent-level archival/export before destructive deletes. |
| GET | /tasks/{id}/tree | Get full subtree recursively |
| GET | /tasks/{id}/ancestry | Get chain from task to project root |
| GET | /tasks/{id}/context | Synthesized context + freshness metadata. Optional `?include_commits=true` adds commit history. |
| PATCH | /tasks/{id}/status | State transition with validation |
| PATCH | /tasks/{id}/reorder | Change position among siblings |

Deletion and retention policy for v1:

- Deletion is hard-delete by default for simplicity.
- Deleting a project removes all descendant tasks, work logs, and commit records.
- If retention is needed, callers should use export endpoints before deletion.
- Soft-delete can be added in a future version if retention requirements grow.

### Atomic Operation Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /tasks/{id}/size | Submit five-dimension scoring. Server validates and computes total. Requires `work_log_content` — the server creates the work log entry transactionally with the sizing. |
| POST | /tasks/{id}/breakdown | Create subtasks from a breakdown. Accepts subtask array and optional parent description update. Requires `work_log_content` — the server creates the work log entry transactionally with the breakdown. |
| POST | /tasks/{id}/refine | Update description/context for refinement. Clears `needs_refinement` flag. Requires `work_log_content` and writes log transactionally. |
| POST | /tasks/{id}/flag-refinement | Set `needs_refinement` with notes explaining what is missing. |
| POST | /tasks/{id}/complete | Complete implementation atomically: append implementation work log, attach optional commits, and set status to `done` in one transaction. |

### Lock Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /tasks/{id}/lock | Acquire lock (caller_label, purpose). Validates preconditions. Sets expires_at from purpose-based TTL. |
| PATCH | /tasks/{id}/lock/heartbeat | Extend lock expiry. Resets `last_heartbeat_at` and recomputes `expires_at`. Caller must be the lock holder. |
| DELETE | /tasks/{id}/lock | Release lock. Caller must be the lock holder, or pass `?force=true` to force-release any lock. |

### Work Log and Commit Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /tasks/{id}/work-log | Append a work log entry (author, operation, content) |
| GET | /tasks/{id}/work-log | Get chronological work log for a task |
| POST | /tasks/{id}/commits | Record a commit (hash, message, author) |
| GET | /tasks/{id}/commits | Get all commits for a task |

### Discovery and Queue Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /projects/{id}/backlog | Tasks in ready + todo state (implementation backlog) |
| GET | /projects/{id}/in-progress | Tasks in doing state with lock information |
| GET | /projects/{id}/needs-refinement | Tasks with low confidence or needs_refinement flag |
| GET | /tasks/available | Unlocked tasks available for work, filterable by project, operation type, task type, and point range. |

Queue semantics for deterministic multi-agent behavior:

- All queue-style endpoints support `limit`, `offset`, and `sort` query parameters.
- Default ordering for available work: `priority DESC`, `effective_points ASC`, `created_at ASC`, `id ASC`.
- `/tasks/available` returns eligibility-filtered tasks only:
  - `operation=sizing`: unsized tasks
  - `operation=breakdown`: tasks in computed `Needs Breakdown`
  - `operation=implementation`: tasks in computed `Ready`
- Final claim is lock-based: clients must still acquire lock; `409` indicates race/loss.

### API Error Contract

All error responses share a common shape:

```json
{
  "error": {
    "code": "LOCK_CONFLICT",
    "message": "Task is already locked by another caller",
    "details": { "task_id": "..." },
    "request_id": "..."
  }
}
```

Canonical HTTP statuses:

- `400` malformed request
- `401` reserved for future auth-enabled deployments
- `403` reserved for future policy restrictions
- `404` entity not found
- `409` lock conflict or invalid concurrent update
- `422` business rule violation (for example invalid state transition)
- `429` rate limiting (optional, deployment-specific)
- `500` unexpected server error

Domain error codes include: `LOCK_CONFLICT`, `INVALID_READINESS_STATE`, `INVALID_STATUS_TRANSITION`, `CONTEXT_STALE`, `VALIDATION_ERROR`.

## Agent Skill Design

Agent skills are markdown files that teach coding agents (Claude Code, Cursor) how to interact with Chorus. Rather than running a separate intermediary process, agents read the skill file and make HTTP calls directly against the REST API. This is simpler to maintain, requires no additional infrastructure, and works with any agent that can read files and make HTTP requests.

### Skill File Contents

The skill file encodes everything an agent needs to operate:

| Section | Content |
|---|---|
| Overview | What Chorus is and how the task pipeline works |
| API Reference | Base URL, key endpoints with request/response examples |
| Sizing Rubric | The five-dimension scoring framework with scoring guidelines and examples |
| Workflow Patterns | Step-by-step procedures for each atomic operation |
| Conventions | Work log expectations, commit tracking, lock hygiene, scope discipline |

### Agent Workflow Patterns

The skill file teaches agents these standard workflows:

**Sizing workflow:** `GET /tasks/available?operation=sizing` -> `POST /tasks/{id}/lock` (purpose=sizing) -> `GET /tasks/{id}/context` -> `POST /tasks/{id}/size` (with `work_log_content`) -> `DELETE /tasks/{id}/lock`

**Breakdown workflow:** `GET /tasks/available?operation=breakdown` -> `POST /tasks/{id}/lock` (purpose=breakdown) -> `GET /tasks/{id}/context` -> `POST /tasks/{id}/breakdown` (with `work_log_content`) -> `DELETE /tasks/{id}/lock`

**Implementation workflow:** `GET /tasks/available?operation=implementation` -> `POST /tasks/{id}/lock` (purpose=implementation) -> `GET /tasks/{id}/context` -> [do coding work] -> `POST /tasks/{id}/complete` (work log + optional commits + done) -> `DELETE /tasks/{id}/lock`

**Discovery workflow:** When an agent notices new work during implementation, it should create a new task linked to the current context rather than expanding scope. This keeps the current task atomic.

Implementation completion should prefer `POST /tasks/{id}/complete` so status and operation log are written atomically.

## Non-Functional Requirements

Initial v1 targets for a homelab deployment:

| Area | Target |
|---|---|
| Scale | Up to 50 projects, 100k tasks total, depth up to 12 levels |
| Read latency | p95 < 300ms for single-task reads; p95 < 800ms for queue endpoints |
| Write latency | p95 < 500ms for lock/sizing/refinement endpoints |
| Lock cleanup | Expired lock sweep every 60 seconds; stale lock visible for no more than 2 minutes |
| Context payload | Default context response capped at 64 KB serialized; endpoint supports truncation indicators |
| Idempotency | `size`, `breakdown`, `refine`, and `complete` accept optional idempotency key header |

Agent retry guidance:

- On `409`, re-query available tasks and retry with exponential backoff.
- On `422`, log failure reason to work log (if lock held) and release lock.
- On `500`, retry with bounded backoff and jitter.

## Frontend Design

The React frontend serves as the human oversight interface. While agents interact with the REST API directly (guided by skill files), humans use the frontend to create projects, manage tasks, and monitor agent activity.

### Key Views

| View | Purpose | Key Interactions |
|---|---|---|
| Task Tree | Primary view. Hierarchical display of all tasks in a project with inline status, size, and computed readiness indicators. | Expand/collapse nodes, drag-and-drop reordering, click to open task detail panel, inline status badges |
| Task Detail | Slide-out panel showing full task information when a task is selected. | Edit description/context, view sizing breakdown (radar chart), scroll work log timeline, view commits, flag for refinement |
| Kanban Board | Tasks organized by status columns (To Do, Doing, Done, Won't Do) within a project. | Visual status tracking, see which agents are working on what, identify bottlenecks |
| Lock Monitor | Dashboard showing active locks and recent work. | Monitor agent progress, identify stale locks, force-release expired locks |

### Technology Choices

| Component | Library | Rationale |
|---|---|---|
| Build | Vite | Fast dev server, simple config, no framework overhead |
| UI Framework | React | Component model fits tree/panel UI well |
| Tree View | react-arborist or dnd-kit | Collapsible tree with drag-and-drop reordering |
| State Management | TanStack Query | Server state caching with automatic refetching |
| Styling | Tailwind CSS | Utility-first, consistent design without custom CSS overhead |

## Project Structure

```
chorus/
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app, middleware, startup
│   │   ├── models/                     # SQLAlchemy ORM models
│   │   │   ├── project.py
│   │   │   ├── task.py
│   │   │   ├── lock.py
│   │   │   ├── work_log.py
│   │   │   └── commit.py
│   │   ├── schemas/                    # Pydantic request/response models
│   │   │   ├── task.py
│   │   │   ├── project.py
│   │   │   └── sizing.py
│   │   ├── api/
│   │   │   ├── routes/                 # HTTP route handlers
│   │   │   │   ├── projects.py
│   │   │   │   ├── tasks.py
│   │   │   │   └── locks.py
│   │   │   └── dependencies.py         # DB session, common deps
│   │   ├── services/                   # Business logic
│   │   │   ├── task_service.py         # Computed fields, tree ops, rollup
│   │   │   ├── lock_service.py         # Acquire, release, heartbeat, TTL expiry cleanup
│   │   │   └── sizing_service.py       # Scoring validation, breakdown triggers
│   │   └── db/
│   │       ├── session.py              # AsyncSession factory
│   │       └── migrations/             # Alembic migration scripts
│   ├── Dockerfile
│   ├── requirements.txt
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── api/                        # API client generated from OpenAPI spec
│   │   └── App.jsx
│   ├── Dockerfile
│   └── package.json
└── skills/
    └── chorus/
        └── SKILL.md                    # Complete agent skill: API reference, workflow patterns, sizing rubric
```
