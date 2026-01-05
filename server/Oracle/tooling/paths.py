# Oracle/tooling/paths.py
import os
import sys
from pathlib import Path


def get_base_path() -> Path:
    """
    Get the base path for the application.
    When running as PyInstaller exe, returns the directory containing the exe.
    When running as script, returns the project root.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return Path(sys.executable).parent
    else:
        # Running as script - go up from Oracle/tooling to project root
        return Path(__file__).parent.parent.parent


# Export REPO_ROOT for convenience
REPO_ROOT = get_base_path()


def get_config_path(filename: str) -> Path:
    """
    Get the full path to a config file.
    Looks for the file next to the exe (or in project root when running as script).
    """
    return get_base_path() / filename
