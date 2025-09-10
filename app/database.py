import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# ✅ Get DATABASE_URL from environment (set this on Render)
SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///test.db")
# Fallback to SQLite locally if DATABASE_URL is not set

# ✅ Create the database engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False  # Set True if you want SQL logs
)

# ✅ Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ Base class for models
Base = declarative_base()

# ✅ Dependency to get DB session
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
