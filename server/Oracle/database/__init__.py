"""
Database package using Tortoise ORM with SQLite.
"""
from Oracle.database.database_manager import DatabaseManager


async def init_db():
    """Initialize the Tortoise ORM connection using config settings."""
    manager = await DatabaseManager.instance()
    await manager.initialize()


async def close_db():
    """Close all database connections."""
    manager = await DatabaseManager.instance()
    await manager.close()
