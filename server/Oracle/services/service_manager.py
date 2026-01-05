# Oracle/services/service_manager.py

import pkgutil
import importlib
import traceback
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import glob
import sys

from Oracle.parsing.parsers.events.parser_event import ParserEvent
from Oracle.services.event_bus import EventBus
from Oracle.services.service_base import ServiceBase
from Oracle.services.loaders import get_loader
from Oracle.tooling.logger import Logger
from Oracle.tooling.singleton import Singleton


logger = Logger("ServiceManager")

@Singleton
class ServiceManager:
    """
    Manages the lifecycle and dispatching of services.
    Dynamically loads services from the Oracle.services package.
    Supports dependency resolution with versioning.
    """
    _event_bus: EventBus

    def __init__(self, event_bus: EventBus):
        self.services: List[ServiceBase] = []
        self._event_bus = event_bus
        self._service_registry: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self):
        """Initialize and load all services."""
        await self._load_services()

    def _parse_version_requirement(self, requirement: str) -> Tuple[str, str, str]:
        """
        Parse version requirement like '>1.0.0', '==2.0', '<=3.1.0'
        Returns: (operator, version_string, normalized_operator)
        """
        match = re.match(r'([><=!]+)(.+)', requirement.strip())
        if not match:
            return "==", requirement.strip(), "=="
        
        op = match.group(1)
        ver = match.group(2).strip()
        return op, ver, op

    def _parse_version(self, ver: str) -> Tuple[int, ...]:
        """Parse version string to tuple of integers for comparison."""
        try:
            return tuple(int(x) for x in ver.split('.'))
        except Exception:
            return (0,)

    def _check_version(self, installed_version: str, operator: str, required_version: str) -> bool:
        """Check if installed version satisfies requirement."""
        try:
            installed = self._parse_version(installed_version)
            required = self._parse_version(required_version)
            
            if operator == "==":
                return installed == required
            elif operator == ">":
                return installed > required
            elif operator == ">=":
                return installed >= required
            elif operator == "<":
                return installed < required
            elif operator == "<=":
                return installed <= required
            elif operator == "!=":
                return installed != required
            else:
                logger.warning(f"Unknown version operator: {operator}")
                return False
        except Exception as e:
            logger.error(f"Version comparison error: {e}")
            return False

    def _check_dependencies(self, service_class: type, metadata: Dict[str, Any]) -> bool:
        """Check if all dependencies are satisfied."""
        requires = metadata.get("requires", {})
        
        for dep_name, dep_version in requires.items():
            if dep_name not in self._service_registry:
                logger.error(
                    f"Service {metadata['name']} requires {dep_name} {dep_version} but it's not loaded"
                )
                return False
            
            dep_metadata = self._service_registry[dep_name]
            operator, required_ver, _ = self._parse_version_requirement(dep_version)
            
            if not self._check_version(dep_metadata["version"], operator, required_ver):
                logger.error(
                    f"Service {metadata['name']} requires {dep_name} {dep_version}, "
                    f"but version {dep_metadata['version']} is loaded"
                )
                return False
        
        return True

    async def _load_services(self):
        logger.info("Loading services...")
        
        # Get loader and dependencies
        loader = get_loader()
        self._service_registry = loader.get_dependencies()
        
        logger.info(f"Registered {len(self._service_registry)} services, checking dependencies...")
        
        # Instantiate services with dependency checks
        for service_name, metadata in self._service_registry.items():
            service_class = metadata["class"]
            
            if self._check_dependencies(service_class, metadata):
                try:
                    instance = service_class(self._event_bus)
                    await instance.initialize()  # Register event handlers
                    await instance.startup()     # Service-specific initialization
                    self.services.append(instance)
                    logger.info(f"🔧 Loaded service: {metadata['name']} v{metadata.get('version', '1.0.0')}")
                except Exception as e:
                    logger.error(f"Failed to instantiate {metadata['name']}: {e}")
                    logger.trace(e)
            else:
                logger.warning(f"⚠️  Skipped service {metadata['name']} due to unmet dependencies")
        
        logger.info(f"✅ Loaded {len(self.services)} services")
        for service in self.services:
            try:
                await service.post_startup()
                logger.debug(f"✅ Post-startup complete: {service.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error in post-startup for {service.__class__.__name__}: {e}")
                logger.trace(e)


    def get_loaded_services(self) -> List[str]:
        """Return list of loaded service class names."""
        return [svc.__class__.__name__ for svc in self.services]

    async def shutdown(self):
        """Shutdown all services gracefully."""
        logger.info("🛑 Shutting down all services...")
        for service in self.services:
            try:
                if hasattr(service, 'shutdown'):
                    await service.shutdown()
                    logger.debug(f"✅ Shutdown: {service.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error shutting down {service.__class__.__name__}: {e}")
        logger.info("✅ All services shutdown complete")
