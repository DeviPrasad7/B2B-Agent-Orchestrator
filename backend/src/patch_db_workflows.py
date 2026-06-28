import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.etzbjjcqqpseokqjymvp:412526Dsp_123@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"

engine = create_async_engine(DATABASE_URL, echo=True)

async def patch():
    async with engine.begin() as conn:
        try:
            print("Creating workflows table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id UUID NOT NULL,
                    name VARCHAR NOT NULL,
                    description VARCHAR,
                    steps JSON NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                )
            """))
            
            print("Adding custom_workflow_id to prospects...")
            await conn.execute(text("ALTER TABLE prospects ADD COLUMN IF NOT EXISTS custom_workflow_id UUID REFERENCES workflows(id)"))
                
            print("Database patched successfully.")
        except Exception as e:
            print(f"Error patching database: {e}")

if __name__ == "__main__":
    asyncio.run(patch())
