"""
Database Manager - Async Singleton for Tortoise ORM.
"""
from typing import Optional
from tortoise import Tortoise

from Oracle.tooling.logger import Logger
from Oracle.tooling.singleton import SingletonMixin
from Oracle.tooling.config import Config
from Oracle.tooling.paths import get_base_path


logger = Logger("DatabaseManager")


class DatabaseManager(SingletonMixin):
    """Async singleton manager for database connections."""
    
    def __init__(self):
        """Initialize the database manager."""
        self.db_path: Optional[str] = None
        self._initialized: bool = False
    
    async def initialize(self) -> None:
        """Initialize the database connection using config settings."""
        if self._initialized:
            logger.debug("Database already initialized, skipping")
            return
        
        # Get database path from config
        config = Config()
        db_config = config.get("database")
        db_filename = db_config.get("path", "oracle.db")
        self.db_path = str(get_base_path() / db_filename)
        logger.info(f"💾 Initializing database at {self.db_path}")
        
        try:
            await Tortoise.init(
                db_url=f"sqlite://{self.db_path}",
                modules={"models": ["Oracle.database.models"]}
            )
            await Tortoise.generate_schemas()
            
            self._initialized = True
            logger.info(f"✅ Database initialized at {self.db_path}")
        except Exception as e:
            error_msg = str(e).lower()
            if "locked" in error_msg or "database is locked" in error_msg:
                logger.error(f"❌ Database is locked by another process: {self.db_path}")
                logger.error(f"   Please close any other instances of Oracle Server")
                raise RuntimeError(f"Database locked: {self.db_path}") from e
            else:
                logger.error(f"❌ Failed to initialize database: {e}")
                raise
    
    async def close(self) -> None:
        """Close all database connections."""
        if not self._initialized:
            logger.debug("💾 Database not initialized, nothing to close")
            return
        
        await Tortoise.close_connections()
        self._initialized = False
        logger.info("💾 Database connections closed")
    
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._initialized
