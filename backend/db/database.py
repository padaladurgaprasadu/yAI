import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL connection string
# Fallback to local Docker setup if not provided in .env
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://aion_user:aion_password@localhost:5432/aion_db"
)

# Initialize the SQLAlchemy Engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True, # Test connections before handing them out
    echo=False # Set to True for SQL query logging
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative class definitions
Base = declarative_base()

def get_db():
    """
    Dependency function to get a database session for FastAPI endpoints.
    Ensures the session is closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
