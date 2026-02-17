# Chorus

Project management for humans and AI.

## Quick Start

```bash
docker compose up --build
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

### Running Migrations

```bash
docker compose exec backend alembic upgrade head
```
