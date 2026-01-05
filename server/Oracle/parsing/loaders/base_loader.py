"""Base loader for parser modules."""

from abc import ABC, abstractmethod
from typing import List, Type
from pathlib import Path


class BaseLoader(ABC):
    """Abstract base class for parser module loaders."""

    @abstractmethod
    def load_parsers(self) -> List[Type]:
        """
        Load and return all parser classes.
        
        Returns:
            List of parser class types
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
    def reload_parsers(self) -> List[Type]:
        """
        Reload all parser modules and return updated parser classes.
        
        Returns:
            List of parser class types
        """
        pass
