import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ChorusError
from app.models.base import LockPurpose
from app.models.lock import TaskLock
from app.models.task import Task
from app.schemas.lock import LockAcquireRequest
from app.services import task_service

logger = logging.getLogger(__name__)

LOCK_TTL: dict[LockPurpose, timedelta] = {
    LockPurpose.sizing: timedelta(minutes=15),
    LockPurpose.breakdown: timedelta(minutes=30),
    LockPurpose.refinement: timedelta(minutes=30),
    LockPurpose.implementation: timedelta(hours=1),
}

CLEANUP_INTERVAL_SECONDS = 60


def validate_lock_precondition(task: Task, purpose: LockPurpose) -> None:
    if purpose == LockPurpose.sizing:
        if task.points is not None:
            raise ChorusError(422, "INVALID_READINESS_STATE", "Task is already sized")
    elif purpose == LockPurpose.breakdown:
        if task.points is None and not task.children:
            raise ChorusError(422, "INVALID_READINESS_STATE", "Task must be sized before breakdown")
        ep = task_service.compute_effective_points(task)
        unsized = task_service.compute_unsized_children(task)
        if (ep is None or ep <= 6) and unsized == 0:
            raise ChorusError(
                422,
                "INVALID_READINESS_STATE",
                "Task does not need breakdown (effective_points <= 6 and no unsized children)",
            )
    elif purpose == LockPurpose.implementation:
        readiness = task_service.compute_readiness(task)
        if readiness != "ready":
            raise ChorusError(
                422,
                "INVALID_READINESS_STATE",
                f"Task is not ready for implementation (readiness={readiness})",
                {"readiness": readiness},
            )
    # refinement: no precondition


async def acquire_lock(
    session: AsyncSession, task_id: uuid.UUID, data: LockAcquireRequest
) -> TaskLock:
    task = await task_service.get_task(session, task_id)

    # Check existing lock
    result = await session.execute(select(TaskLock).where(TaskLock.task_id == task_id))
    existing = result.scalar_one_or_none()
    if existing:
        now = datetime.now(timezone.utc)
        if existing.expires_at < now:
            await session.delete(existing)
            await session.flush()
        else:
            raise ChorusError(409, "LOCK_CONFLICT", "Task is already locked")

    validate_lock_precondition(task, data.lock_purpose)

    now = datetime.now(timezone.utc)
    lock = TaskLock(
        task_id=task_id,
        caller_label=data.caller_label,
        lock_purpose=data.lock_purpose,
        acquired_at=now,
        expires_at=now + LOCK_TTL[data.lock_purpose],
    )
    session.add(lock)
    await session.flush()
    return lock


async def heartbeat_lock(
    session: AsyncSession, task_id: uuid.UUID, caller_label: str
) -> TaskLock:
    result = await session.execute(select(TaskLock).where(TaskLock.task_id == task_id))
    lock = result.scalar_one_or_none()
    if not lock:
        raise ChorusError(404, "NOT_FOUND", "No lock found for this task")

    now = datetime.now(timezone.utc)
    if lock.expires_at < now:
        raise ChorusError(409, "LOCK_CONFLICT", "Lock has expired")

    if lock.caller_label != caller_label:
        raise ChorusError(403, "VALIDATION_ERROR", "Caller label does not match lock holder")

    purpose = LockPurpose(lock.lock_purpose) if isinstance(lock.lock_purpose, str) else lock.lock_purpose
    lock.last_heartbeat_at = now
    lock.expires_at = now + LOCK_TTL[purpose]
    await session.flush()
    return lock


async def release_lock(
    session: AsyncSession, task_id: uuid.UUID, caller_label: str, force: bool = False
) -> None:
    result = await session.execute(select(TaskLock).where(TaskLock.task_id == task_id))
    lock = result.scalar_one_or_none()
    if not lock:
        raise ChorusError(404, "NOT_FOUND", "No lock found for this task")

    if not force and lock.caller_label != caller_label:
        raise ChorusError(403, "VALIDATION_ERROR", "Caller label does not match lock holder")

    await session.delete(lock)
    await session.flush()


async def cleanup_expired_locks(session: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await session.execute(delete(TaskLock).where(TaskLock.expires_at < now))
    return result.rowcount


async def cleanup_expired_idempotency_records(session: AsyncSession) -> int:
    from app.models.idempotency import IdempotencyRecord

    now = datetime.now(timezone.utc)
    result = await session.execute(
        delete(IdempotencyRecord).where(IdempotencyRecord.expires_at < now)
    )
    return result.rowcount


async def _cleanup_loop(session_factory):
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            async with session_factory() as session:
                lock_count = await cleanup_expired_locks(session)
                idem_count = await cleanup_expired_idempotency_records(session)
                await session.commit()
                if lock_count:
                    logger.info("Cleaned up %d expired locks", lock_count)
                if idem_count:
                    logger.info("Cleaned up %d expired idempotency records", idem_count)
        except Exception:
            logger.exception("Error during cleanup")


def start_lock_cleanup_task(session_factory):
    return asyncio.create_task(_cleanup_loop(session_factory))
