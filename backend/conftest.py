from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.session import get_session
from app.main import app
from app.models import Base

DATABASE_URL = "postgresql+asyncpg://chorus:chorus_dev@db:5432/chorus_test"

_schema_created = False


@pytest_asyncio.fixture
async def engine():
    global _schema_created
    eng = create_async_engine(DATABASE_URL)
    if not _schema_created:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        _schema_created = True
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession]:
    async with engine.connect() as conn:
        txn = await conn.begin()
        session_factory = async_sessionmaker(bind=conn, expire_on_commit=False)
        async with session_factory() as s:
            await conn.begin_nested()

            @event.listens_for(s.sync_session, "after_transaction_end")
            def reopen_nested(session, transaction):
                if conn.closed:
                    return
                if not conn.in_nested_transaction():
                    conn.sync_connection.begin_nested()

            yield s

        await txn.rollback()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
