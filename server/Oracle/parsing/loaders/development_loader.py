"""Development loader for parser modules - loads from source files."""

import importlib
import sys
from pathlib import Path
from typing import List, Type

from Oracle.parsing.loaders.base_loader import BaseLoader
from Oracle.parsing.parsers.parser_base import ParserBase


class DevelopmentLoader(BaseLoader):
    """Loads parsers from source .py files during development."""

    def __init__(self):
        self.parsers_path = Path(__file__).parent.parent / "parsers"
        self._loaded_modules = {}

    def get_modules_path(self) -> Path:
        """Get the path to the parsers source directory."""
        return self.parsers_path

    def load_parsers(self) -> List[Type[ParserBase]]:
        """
        Load parser classes from source .py files.
        
        Returns:
            List of parser class types
        """
        parsers = []
        
        for py_file in self.parsers_path.glob("*.py"):
            if py_file.stem.startswith("_") or py_file.stem == "base":
                continue
                
            module_name = f"Oracle.parsing.parsers.{py_file.stem}"
            
            try:
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                else:
                    module = importlib.import_module(module_name)
                    self._loaded_modules[py_file.stem] = module
                
                # Find ParserBase subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, ParserBase) and 
                        attr is not ParserBase):
                        parsers.append(attr)
                        
            except Exception as e:
                print(f"[DevelopmentLoader] Failed to load {py_file.stem}: {e}")
                
        return parsers

    def reload_parsers(self) -> List[Type[ParserBase]]:
        """
        Reload all parser modules from source.
        
        Returns:
            List of parser class types
        """
        # Reload all previously loaded modules
        for module_name, module in self._loaded_modules.items():
            try:
                importlib.reload(module)
            except Exception as e:
                print(f"[DevelopmentLoader] Failed to reload {module_name}: {e}")
        
        # Clear and reload
        self._loaded_modules.clear()
        return self.load_parsers()
