"""Test PYZ module loading"""
import sys
from pathlib import Path

# Add server to path
server_path = Path(__file__).parent.parent
sys.path.insert(0, str(server_path))

from Oracle.tooling.module_loader import create_loader

# Create loader pointing to the output modules
modules_path = Path(__file__).parent.parent / "deploy" / "output" / "server" / "modules"
print(f"Checking path: {modules_path}")
print(f"Path exists: {modules_path.exists()}")
loader = create_loader(str(modules_path))

print(f"\nLoading modules from: {modules_path}\n")

# Try to load services
print("=" * 60)
print("Loading Services...")
print("=" * 60)
from Oracle.services.service_base import ServiceBase
services = loader.load_services(ServiceBase)
print(f"\nFound {len(services)} services:")
for name, service_class in services.items():
    print(f"  + {name}: {service_class.__name__}")

# Try to load parsers
print("\n" + "=" * 60)
print("Loading Parsers...")
print("=" * 60)
from Oracle.parsing.parsers.parser_base import ParserBase
parsers = loader.load_parsers(ParserBase)
print(f"\nFound {len(parsers)} parsers:")
for name, parser_class in parsers.items():
    print(f"  + {name}: {parser_class.__name__}")

print("\n" + "=" * 60)
print(f"Total: {len(services)} services + {len(parsers)} parsers")
print("=" * 60)
