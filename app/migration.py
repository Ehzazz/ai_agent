import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from API.models import Base

# Load environment variables
load_dotenv()

# Get the database URL from .env
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Convert async URL to sync for migration
if DB_URL.startswith("postgresql+asyncpg"):
    DB_URL_SYNC = DB_URL.replace("postgresql+asyncpg", "postgresql")
else:
    DB_URL_SYNC = DB_URL

# Create a synchronous SQLAlchemy engine for migrations
engine = create_engine(DB_URL_SYNC, echo=True)

def run_migration():
    print("Creating all tables if they do not exist...")
    Base.metadata.create_all(engine)
    print("Migration complete.")

if __name__ == "__main__":
    run_migration() 