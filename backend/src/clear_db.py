import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from core.settings import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        from sqlalchemy import text
        # Truncate all tables and cascade the deletes
        await conn.execute(text("TRUNCATE TABLE prospects CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE hitl_requests CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE events CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE workflows CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE custom_agents CASCADE;"))
        print("Successfully cleared all data from the database.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
