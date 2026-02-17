# Chorus

Project management for humans and AI.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Task](https://taskfile.dev/installation/) (task runner)

## Quick Start

```bash
task up
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Health check**: http://localhost:8000/health

## Architecture

| Service    | Stack                          | Port |
|------------|--------------------------------|------|
| Frontend   | React 19, Vite 7, Tailwind v4 | 3000 |
| Backend    | FastAPI, SQLAlchemy 2, Alembic | 8000 |
| Database   | PostgreSQL 17                  | 5432 |

## Development

The frontend Vite dev server proxies `/api/*` requests to the backend, stripping the `/api` prefix. Both hot-reload via volume mounts in Docker Compose.

Run `task --list` to see all available commands. Key ones:

```bash
task up                # Start all services
task down              # Stop all services
task logs              # Tail logs (e.g. task logs -- backend)

task db:migrate        # Run migrations to head
task db:migration -- "description"  # Create new migration
task db:downgrade      # Rollback one migration
task db:psql           # Open psql shell

task backend:test      # Run backend tests
task backend:lint      # Lint backend code
task backend:format    # Format backend code
task backend:shell     # Shell into backend container

task frontend:test     # Run frontend tests
task frontend:lint     # Lint frontend code
task frontend:shell    # Shell into frontend container
```
