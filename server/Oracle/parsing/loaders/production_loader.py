"""Production loader for parser modules - loads from .pyz archives."""

import sys
import importlib
from pathlib import Path
from typing import List, Type

from Oracle.parsing.loaders.base_loader import BaseLoader
from Oracle.parsing.parsers.parser_base import ParserBase


class ProductionLoader(BaseLoader):
    """Loads parsers from .pyz archives in production (frozen) builds."""

    def __init__(self):
        # Production loader requires frozen build
        assert getattr(sys, 'frozen', False), "ProductionLoader can only be used in frozen builds"
        
        # Modules are in a modules/parsers directory next to the executable
        exe_dir = Path(sys.executable).parent
        self.modules_path = exe_dir / "modules" / "parsers"
        self._loaded_modules = {}

    def get_modules_path(self) -> Path:
        """Get the path to the .pyz modules directory."""
        return self.modules_path

    def load_parsers(self) -> List[Type[ParserBase]]:
        """
        Load parser classes from .pyz archives.
        
        Returns:
            List of parser class types
        """
        parsers = []
        
        if not self.modules_path.exists():
            print(f"[ProductionLoader] Modules path not found: {self.modules_path}")
            return parsers
        
        for pyz_file in self.modules_path.glob("*.pyz"):
            module_name = pyz_file.stem
            
            try:
                # Add .pyz to sys.path if not already there
                pyz_path = str(pyz_file)
                if pyz_path not in sys.path:
                    sys.path.insert(0, pyz_path)
                
                # Import the module
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                else:
                    module = importlib.import_module(module_name)
                    self._loaded_modules[module_name] = module
                
                # Find ParserBase subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, ParserBase) and 
                        attr is not ParserBase):
                        parsers.append(attr)
                        
            except Exception as e:
                print(f"[ProductionLoader] Failed to load {module_name}: {e}")
                
        return parsers

    def reload_parsers(self) -> List[Type[ParserBase]]:
        """
        Reload is not supported in production builds.
        
        Returns:
            Previously loaded parser classes
        """
        print("[ProductionLoader] Reload not supported in production mode")
        return self.load_parsers()
