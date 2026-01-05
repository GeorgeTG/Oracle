"""System control endpoints."""

import asyncio
import os
import signal
from fastapi import APIRouter
from Oracle.tooling.logger import Logger

router = APIRouter(prefix="/system", tags=["system"])
logger = Logger("SystemAPI")


@router.post("/restart")
async def restart_server():
    """Restart the server process."""
    logger.warning("🔄 Server restart requested via API")
    
    # Schedule restart after response is sent
    async def do_restart():
        await asyncio.sleep(0.5)  # Small delay to ensure response is sent
        logger.warning("🔄 Restarting server...")
        # Send SIGTERM to self for graceful shutdown
        os.kill(os.getpid(), signal.SIGTERM)
    
    asyncio.create_task(do_restart())
    
    return {"message": "Server restart initiated"}


@router.get("/tasks")
async def get_tasks():
    """Get information about all running asyncio tasks."""
    all_tasks = asyncio.all_tasks()
    current_task = asyncio.current_task()
    
    tasks_info = []
    
    for task in all_tasks:
        if task == current_task:
            continue  # Skip the current API request task
        
        name = task.get_name()
        coro = task.get_coro()
        
        # Get coroutine info
        coro_name = coro.__name__ if hasattr(coro, '__name__') else str(coro)
        coro_frame = coro.cr_frame if hasattr(coro, 'cr_frame') else None
        
        status = "RUNNING" if not task.done() else "DONE"
        
        task_data = {
            "name": name,
            "status": status,
            "coroutine": coro_name,
            "location": None
        }
        
        # If we have frame info, show where it's waiting
        if coro_frame and not task.done():
            filename = coro_frame.f_code.co_filename
            lineno = coro_frame.f_lineno
            func_name = coro_frame.f_code.co_name
            task_data["location"] = {
                "file": filename,
                "line": lineno,
                "function": func_name
            }
        
        tasks_info.append(task_data)
    
    return {
        "total_tasks": len(tasks_info),
        "tasks": tasks_info
    }
