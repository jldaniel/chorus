# Chorus

Project management for humans and AI.

## Tech Stack

| Layer    | Technologies                          |
|----------|---------------------------------------|
| Frontend | React 19, Vite 7, Tailwind CSS v4    |
| Backend  | Python, FastAPI, SQLAlchemy 2, Alembic, uv |
| Database | PostgreSQL 17                         |
| Tooling  | Docker Compose, Task (taskfile.dev)   |
| Linting  | Ruff (backend), ESLint (frontend)     |

## Development

All services run in Docker. Use `task` commands instead of running tools directly:

```
task up              # Start all services
task down            # Stop all services
task backend:test    # Run backend tests
task backend:lint    # Lint backend
task backend:format  # Format backend
task frontend:test   # Run frontend tests
task frontend:lint   # Lint frontend
task db:migrate      # Run migrations to head
task db:migration -- "description"  # Create new migration
```

Run `task --list` for the full list.

## Key Conventions

- Prefer `task` targets over raw docker/docker-compose commands when a target exists for the operation.
- The frontend Vite dev server proxies `/api/*` to the backend, stripping the `/api` prefix.
- Architecture and phased implementation plan live in `docs/`.
