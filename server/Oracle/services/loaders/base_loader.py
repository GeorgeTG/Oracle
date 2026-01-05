"""Base loader for service modules."""

from abc import ABC, abstractmethod
from typing import List, Type, Dict, Any, Tuple
from pathlib import Path


class BaseLoader(ABC):
    """Abstract base class for service module loaders."""

    @abstractmethod
    def load_services(self) -> List[Type]:
        """
        Load and return all service classes.
        
        Returns:
            List of service class types
        """
        pass

    @abstractmethod
    def get_dependencies(self) -> Dict[str, Dict[str, Any]]:
        """
        Get dependency information for all services.
        
        Returns:
            Dictionary mapping service name to metadata:
            {
                "ServiceName": {
                    "class": ServiceClass,
                    "version": "1.0.0",
                    "description": "...",
                    "requires": {"OtherService": ">=1.0.0"}
                }
            }
        """
        pass

    @abstractmethod
    def get_modules_path(self) -> Path:
        """
        Get the path to the modules directory.
        
        Returns:
            Path to modules directory
        """
        pass

    @abstractmethod
    def reload_services(self) -> List[Type]:
        """
        Reload all service modules and return updated service classes.
        
        Returns:
            List of service class types
        """
        pass
