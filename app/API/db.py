# db.py
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Load .env
load_dotenv()

# PostgreSQL connection URL (for asyncpg)
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is not set")  # postgresql+asyncpg://user:pass@localhost/dbname

# SQLAlchemy base model
Base = declarative_base()

# Create async engine
engine = create_async_engine(DB_URL, echo=True)

# Session factory
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Dependency to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
