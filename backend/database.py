"""SQLite setup for Code View."""

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'code_view.db'}"

engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker] = None


class Base(DeclarativeBase):
    pass


async def init_database() -> None:
    """Create data directory and initialize the async engine (tables reserved for later)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    global engine, async_session_factory
    if engine is None:
        engine = create_async_engine(DATABASE_URL, echo=False)
        async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database engine ready at %s", DATABASE_URL)
