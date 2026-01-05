import os
import sys
import zipfile
import importlib.util
import json
from pathlib import Path

# Ensure project root is in sys.path for Oracle imports
project_root = str((Path(__file__).parent.parent.parent.parent / "server").resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)
print(f"[pack_modules] sys.path[0] = {sys.path[0]}")

print("[pack_modules] Starting module packing...")

# Output to deploy/output/server/modules/[parsers|services]
DEPLOY_ROOT = Path(__file__).parent.parent.parent / "output" / "server" / "modules"
SERVICES_DST = DEPLOY_ROOT / "services"
PARSERS_DST = DEPLOY_ROOT / "parsers"

BASE = Path(__file__).parent.parent.parent.parent / "server"
SERVICES_SRC = BASE / "Oracle" / "services"
PARSERS_SRC = BASE / "Oracle" / "parsing" / "parsers"

for d in [SERVICES_DST, PARSERS_DST]:
    d.mkdir(parents=True, exist_ok=True)
    print(f"[pack_modules] Ensured directory: {d}")

def is_service_module(pyfile):
    print(f"[pack_modules] Checking service: {pyfile}")
    spec = importlib.util.spec_from_file_location("_mod", pyfile)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"[pack_modules] Import error in {pyfile}: {e}")
        return False
    for obj in mod.__dict__.values():
        try:
            from Oracle.services.service_base import ServiceBase
            if isinstance(obj, type) and issubclass(obj, ServiceBase) and obj is not ServiceBase:
                print(f"[pack_modules] {pyfile} contains ServiceBase subclass: {obj.__name__}")
                return True
        except Exception as e:
            print(f"[pack_modules] Error checking class in {pyfile}: {e}")
            continue
    return False

def is_parser_module(pyfile):
    print(f"[pack_modules] Checking parser: {pyfile}")
    spec = importlib.util.spec_from_file_location("_mod", pyfile)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"[pack_modules] Import error in {pyfile}: {e}")
        return False
    for obj in mod.__dict__.values():
        try:
            from Oracle.parsing.parsers.parser_base import ParserBase
            if isinstance(obj, type) and issubclass(obj, ParserBase) and obj is not ParserBase:
                print(f"[pack_modules] {pyfile} contains ParserBase subclass: {obj.__name__}")
                return True
        except Exception as e:
            print(f"[pack_modules] Error checking class in {pyfile}: {e}")
            continue
    return False

def pack(src, dst, is_valid, module_type):
    """Pack Python modules into .pyz archives"""
    for pyfile in src.glob("*.py"):
        if pyfile.name.startswith("__"): 
            continue
        print(f"[pack_modules] Considering {pyfile}")
        if is_valid(pyfile):
            pyzname = dst / (pyfile.stem + ".pyz")
            specname = dst / (pyfile.stem + ".spec.json")
            
            try:
                # Load module to extract metadata
                spec = importlib.util.spec_from_file_location("_mod", pyfile)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                
                # Extract __PARSER__ or __SERVICE__ metadata
                metadata = None
                for obj in mod.__dict__.values():
                    if isinstance(obj, type):
                        if hasattr(obj, '__PARSER__'):
                            metadata = obj.__PARSER__
                            break
                        elif hasattr(obj, '__SERVICE__'):
                            metadata = obj.__SERVICE__
                            break
                
                # Create .pyz archive
                with zipfile.ZipFile(pyzname, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    # Add the main module
                    zf.write(pyfile, arcname=pyfile.name)
                    
                    # Create __main__.py to make it executable
                    main_content = f"""# Auto-generated __main__.py for {pyfile.name}
import sys
from pathlib import Path

# Add current archive to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and expose the module
from {pyfile.stem} import *

if __name__ == "__main__":
    print(f"Module {pyfile.stem} loaded from PYZ archive")
"""
                    zf.writestr("__main__.py", main_content)
                
                print(f"[pack_modules] Packed {pyfile.name} -> {pyzname}")
                
                # Create .spec.json if metadata found
                if metadata:
                    with open(specname, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    print(f"[pack_modules] Created spec: {specname}")
                else:
                    print(f"[pack_modules] Warning: No metadata found for {pyfile.name}")
                    
            except Exception as e:
                print(f"[pack_modules] Failed to create pyz {pyfile}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[pack_modules] Skipped {pyfile} (no valid class)")

pack(SERVICES_SRC, SERVICES_DST, is_service_module, "service")
pack(PARSERS_SRC, PARSERS_DST, is_parser_module, "parser")
print("[pack_modules] Packing complete.")
