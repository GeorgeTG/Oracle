"""Parser module loaders package."""

import sys
from Oracle.parsing.loaders.base_loader import BaseLoader
from Oracle.parsing.loaders.development_loader import DevelopmentLoader
from Oracle.parsing.loaders.production_loader import ProductionLoader


def get_loader() -> BaseLoader:
    """
    Get the appropriate loader based on execution environment.
    
    Returns:
        DevelopmentLoader if running from source,
        ProductionLoader if running as frozen executable (PyInstaller)
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        return ProductionLoader()
    else:
        # Running from source
        return DevelopmentLoader()


__all__ = [
    'BaseLoader',
    'DevelopmentLoader',
    'ProductionLoader',
    'get_loader',
]
