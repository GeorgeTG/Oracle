import asyncio
import sys
import signal
import threading
from contextlib import asynccontextmanager
import uvicorn

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from Oracle.parsing.router import Router
from Oracle.parsing.utils.notify_reader import follow_file
from Oracle.services.event_bus import EventBus
from Oracle.services.service_manager import ServiceManager
from Oracle.database import init_db, close_db
from Oracle.tooling.logger import Logger
from Oracle.tooling.paths import get_base_path
from Oracle.tooling.config import Config
from Oracle.api.dependencies import get_router, get_service_manager
from Oracle.api import maps, sessions, inventory, stats, websocket, items, market, players, system


router = None
service_manager = None
reader_task = None
event_bus = None

# Global config instance
config = Config()

# Setup file logging
log_dir = get_base_path() / "logs"
Logger.set_log_directory(log_dir)

# Load config and set global log level
logger_config = config.get("logger")
if logger_config and "level" in logger_config:
    from Oracle.tooling.logger import LogLevel
    log_level = LogLevel.from_string(logger_config["level"])
    Logger.set_default_level(log_level)

logger = Logger("Server")

async def log_pipeline():
    parser_config = config.get("parser")
    log_path = parser_config["log_path"]

    try:
        logger.info(f"📄 Starting log tail with watchdog: {log_path}")
        async for line in follow_file(log_path):
            await router.feed_line(line)
    except asyncio.CancelledError:
        logger.debug("Log pipeline cancelled")
        raise
    except Exception as e:
        logger.error(f"❌ Exception in log pipeline: {e}")
        logger.trace(e)
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init database
    await init_db()
    
    # Initialize PriceDB before other services
    from Oracle.market.price_db import PriceDB
    logger.info("💰 Initializing PriceDB...")
    price_db = await PriceDB.instance()
    await price_db.refresh_pricelist()
    logger.info("💰 PriceDB initialized")
    
    # Init EventBus, Router and ServiceManager
    global service_manager, router, event_bus
    event_bus = await EventBus.instance()
    router = await Router.instance(event_bus)
    service_manager = await ServiceManager.instance(event_bus)

    logger.info("🚀 Starting pipelines…")

    global reader_task
    reader_task = asyncio.create_task(log_pipeline())

    try:
        yield  # 👉 keep tasks alive until shutdown
    except Exception as e:
        logger.error(f"❌ Exception in lifespan: {e}")
        raise
    finally:
        logger.info("⛔ Shutting down pipelines")
        
        # Shield shutdown operations from cancellation
        try:
            # Cancel log reader task
            logger.debug("Cancelling log reader task...")
            if reader_task and not reader_task.done():
                reader_task.cancel()
                try:
                    await asyncio.shield(asyncio.wait_for(reader_task, timeout=1.0))
                except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                    pass
            logger.debug("✓ Log reader cancelled")
            
            # Shutdown services
            logger.debug("Shutting down services...")
            await asyncio.shield(service_manager.shutdown())
            logger.debug("✓ Services shutdown")
            
            # Shutdown router
            logger.debug("Shutting down router...")
            if router:
                await asyncio.shield(router.shutdown())
            logger.debug("✓ Router shutdown")
            
            # Shutdown event bus
            logger.debug("Shutting down event bus...")
            if event_bus:
                await asyncio.shield(event_bus.shutdown())
            logger.debug("✓ Event bus shutdown")
            
            # Close database
            logger.debug("Closing database...")
            await asyncio.shield(close_db())
            logger.debug("✓ Database closed")
            
            logger.info("✅ Shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title="Oracle Server API",
    description="""
    🎮 **Oracle Server** - Advanced game log parsing and analytics API
    
    This API provides real-time parsing of game logs, tracking player sessions, 
    map completions, inventory changes, and statistics.
    
    ## Features
    
    * **Real-time WebSocket** - Live updates via WebSocket connection
    * **Map Tracking** - Complete map run analytics with filtering and pagination
    * **Session Management** - Track farming sessions with detailed metrics
    * **Inventory System** - Full inventory tracking per player
    * **Statistics** - Performance metrics and game analytics
    
    ## Getting Started
    
    1. Connect to WebSocket at `/ws` for real-time updates
    2. Query historical data via REST endpoints
    3. Use filters and pagination for efficient data retrieval
    """,
    version="1.0.0",
    contact={
        "name": "Oracle Server",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "status",
            "description": "Server health and status monitoring"
        },
        {
            "name": "maps",
            "description": "Map completion tracking and analytics. Query, filter, and manage completed map runs."
        },
        {
            "name": "sessions",
            "description": "Farming session management. Track player sessions with aggregated statistics."
        },
        {
            "name": "inventory",
            "description": "Player inventory tracking. View current inventory state per player."
        },
        {
            "name": "items",
            "description": "Item management. CRUD operations for game items."
        },
        {
            "name": "stats",
            "description": "Statistics control and management operations."
        },
        {
            "name": "websocket",
            "description": "Real-time WebSocket connections for live updates."
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(maps.router)
app.include_router(market.router)
app.include_router(sessions.router)
app.include_router(inventory.router)
app.include_router(items.router)
app.include_router(stats.router)
app.include_router(websocket.router)
app.include_router(players.router)
app.include_router(system.router)


@app.get(
    "/",
    tags=["status"],
    summary="Root health check",
    description="Basic health check endpoint to verify the server is running."
)
async def root():
    """Root endpoint - basic health check."""
    return {"status": "OK", "message": "Oracle Server is running"}


@app.get(
    "/status",
    tags=["status"],
    summary="Detailed server status",
    description="Get comprehensive server status including loaded parsers, services, and pipeline health."
)
async def status(
    router: Router = Depends(get_router),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """Get detailed server status."""
    global reader_task
    
    # Check the status of the log pipeline task
    reader_status = "Not Started"
    if reader_task:
        if reader_task.done():
            # If completed, it means there was an error or it was cancelled
            reader_status = f"Finished (Cancelled: {reader_task.cancelled()}, Exception: {reader_task.exception() is not None})"
        else:
            # Task is still running
            reader_status = "Running and Monitoring"

    return {
        "status": "OK", 
        "log_reader_status": reader_status,
        "loaded_parsers": router.get_loaded_parsers() if router else [],
        "loaded_services": service_manager.get_loaded_services() if service_manager else []
    }


if __name__ == "__main__":
    server_config = config.get("server")
    host = server_config.get("host", "127.0.0.1")
    port = server_config.get("port", 8000)
    
    # Detect if running from PyInstaller executable
    is_frozen = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
    
    logger.info(f"🚀 Starting server on {host}:{port}")
    
    # Configure uvicorn with proper shutdown handling
    config_kwargs = {
        "app": app,
        "host": host,
        "port": port,
        "reload": False if is_frozen else True,
        "log_config": None,  # Use our logger
        "access_log": False
    }
    
    # Use string reference for reload mode to enable hot reload
    if not is_frozen and config_kwargs["reload"]:
        config_kwargs["app"] = "Oracle.server:app"
        # Add config.toml to reload watch
        config_kwargs["reload_includes"] = ["*.toml"]
    
    # Setup signal handler for clean shutdown on Windows
    def signal_handler(sig, frame):
        logger.info("🛑 Received interrupt signal, shutting down...")
        # Force exit after timeout
        import time
        def force_exit():
            time.sleep(5)
            logger.warning("⚠️ Forcing exit after timeout")
            import os
            os._exit(0)
        
        t = threading.Thread(target=force_exit, daemon=True)
        t.start()
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        uvicorn.run(**config_kwargs)
    except OSError as e:
        if "address already in use" in str(e).lower() or "only one usage" in str(e).lower():
            logger.error(f"❌ Port {port} is already in use. Please close the other application or change the port in config.toml")
            logger.error(f"   Error details: {e}")
            sys.exit(1)
        else:
            logger.error(f"❌ Network error: {e}")
            raise
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        logger.trace(e)
        sys.exit(1)
