
# init_db.py
"""
Initialize database with Docker Compose.
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import init_db, engine
from backend.utils.logging import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialization complete!")
    
    # Verify tables created
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.info(f"Tables created: {tables}")