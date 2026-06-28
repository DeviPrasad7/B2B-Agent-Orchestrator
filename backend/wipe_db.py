import asyncio
from src.core.database import async_session
from sqlalchemy import text

async def wipe():
    async with async_session() as session:
        await session.execute(text("TRUNCATE TABLE prospects RESTART IDENTITY CASCADE;"))
        await session.commit()
        print("Database wiped.")

if __name__ == "__main__":
    asyncio.run(wipe())
