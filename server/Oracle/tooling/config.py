"""
Configuration management using TOML files.
Singleton pattern for global config access.
"""

import toml
from pathlib import Path
from typing import Any, Dict, Optional
from Oracle.tooling.paths import get_config_path


class Config:
    """Singleton configuration manager using TOML."""
    
    _instance: Optional["Config"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_config'):
            self._config: Dict[str, Any] = {}
            self._loaded = False
    
    def load(self, config_file: str = "config.toml"):
        """Load configuration from TOML file."""
        if self._loaded:
            return
        
        config_path = get_config_path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = toml.load(f)
        
        self._loaded = True
    
    def get(self, section: str) -> Dict[str, Any]:
        """
        Get a configuration section.
        
        Args:
            section: Section name (e.g., "server", "database", "logging")
        
        Returns:
            Dictionary with section configuration
        
        Example:
            config = Config.instance()
            server_config = config.get("server")
            port = server_config["port"]
        """
        if not self._loaded:
            self.load()
        
        return self._config.get(section, {})
    
    def get_value(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value.
        
        Args:
            section: Section name
            key: Configuration key
            default: Default value if not found
        
        Returns:
            Configuration value or default
        
        Example:
            config = Config.instance()
            port = config.get_value("server", "port", 8000)
        """
        section_config = self.get(section)
        return section_config.get(key, default)
    
    def reload(self):
        """Reload configuration from file."""
        self._loaded = False
        self.load()
    
    @property
    def all(self) -> Dict[str, Any]:
        """Get all configuration."""
        if not self._loaded:
            self.load()
        return self._config
