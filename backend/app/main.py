import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes.atomic import router as atomic_router
from app.api.routes.discovery import router as discovery_router
from app.api.routes.locks import router as locks_router
from app.api.routes.projects import router as projects_router
from app.api.routes.tasks import router as tasks_router
from app.db.session import async_session
from app.exceptions import ChorusError
from app.services.lock_service import start_lock_cleanup_task

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = start_lock_cleanup_task(async_session)
    yield
    cleanup_task.cancel()


app = FastAPI(title="Chorus", lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@app.exception_handler(ChorusError)
async def chorus_error_handler(request: Request, exc: ChorusError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": _get_request_id(request),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for err in exc.errors():
        clean = {
            "type": err.get("type"),
            "loc": list(err.get("loc", [])),
            "msg": err.get("msg"),
        }
        errors.append(clean)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": errors},
                "request_id": _get_request_id(request),
            }
        },
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "details": {},
                "request_id": _get_request_id(request),
            }
        },
    )


app.include_router(projects_router)
app.include_router(discovery_router)
app.include_router(tasks_router)
app.include_router(locks_router)
app.include_router(atomic_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
