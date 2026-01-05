"""
Dynamic PYZ Module Loader
Loads services and parsers from .pyz archives at runtime
"""
import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Type
import logging

logger = logging.getLogger(__name__)


class ModuleLoader:
    """Loads Python modules from .pyz archives"""
    
    def __init__(self, modules_dir: Path):
        self.modules_dir = Path(modules_dir)
        self.loaded_modules: Dict[str, Any] = {}
        
    def load_pyz_module(self, pyz_path: Path) -> Any:
        """Load a module from a .pyz archive"""
        module_name = pyz_path.stem
        
        try:
            # Add pyz archive to sys.path
            pyz_str = str(pyz_path)
            if pyz_str not in sys.path:
                sys.path.insert(0, pyz_str)
            
            # Import the module directly from the pyz
            module = __import__(module_name)
            
            logger.info(f"Loaded module: {module_name} from {pyz_path}")
            return module
                
        except Exception as e:
            logger.error(f"Failed to load {pyz_path}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def load_services(self, base_class: Type = None) -> Dict[str, Any]:
        """Load all service modules from services/*.pyz"""
        services_dir = self.modules_dir / "services"
        services = {}
        
        if not services_dir.exists():
            logger.warning(f"Services directory not found: {services_dir}")
            return services
        
        for pyz_file in services_dir.glob("*.pyz"):
            module = self.load_pyz_module(pyz_file)
            if module:
                # If base_class provided, find subclasses
                if base_class:
                    for name, obj in module.__dict__.items():
                        if (isinstance(obj, type) and 
                            issubclass(obj, base_class) and 
                            obj is not base_class):
                            services[pyz_file.stem] = obj
                            logger.info(f"Found service class: {name} in {pyz_file.stem}")
                            break
                else:
                    services[pyz_file.stem] = module
        
        logger.info(f"Loaded {len(services)} services")
        return services
    
    def load_parsers(self, base_class: Type = None) -> Dict[str, Any]:
        """Load all parser modules from parsers/*.pyz"""
        parsers_dir = self.modules_dir / "parsers"
        parsers = {}
        
        if not parsers_dir.exists():
            logger.warning(f"Parsers directory not found: {parsers_dir}")
            return parsers
        
        for pyz_file in parsers_dir.glob("*.pyz"):
            module = self.load_pyz_module(pyz_file)
            if module:
                # If base_class provided, find subclasses
                if base_class:
                    for name, obj in module.__dict__.items():
                        if (isinstance(obj, type) and 
                            issubclass(obj, base_class) and 
                            obj is not base_class):
                            parsers[pyz_file.stem] = obj
                            logger.info(f"Found parser class: {name} in {pyz_file.stem}")
                            break
                else:
                    parsers[pyz_file.stem] = module
        
        logger.info(f"Loaded {len(parsers)} parsers")
        return parsers
    
    def load_all_modules(self, 
                        service_base_class: Type = None,
                        parser_base_class: Type = None) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Load both services and parsers"""
        services = self.load_services(service_base_class)
        parsers = self.load_parsers(parser_base_class)
        return services, parsers


# Convenience function
def create_loader(modules_path: str = None) -> ModuleLoader:
    """Create a ModuleLoader instance"""
    if modules_path is None:
        # Default to modules directory relative to this file
        base_path = Path(__file__).parent.parent.parent.parent
        modules_path = base_path / "modules"
    
    return ModuleLoader(Path(modules_path))
