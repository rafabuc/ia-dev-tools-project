# backend/database.py
"""
Database configuration for Docker Compose environment.
"""

import os
from typing import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from backend.utils.logging import get_logger

logger = get_logger(__name__)

# Use   the PostgreSQL URL from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # Development local without Docker (fallback)
    "postgresql://user:pass@localhost:5432/devops_copilot"
)

logger.info(f"Database URL: {DATABASE_URL}")

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    Get database session dependency.
    
    Yields:
        SQLAlchemy Session
        
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    from backend.models.base import Base  # Importar la Base única
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
    
    # Verificar conexión
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        logger.info(f"Connected to: {result.fetchone()[0]}")