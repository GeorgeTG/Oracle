"""Development loader for service modules - loads from source files."""

import importlib
import sys
from pathlib import Path
from typing import List, Type, Dict, Any

from Oracle.services.loaders.base_loader import BaseLoader
from Oracle.services.service_base import ServiceBase


class DevelopmentLoader(BaseLoader):
    """Loads services from source .py files during development."""

    def __init__(self):
        self.services_path = Path(__file__).parent.parent
        self._loaded_modules = {}
        self._service_registry: Dict[str, Dict[str, Any]] = {}

    def get_modules_path(self) -> Path:
        """Get the path to the services source directory."""
        return self.services_path

    def get_dependencies(self) -> Dict[str, Dict[str, Any]]:
        """
        Get dependency information for all services.
        Loads services first if not already loaded.
        
        Returns:
            Dictionary mapping service name to metadata
        """
        if not self._service_registry:
            self.load_services()
        return self._service_registry

    def load_services(self) -> List[Type[ServiceBase]]:
        """
        Load service classes from source .py files.
        
        Returns:
            List of service class types
        """
        services = []
        self._service_registry.clear()
        
        for py_file in self.services_path.glob("*.py"):
            if py_file.stem.startswith("_") or py_file.stem in ["service_base", "event_bus", "service_manager"]:
                continue
                
            module_name = f"Oracle.services.{py_file.stem}"
            
            try:
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                else:
                    module = importlib.import_module(module_name)
                    self._loaded_modules[py_file.stem] = module
                
                # Find ServiceBase subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, ServiceBase) and 
                        attr is not ServiceBase):
                        
                        metadata = getattr(attr, "__SERVICE__", None)
                        if metadata:
                            service_name = metadata.get("name", attr.__name__)
                            self._service_registry[service_name] = {
                                "name": service_name,
                                "class": attr,
                                "version": metadata.get("version", "1.0.0"),
                                "description": metadata.get("description", ""),
                                "requires": metadata.get("requires", {})
                            }
                        else:
                            # Default metadata for services without __SERVICE__
                            self._service_registry[attr.__name__] = {
                                "name": attr.__name__,
                                "class": attr,
                                "version": "1.0.0",
                                "description": "",
                                "requires": {}
                            }
                        
                        services.append(attr)
                        
            except Exception as e:
                print(f"[DevelopmentLoader] Failed to load {py_file.stem}: {e}")
                
        return services

    def reload_services(self) -> List[Type[ServiceBase]]:
        """
        Reload all service modules from source.
        
        Returns:
            List of service class types
        """
        # Reload all previously loaded modules
        for module_name, module in self._loaded_modules.items():
            try:
                importlib.reload(module)
            except Exception as e:
                print(f"[DevelopmentLoader] Failed to reload {module_name}: {e}")
        
        # Clear and reload
        self._loaded_modules.clear()
        self._service_registry.clear()
        return self.load_services()
