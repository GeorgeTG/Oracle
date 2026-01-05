import inspect
import pkgutil
from pathlib import Path
from Oracle.parsing.parsers.events.parser_event import ParserEvent
from Oracle.parsing.parsers.events.parser_event_type import ParserEventType

# Export base classes
__all__ = ["ParserEvent", "ParserEventType"]

# Dynamically discover and import all ParserEvent subclasses
_models = {}
_package_dir = Path(__file__).parent

for _, module_name, _ in pkgutil.iter_modules([str(_package_dir)]):
    if module_name in ("parser_event", "parser_event_type", "model_base") or module_name.startswith("_"):
        continue
    
    module = __import__(f"Oracle.parsing.parsers.events.{module_name}", fromlist=["*"])
    
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if (
            issubclass(obj, ParserEvent) 
            and obj is not ParserEvent 
            and obj.__module__ == module.__name__
        ):
            _models[name] = obj
            globals()[name] = obj

# Add discovered models to __all__
__all__.extend(_models.keys())
