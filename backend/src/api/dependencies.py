"""
Centralized FastAPI dependency factories.

All route files should import dependency functions from here rather than
defining their own helpers. This prevents drift between route modules
and ensures a single place to update session wiring.

Usage in route files:
    from api.dependencies import get_memory_service, get_session
    ...
    async def my_route(session: AsyncSession = Depends(get_session)):
        ...
"""

from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_service import MemoryService
from models.database import async_session


async def get_session() -> AsyncSession:
    """Yield a short-lived async DB session, auto-closed on exit."""
    async with async_session() as session:
        yield session


def get_memory_service() -> MemoryService:
    """Return a MemoryService wired to the application session factory.

    The factory (``async_session``) is passed rather than an open session,
    so MemoryService can create short-lived sessions for each DB operation.
    """
    return MemoryService(async_session)

