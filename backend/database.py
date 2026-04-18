"""SQLite setup for Code View."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'code_view.db'}"

engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


class Base(DeclarativeBase):
    pass


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if async_session_factory is None:
        raise RuntimeError("Database not initialized; call init_database() first")
    async with async_session_factory() as session:
        yield session


async def init_database() -> None:
    """Create data directory, engine, and all ORM tables."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    global engine, async_session_factory
    if engine is None:
        engine = create_async_engine(DATABASE_URL, echo=False)
        async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Register ORM models on shared metadata
    import models.db_models  # noqa: F401

    assert engine is not None
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_sqlite_schema(conn)

    logger.info("Database engine ready at %s", DATABASE_URL)


async def _migrate_sqlite_schema(conn) -> None:
    """Lightweight SQLite migrations for additive columns (existing deployments)."""

    def _upgrade(sync_conn):
        cur = sync_conn.execute(text("PRAGMA table_info(analysis_records)"))
        analysis_cols = {row[1] for row in cur.fetchall()}
        if "refinement_metadata" not in analysis_cols:
            sync_conn.execute(
                text("ALTER TABLE analysis_records ADD COLUMN refinement_metadata JSON")
            )

        cur = sync_conn.execute(text("PRAGMA table_info(evidence_items)"))
        evidence_cols = {row[1] for row in cur.fetchall()}
        if "refinement_signal" not in evidence_cols:
            sync_conn.execute(
                text("ALTER TABLE evidence_items ADD COLUMN refinement_signal VARCHAR")
            )

    await conn.run_sync(_upgrade)
