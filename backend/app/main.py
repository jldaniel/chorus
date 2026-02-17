from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.locks import router as locks_router
from app.api.routes.projects import router as projects_router
from app.api.routes.tasks import router as tasks_router
from app.db.session import async_session
from app.services.lock_service import start_lock_cleanup_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = start_lock_cleanup_task(async_session)
    yield
    cleanup_task.cancel()


app = FastAPI(title="Chorus", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(locks_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
