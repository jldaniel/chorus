import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.lock import LockAcquireRequest, LockRead
from app.services import lock_service

router = APIRouter(prefix="/tasks", tags=["locks"])


@router.post("/{task_id}/lock", response_model=LockRead, status_code=201)
async def acquire_lock(
    task_id: uuid.UUID,
    data: LockAcquireRequest,
    session: AsyncSession = Depends(get_session),
):
    lock = await lock_service.acquire_lock(session, task_id, data)
    await session.commit()
    return lock


@router.patch("/{task_id}/lock/heartbeat", response_model=LockRead)
async def heartbeat_lock(
    task_id: uuid.UUID,
    caller_label: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    lock = await lock_service.heartbeat_lock(session, task_id, caller_label)
    await session.commit()
    return lock


@router.delete("/{task_id}/lock", status_code=204)
async def release_lock(
    task_id: uuid.UUID,
    caller_label: str = Query(...),
    force: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    await lock_service.release_lock(session, task_id, caller_label, force)
    await session.commit()
