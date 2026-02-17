from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.projects import router as projects_router
from app.api.routes.tasks import router as tasks_router

app = FastAPI(title="Chorus")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(tasks_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
