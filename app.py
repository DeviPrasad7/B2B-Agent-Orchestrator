import asyncio
import sys
import os

# Add src to python path so imports work without installing as a package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from core.settings import settings
from models.database import engine, Base, init_db
import uvicorn
from api.main import app

async def main():
    await init_db()
    
    # Run FastAPI server
    is_dev = settings.APP_ENV != "production"
    config = uvicorn.Config("app:app", host="0.0.0.0", port=8000, reload=is_dev)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
