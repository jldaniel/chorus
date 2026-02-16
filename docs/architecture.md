# Chorus

**Agent-Native Project Management System**

## Table of Contents

- [Executive Summary](#executive-summary)
- [Core Concepts](#core-concepts)
- [Autonomy Mode](#autonomy-mode)
- [Complexity Scoring Framework](#complexity-scoring-framework)
- [Agent Interaction Model](#agent-interaction-model)
- [Task Lifecycle](#task-lifecycle)
- [Data Model](#data-model)
- [System Architecture](#system-architecture)
- [API Design](#api-design)
- [Agent Skill Design](#agent-skill-design)
- [Frontend Design](#frontend-design)
- [Project Structure](#project-structure)
- [Implementation Plan](#implementation-plan)
- [Key Design Decisions](#key-design-decisions)

## Executive Summary

Chorus is a project management system intended for working with AI agents on more complicated tasks. The project focuse letting agents help break down and define tasks to then work on those tasks when sufficiently defined. The system provides hierarchical task management with infinite nesting, a complexity scoring framework, basic locking for multi-agent concurrency. An autonomy mode system controls whether agents can freely operate on projects and tasks or whether human review gates are enforced. Tasks flow through a pipeline of atomic operations — sizing, breakdown, refinement, review, and implementation — each performed by a single agent in a single session.

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
| Doing | An agent is actively working on implementation |
| Done | Implementation is complete |
| Won't Do | Task has been cancelled or determined unnecessary |

### Task Readiness

The system computes readiness using the following logic, evaluated in priority order. The "Pending Review" state only applies to tasks in `manual` mode — in `agent` mode, the review gate is skipped.

| Computed State | Condition | What It Means |
|---|---|---|
| Needs Refinement | `needs_refinement` flag is true | A human or agent has flagged the task as insufficiently defined. The `refinement_notes` field explains what is missing. |
| Needs Sizing | `points` is null | The task has not been assessed for complexity. An agent should take it for sizing. |
| Needs Breakdown | `points` > 6 and no sized children exist | The task has been sized and is too complex for a single agent session. It needs decomposition into subtasks. |
| Pending Review | `approved` is false AND effective autonomy mode is `manual` | The task appears technically ready but has not been reviewed by a human. Only applies in `manual` mode. |
| Ready | All above conditions are false | The task is fully defined, appropriately sized, and (if in manual mode) approved. An agent can take it for implementation. |

The `needs_refinement` boolean is the only readiness-related flag stored on the task. It exists because refinement is a judgment call that cannot be inferred from other data. When a human or agent determines that a task description is ambiguous, incomplete, or contradictory, they set this flag and provide `refinement_notes` explaining what needs to change.

### Projects

Projects are organizational containers for tasks. Each project has a name and description that provides high-level context about the project's goals, constraints, and architecture. Top-level tasks belong to a project, and all descendants inherit that project association through the hierarchy. Each project also has an autonomy mode that serves as the default for all tasks within it (see [Autonomy Mode](#autonomy-mode)).

## Autonomy Mode

Chorus supports two modes of operation that control whether AI agents can interact with a project or task. This is enforced at the API layer, not just advisory.

### Modes

| Mode | Behavior |
|---|---|
| `agent` | Agents operate freely — they can size, break down, refine, and implement tasks without human review gates. The `approved` flag and "Pending Review" computed state are skipped; tasks go directly from sized to ready. |
| `manual` | Agents are blocked from operating on the task. All mutation endpoints (lock acquisition, sizing, breakdown, status changes) return 403 for non-human agent types. Humans retain full control over task definition, review, and implementation. |

### Inheritance

Autonomy mode is set on **projects** as the default for all tasks. Individual **tasks** can override the project default, and that override flows down to all descendants.

The resolution order for a task's effective autonomy mode:

1. If the task has an explicit `autonomy_mode_override`, use it.
2. Otherwise, walk up the parent chain until a task with an explicit override is found.
3. If no ancestor has an override, use the project's `autonomy_mode`.

The API computes and returns `effective_autonomy_mode` on every task response. This allows a human to set a project to `manual` but release a specific subtree to agents by overriding a single task to `agent` — all children inherit that override.

### API Enforcement

Enforcement happens at the API layer using the requesting agent's identity. Every agent session registers in the system with a `session_id` and `agent_type` (e.g., `claude_code`, `cursor`, `human`). When a mutation endpoint receives a request for a task whose effective mode is `manual`:

- If the requester's `agent_type` is non-human: the API returns **403 Forbidden** with a message explaining the task is in manual mode.
- If the requester's `agent_type` is `human`: the request proceeds normally.

This applies to all mutation endpoints: lock acquisition, sizing, breakdown, refinement, status changes, subtask creation, and approval.

Discovery endpoints (`/tasks/available`) filter out `manual`-mode tasks by default when queried by a non-human agent, so agents never see work they cannot act on.

The skill file reinforces this by teaching agents to only look for `agent`-mode work, but even if an agent ignores that guidance, the API blocks it.

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
| Total <= 6 | Task is appropriately sized for agent execution. Mark as sized and move through review. |
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

Chorus uses pessimistic locking to ensure only one agent operates on a task at a time. When an agent takes a task, it acquires an exclusive lock specifying the operation purpose. Other agents see the task as locked and skip it. Locks have a TTL-based expiration time to prevent zombie locks from crashed or abandoned agent sessions. The TTL is set automatically based on the lock purpose — no heartbeat or background process is required.

TTL per lock purpose:

| Lock Purpose | TTL |
|---|---|
| sizing | 15 minutes |
| breakdown | 30 minutes |
| refinement | 30 minutes |
| implementation | 1 hour |

When a lock is acquired, the server computes `expires_at` from the purpose-based TTL. If an existing lock has expired at the time a new acquisition is attempted, the server releases the stale lock and grants the new request. A background cleanup task also periodically sweeps expired locks. Humans (project owners) can force-release any lock via `DELETE /tasks/{id}/lock`, even locks they don't hold.

The locking protocol:

| Step | Action | Details |
|---|---|---|
| 1 | Acquire | Agent requests a lock with a purpose (sizing, breakdown, refinement, implementation). The server validates that the task is in an appropriate state for the requested operation and that no unexpired lock is held. If an expired lock exists, it is released automatically. |
| 2 | Operate | Agent performs its atomic operation. The lock purpose constrains what operations are valid. |
| 3 | Log | Agent writes a work log entry describing what it did, decisions it made, and any issues encountered. |
| 4 | Release | Agent explicitly releases the lock. If the agent crashes, the TTL expiry handles cleanup. |

Lock validation rules enforced by the API:

| Lock Purpose | Precondition |
|---|---|
| (all) | If the task's effective autonomy mode is `manual`, the requesting agent must have `agent_type` of `human`. Non-human agents receive 403. |
| sizing | Task must not already be sized (`points` is null) |
| breakdown | Task must be sized with total > 6 or flagged for breakdown |
| refinement | No specific precondition — any task can be refined |
| implementation | Task must be in ready computed state |

### Work Logs

Work logs are the continuity mechanism between agents. Since each operation is atomic and agents have no memory between sessions, the work log provides the full history of what has been done to a task. Every atomic operation must leave a work log entry. When a new agent picks up a task, it reads the description (the spec), the sizing breakdown (the complexity assessment), and the work log (the operational history) to get complete context.

Work log entries are immutable and append-only. Each entry records the agent, the operation type, a timestamp, and freeform content describing what was done.

### Commit Tracking

Commits are tracked as metadata on tasks, decoupled from task status. An agent can work on a task, make several commits, and release the lock without completing the task. The next agent sees the commit history and can pick up where the previous agent left off. Each commit records the hash, message, the agent that made it, and a timestamp.

### Context Traversal

Agents need to understand how their task fits into the broader project. The API provides endpoints for traversing the task hierarchy: ancestry (the chain from a task up to the project root) and tree (a task and all its descendants). A dedicated context endpoint synthesizes the full picture — the task's description, all ancestor descriptions, the work log, and commit history — into a single response optimized for an LLM's context window.

### Parent-Child Consistency

When breaking down tasks, agents may arrive at conclusions that diverge from the parent task's original description. Chorus addresses this with two conventions. First, parent descriptions should be summaries of goals and scope, not implementation details — the subtasks are where specifics live. Second, when a breakdown changes the parent's intent, the agent updates the parent description and explicitly documents the change in the work log. The context field on child tasks captures relevant parent information at the time of breakdown, and the system can flag when a parent has been modified after its children's context was written.

## Task Lifecycle

A task moves through a pipeline of atomic operations, with review gates between each step. The pipeline is not a rigid state machine — tasks can be refined at any point, sizing can be revised, and the review gate is optional for trusted workflows.

### Standard Flow

The typical lifecycle of a task from creation to completion:

| Phase | Actor | What Happens |
|---|---|---|
| 1. Creation | Human / PM Agent | A task is created with a name and description. May include a gut-feel size estimate. The task enters the system as To Do with computed readiness of Needs Sizing (if unsized) or Needs Breakdown (if sized > 6). |
| 2. Sizing | Sizing Agent | Agent locks the task for sizing. Reads the description. Scores each of the five complexity dimensions with reasoning. If total <= 6, the task is marked as sized. If total >= 7, it is flagged for breakdown. Agent releases the lock. |
| 3. Review | Human / PM Agent | **Manual mode only.** Reviews the sizing assessment. Checks that the description is clear, the scoring is reasonable, and the task is well-defined. Approves the task or flags it for refinement with notes. In `agent` mode, this step is skipped — tasks move directly from sizing to breakdown or implementation. |
| 4. Breakdown | Breakdown Agent | For tasks scoring >= 7: agent locks the parent, creates subtasks with descriptions and context, optionally updates the parent description, logs decisions. Each subtask starts the pipeline from the beginning. |
| 5. Implementation | Implementation Agent | Agent locks a ready task for implementation. Reads the description, context, sizing, and work log. Performs the coding work. Makes commits (tracked as metadata). Marks the task Done. Releases the lock. |

### Flexible Workflows

The pipeline is not strictly linear. A task can be refined at any point — before or after sizing. A human can provide an initial gut-feel size, have the task refined for better definition, and then have it re-sized with more accurate scoring. Sizing can be revised if new information emerges. The approval gate can be skipped for low-risk tasks or high-trust agent teams. What matters is that the data on the task accurately reflects its current state, and the computed readiness derives the correct next action from that data.

## Data Model

### Entity Relationship Overview

The data model consists of six entities. Projects contain Tasks in a hierarchy. Tasks are operated on by Agents via Locks. Work done on tasks is recorded in WorkLogEntries and TaskCommits.

### Projects

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | Unique identifier |
| name | VARCHAR(255) | NOT NULL | Project name |
| description | TEXT | NULLABLE | Project goals, architecture, constraints |
| autonomy_mode | ENUM | NOT NULL, DEFAULT manual | Default autonomy mode for all tasks: agent, manual |
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
| approved | BOOLEAN | NOT NULL, DEFAULT FALSE | Human/PM has reviewed and approved |
| autonomy_mode_override | ENUM | NULLABLE | Override autonomy mode for this subtree: agent, manual. Null = inherit from parent or project. |
| position | INTEGER | NOT NULL, DEFAULT 0 | Ordering among siblings |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW | Last modification timestamp |

### Task Locks

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | Unique identifier |
| task_id | UUID | FK -> Tasks, UNIQUE | One lock per task |
| agent_id | UUID | FK -> Agents, NOT NULL | Agent session holding the lock |
| lock_purpose | ENUM | NOT NULL | sizing, breakdown, refinement, implementation |
| acquired_at | TIMESTAMP | NOT NULL, DEFAULT NOW | When the lock was acquired |
| expires_at | TIMESTAMP | NOT NULL | Auto-release time (set from purpose-based TTL) |

### Task Commits

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | Unique identifier |
| task_id | UUID | FK -> Tasks, NOT NULL | Associated task |
| agent_id | UUID | FK -> Agents, NULLABLE | Agent that made the commit |
| commit_hash | VARCHAR(40) | NOT NULL | Git commit SHA |
| message | TEXT | NULLABLE | Commit message |
| committed_at | TIMESTAMP | NOT NULL | When the commit was made |

### Work Log Entries

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | Unique identifier |
| task_id | UUID | FK -> Tasks, NOT NULL | Associated task |
| agent_id | UUID | FK -> Agents, NULLABLE | Agent or null for human entries |
| operation | ENUM | NOT NULL | sizing, breakdown, refinement, implementation, review, note |
| content | TEXT | NOT NULL | What was done, decisions made, issues encountered |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW | Entry timestamp |

### Agents

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | Unique identifier |
| session_id | VARCHAR | NOT NULL, UNIQUE | The agent's session identifier (e.g. Claude Code session ID) |
| agent_type | VARCHAR(100) | NOT NULL | e.g. claude_code, cursor, human |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW | Registration timestamp |

### Key Indexes

| Index | Table | Columns | Purpose |
|---|---|---|---|
| idx_tasks_project | Tasks | project_id | Filter tasks by project |
| idx_tasks_parent | Tasks | parent_task_id | Tree traversal, find children |
| idx_tasks_status | Tasks | status | Filter by execution state |
| idx_tasks_points | Tasks | points | Find unsized or oversized tasks |
| idx_locks_task | TaskLocks | task_id (UNIQUE) | Lock lookup and enforcement |
| idx_locks_agent | TaskLocks | agent_id | Find all locks held by an agent |
| idx_locks_expiry | TaskLocks | expires_at | Cleanup expired locks |
| idx_commits_task | TaskCommits | task_id | Find commits for a task |
| idx_worklog_task | WorkLogEntries | task_id, created_at | Chronological work history |

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

**FastAPI Backend** — The REST API service. Handles all CRUD operations, enforces business rules (lock validation, state transitions, sizing validation, autonomy mode enforcement), computes derived fields for API responses, and manages the lock lifecycle including expiry cleanup. Organized into routes (HTTP layer), services (business logic), and models (data layer).

**React Frontend** — The human interface. Provides a tree view of the task hierarchy, a task detail panel with sizing breakdown visualization, a review queue for pending tasks, and a kanban-style board for tracking execution status. Communicates exclusively through the REST API.

**Agent Skill Files** — Markdown documentation that teaches coding agents how to interact with Chorus. Agents read the skill file to learn API endpoints, workflow patterns, and the sizing rubric, then make HTTP calls directly against the REST API. No intermediary process is needed — the skill file is the agent interface.

## API Design

### Project Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /projects | Create a new project |
| GET | /projects | List all projects |
| GET | /projects/{id} | Get project details with summary statistics |
| PUT | /projects/{id} | Update project name or description |
| DELETE | /projects/{id} | Delete a project and all associated tasks |
| GET | /projects/{id}/tasks | Get top-level tasks for a project |

### Task Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /projects/{id}/tasks | Create a top-level task in a project |
| POST | /tasks/{id}/subtasks | Create a subtask under a parent |
| GET | /tasks/{id} | Get task with computed fields (effective points, readiness, children summary) |
| PUT | /tasks/{id} | Update task fields (name, description, context, type) |
| DELETE | /tasks/{id} | Delete a task and all descendants |
| GET | /tasks/{id}/tree | Get full subtree recursively |
| GET | /tasks/{id}/ancestry | Get chain from task to project root |
| GET | /tasks/{id}/context | Synthesized context: description + ancestor descriptions + work log |
| PATCH | /tasks/{id}/status | State transition with validation |
| PATCH | /tasks/{id}/reorder | Change position among siblings |

### Atomic Operation Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /tasks/{id}/size | Submit five-dimension scoring. Server validates and computes total. |
| POST | /tasks/{id}/breakdown | Create subtasks from a breakdown. Accepts subtask array and optional parent description update. Requires work log entry. |
| POST | /tasks/{id}/refine | Update description/context for refinement. Clears `needs_refinement` flag. |
| POST | /tasks/{id}/approve | Mark task as reviewed and approved by human/PM. |
| POST | /tasks/{id}/flag-refinement | Set `needs_refinement` with notes explaining what is missing. |

### Lock Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /tasks/{id}/lock | Acquire lock (agent_id, purpose). Validates preconditions. Sets expires_at from purpose-based TTL. |
| DELETE | /tasks/{id}/lock | Release lock. Agent must be the lock holder, or requester must be a project owner (force-release). |

### Work Log and Commit Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /tasks/{id}/work-log | Append a work log entry (agent_id, operation, content) |
| GET | /tasks/{id}/work-log | Get chronological work log for a task |
| POST | /tasks/{id}/commits | Record a commit (hash, message, agent_id) |
| GET | /tasks/{id}/commits | Get all commits for a task |

### Discovery and Queue Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /projects/{id}/review-queue | Tasks in sized or needs_breakdown state pending review |
| GET | /projects/{id}/backlog | Tasks in ready + todo state (implementation backlog) |
| GET | /projects/{id}/in-progress | Tasks in doing state with lock information |
| GET | /projects/{id}/needs-refinement | Tasks with low confidence or needs_refinement flag |
| GET | /tasks/available | Unlocked tasks available for work, filterable by project, operation type, task type, and point range. Filters by effective autonomy mode based on the requesting agent's type — non-human agents only see `agent`-mode tasks. |

### Agent Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /agents | Register a new agent session (session_id, agent_type). Returns agent id for subsequent requests. |
| GET | /agents | List all agent sessions |
| GET | /agents/{id} | Get agent session details |
| GET | /agents/{id}/tasks | Get tasks currently locked by this agent session |

## Agent Skill Design

Agent skills are markdown files that teach coding agents (Claude Code, Cursor) how to interact with Chorus. Rather than running a separate intermediary process, agents read the skill file and make HTTP calls directly against the REST API. This is simpler to maintain, requires no additional infrastructure, and works with any agent that can read files and make HTTP requests.

### Skill File Contents

The skill file encodes everything an agent needs to operate:

| Section | Content |
|---|---|
| Overview | What Chorus is, how autonomy mode works, what the agent should check before operating on any task |
| API Reference | Base URL, authentication, key endpoints with request/response examples |
| Sizing Rubric | The five-dimension scoring framework with scoring guidelines and examples |
| Workflow Patterns | Step-by-step procedures for each atomic operation |
| Conventions | Work log expectations, commit tracking, lock hygiene, scope discipline |

### Agent Workflow Patterns

The skill file teaches agents these standard workflows:

**Sizing workflow:** `GET /tasks/available?operation=sizing` -> `POST /tasks/{id}/lock` (purpose=sizing) -> `GET /tasks/{id}/context` -> `POST /tasks/{id}/size` -> `POST /tasks/{id}/work-log` -> `DELETE /tasks/{id}/lock`

**Breakdown workflow:** `GET /tasks/available?operation=breakdown` -> `POST /tasks/{id}/lock` (purpose=breakdown) -> `GET /tasks/{id}/context` -> `POST /tasks/{id}/breakdown` -> `DELETE /tasks/{id}/lock`

**Implementation workflow:** `GET /tasks/available?operation=implementation` -> `POST /tasks/{id}/lock` (purpose=implementation) -> `GET /tasks/{id}/context` -> [do coding work] -> `POST /tasks/{id}/commits` -> `PATCH /tasks/{id}/status` (done) -> `POST /tasks/{id}/work-log` -> `DELETE /tasks/{id}/lock`

**Discovery workflow:** When an agent notices new work during implementation, it should create a new task linked to the current context rather than expanding scope. This keeps the current task atomic.

## Frontend Design

The React frontend serves as the human oversight interface. While agents interact with the REST API directly (guided by skill files), humans use the frontend to create projects, review task quality, approve work, and monitor agent activity.

### Key Views

| View | Purpose | Key Interactions |
|---|---|---|
| Task Tree | Primary view. Hierarchical display of all tasks in a project with inline status, size, and computed readiness indicators. | Expand/collapse nodes, drag-and-drop reordering, click to open task detail panel, inline status badges |
| Task Detail | Slide-out panel showing full task information when a task is selected. | Edit description/context, view sizing breakdown (radar chart), scroll work log timeline, view commits, approve/flag for refinement |
| Review Queue | Filtered list of tasks awaiting human review, sorted by staleness. | Quick approve, flag for refinement with notes, view sizing details, bulk operations |
| Kanban Board | Tasks organized by status columns (To Do, Doing, Done) within a project. | Visual status tracking, see which agents are working on what, identify bottlenecks |
| Agent Activity | Dashboard showing active agents, their current locks, and recent work. | Monitor agent progress, identify stale locks, view agent work history |

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
│   │   │   ├── agent.py
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
│   │   │   │   ├── agents.py
│   │   │   │   └── locks.py
│   │   │   └── dependencies.py         # DB session, common deps
│   │   ├── services/                   # Business logic
│   │   │   ├── task_service.py         # Computed fields, tree ops, rollup
│   │   │   ├── lock_service.py         # Acquire, release, TTL expiry cleanup
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

## Implementation Plan

The build order prioritizes proving the agent interaction loop early. The frontend is deferred until the backend and agent integration are validated.

| Phase | Deliverable | Description |
|---|---|---|
| Phase 1 | Database + Schema | Docker Compose with PostgreSQL. Alembic migrations for all six entities. SQLAlchemy models with relationships and constraints. |
| Phase 2 | Core API | FastAPI application with CRUD endpoints for projects, tasks, agents. Business logic services for computed readiness, point rollup (recursive CTE), tree operations. Pydantic schemas for all request/response models. |
| Phase 3 | Locking + Operations | Lock acquisition with precondition validation, TTL-based expiry, expiry cleanup (background task). Atomic operation endpoints: size, breakdown, refine, approve. State transition validation. Autonomy mode enforcement on all mutation endpoints. |
| Phase 4 | Agent Skill File | Markdown skill file encoding workflow patterns, sizing rubric, API reference, and autonomy mode guidance. Test with Claude Code: create project, size tasks, break down, implement. |
| Phase 5 | Frontend | React + Vite application. Task tree view with collapsible hierarchy. Task detail panel. Review queue. Kanban board. Agent activity dashboard. |
| Phase 6 | Polish + Iterate | Refine based on real usage. Add bulk operations, task search/filter, project-level analytics, export to markdown (TASKS.md in repo). |

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Database | PostgreSQL over DuckDB | Multi-agent concurrency requires proper concurrent writes. DuckDB is single-writer. PostgreSQL provides ACID transactions, SELECT FOR UPDATE for locking, and JSONB for flexible scoring data. Docker makes local setup trivial. |
| Readiness model | Computed from data, not stored | Eliminates dual sources of truth. `needs_refinement` is the only stored flag because it represents a judgment call that cannot be inferred. All other readiness states are derived from `points`, children, and `approved` fields. |
| Point rollup | Replacement model | Once a task is broken down and children are sized, the children are the source of truth. The parent's original estimate is preserved for context but superseded. This prevents double-counting and makes the hierarchy the canonical sizing. |
| Operations | Atomic, single-purpose | Agents have limited context windows and no memory between sessions. Atomic operations keep context contained, enable clean handoffs, and allow review gates between steps. |
| Locking | Pessimistic with TTL expiry | Prevents conflicting concurrent modifications. Purpose-based TTLs handle agent crashes without requiring heartbeats — important because Claude Code and Cursor run as ephemeral sessions that cannot maintain background processes. Lock acquisition checks expiry inline for immediate reclamation. Simpler and more predictable than optimistic concurrency for agent workloads. |
| Frontend framework | React + Vite over Next.js | No SSR, SEO, or server-side routing needed. This is a dashboard app that talks to a separate API. Vite is lighter weight with faster dev experience. |
| Autonomy mode | Two modes with API enforcement | `agent` and `manual` modes enforced at the API layer via agent identity, not just advisory flags. Non-human agents receive 403 on manual-mode tasks. Discovery endpoints filter by mode so agents never see work they cannot act on. Override inheritance flows down the task tree, allowing fine-grained control within a project. |
| Work logs | Separate table, not text field | Multiple agents perform atomic operations. Structured entries with agent, operation, and timestamp enable querying, filtering, and timeline display. Append-only prevents accidental overwrites. |
| Skills over MCP | Skill files instead of MCP server | A well-written skill file teaches agents the API endpoints, workflow patterns, and sizing rubric — agents make HTTP calls directly. No intermediary process to run or maintain. MCP can be added later if a use case demands it, but for Claude Code and Cursor, skills are sufficient and simpler. |
| Skills before frontend | Build order prioritizes agent integration | The system's primary users are agents. Proving the agent interaction loop (create -> size -> break down -> implement) is more valuable than a GUI for validating the design. |

