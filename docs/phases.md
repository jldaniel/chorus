# Chorus Implementation Phases

## Phase 1: Database Models & Migrations ✅

SQLAlchemy ORM models for all 5 entities (Projects, Tasks, TaskLocks, WorkLogEntries, TaskCommits), Alembic setup, and initial migration. Models are self-contained with clear specs — the schema is fully defined in the architecture doc with types, constraints, and indexes.

## Phase 2: Project CRUD & Core Task CRUD

FastAPI routes, Pydantic schemas, and service layer for Projects (create, list, get, update, delete) and basic Task operations (create top-level, create subtask, get, update, delete). Includes computed fields like `effective_points`, `readiness`, `rolled_up_points`, and `unsized_children`.

## Phase 3: Task Tree Operations & Context

Tree endpoint (`/tasks/{id}/tree`), ancestry endpoint (`/tasks/{id}/ancestry`), context synthesis endpoint (`/tasks/{id}/context`) with freshness metadata, task reordering, and status transitions with parent-child validation rules.

## Phase 4: Locking System

Lock acquire, release, heartbeat endpoints. TTL-based expiry logic, purpose-based TTL values, precondition validation (e.g., sizing lock requires `points` is null), expired lock cleanup (background sweep), force-release.

## Phase 5: Atomic Operations

Sizing (`/tasks/{id}/size`), breakdown (`/tasks/{id}/breakdown`), refinement (`/tasks/{id}/refine`, `/tasks/{id}/flag-refinement`), and completion (`/tasks/{id}/complete`) endpoints. Each writes transactionally with work log entries. Includes commit tracking endpoints.

## Phase 6: Discovery & Queue Endpoints

`/projects/{id}/backlog`, `/projects/{id}/in-progress`, `/projects/{id}/needs-refinement`, `/tasks/available` with filtering by operation type, sorting, and pagination.

## Phase 7: Project Export & Error Handling Polish

`/projects/{id}/export` endpoint, standardized error response format (the `{"error": {...}}` contract), idempotency key support, and remaining edge case handling.

## Phase 8: Agent Skill File

The `skills/chorus/SKILL.md` file — complete API reference, workflow patterns, sizing rubric, and conventions. Written after the API is complete so it reflects reality.

## Phase 9: Frontend

React + Vite app with Task Tree view, Task Detail panel, Kanban Board, and Lock Monitor. Built last since it's a pure consumer of the stable, complete API.
