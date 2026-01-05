"""Production loader for service modules - loads from .pyz archives."""

import sys
import importlib
from pathlib import Path
from typing import List, Type, Dict, Any

from Oracle.services.loaders.base_loader import BaseLoader
from Oracle.services.service_base import ServiceBase


class ProductionLoader(BaseLoader):
    """Loads services from .pyz archives in production (frozen) builds."""

    def __init__(self):
        # Production loader requires frozen build
        assert getattr(sys, 'frozen', False), "ProductionLoader can only be used in frozen builds"
        
        # Modules are in a modules/services directory next to the executable
        exe_dir = Path(sys.executable).parent
        self.modules_path = exe_dir / "modules" / "services"
        self._loaded_modules = {}
        self._service_registry: Dict[str, Dict[str, Any]] = {}

    def get_modules_path(self) -> Path:
        """Get the path to the .pyz modules directory."""
        return self.modules_path

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
        Load service classes from .pyz archives.
        
        Returns:
            List of service class types
        """
        services = []
        self._service_registry.clear()
        
        if not self.modules_path.exists():
            print(f"[ProductionLoader] Modules path not found: {self.modules_path}")
            return services
        
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
                print(f"[ProductionLoader] Failed to load {module_name}: {e}")
                
        return services

    def reload_services(self) -> List[Type[ServiceBase]]:
        """
        Reload is not supported in production builds.
        
        Returns:
            Previously loaded service classes
        """
        print("[ProductionLoader] Reload not supported in production mode")
        return self.load_services()
