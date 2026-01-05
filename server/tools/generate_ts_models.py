#!/usr/bin/env python3
"""
Generate TypeScript models from Python dataclasses, ParserEvent, and ServiceEvent classes.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FieldInfo:
    name: str
    type_hint: str
    optional: bool = False
    default_value: Optional[str] = None


@dataclass
class ClassInfo:
    name: str
    fields: List[FieldInfo]
    base_class: Optional[str] = None
    module_path: str = ""


class TypeScriptGenerator:
    """Generate TypeScript interfaces from Python classes."""
    
    # Python type to TypeScript type mapping
    TYPE_MAP = {
        'str': 'string',
        'int': 'number',
        'float': 'number',
        'bool': 'boolean',
        'datetime': 'string',  # ISO string
        'Dict': 'Record',
        'List': 'Array',
        'Optional': '',  # Handle separately
        'Any': 'any',
        'None': 'null',
    }
    
    def __init__(self, server_root: Path, ui_models_dir: Path):
        self.server_root = server_root
        self.ui_models_dir = ui_models_dir
        self.classes: Dict[str, ClassInfo] = {}
        self.enums: Dict[str, List[str]] = {}
    
    def parse_type_hint(self, type_node) -> Tuple[str, bool]:
        """Parse AST type hint and return (ts_type, is_optional)."""
        if type_node is None:
            return 'any', False
        
        if isinstance(type_node, ast.Name):
            py_type = type_node.id
            ts_type = self.TYPE_MAP.get(py_type, py_type)
            return ts_type, False
        
        if isinstance(type_node, ast.Constant):
            if type_node.value is None:
                return 'null', False
            return 'any', False
        
        if isinstance(type_node, ast.Subscript):
            # Handle generic types like Optional[str], List[int], Dict[str, int]
            if isinstance(type_node.value, ast.Name):
                generic_type = type_node.value.id
                
                if generic_type == 'Optional':
                    inner_type, _ = self.parse_type_hint(type_node.slice)
                    return inner_type, True
                
                elif generic_type == 'List':
                    inner_type, _ = self.parse_type_hint(type_node.slice)
                    return f'{inner_type}[]', False
                
                elif generic_type == 'Dict':
                    if isinstance(type_node.slice, ast.Tuple):
                        key_type, _ = self.parse_type_hint(type_node.slice.elts[0])
                        val_type, _ = self.parse_type_hint(type_node.slice.elts[1])
                        return f'Record<{key_type}, {val_type}>', False
                    return 'Record<string, any>', False
        
        if isinstance(type_node, ast.BinOp):
            # Handle Union types (Type1 | Type2)
            if isinstance(type_node.op, ast.BitOr):
                left_type, left_opt = self.parse_type_hint(type_node.left)
                right_type, right_opt = self.parse_type_hint(type_node.right)
                
                # Check if it's Optional (Type | None)
                if right_type == 'null':
                    return left_type, True
                if left_type == 'null':
                    return right_type, True
                
                return f'{left_type} | {right_type}', left_opt or right_opt
        
        return 'any', False
    
    def extract_class_info(self, node: ast.ClassDef, module_path: str) -> Optional[ClassInfo]:
        """Extract class information from AST node."""
        # Check if it's a dataclass or inherits from ParserEvent/ServiceEvent
        is_dataclass = False
        for dec in node.decorator_list:
            # Check for @dataclass or @dataclass(...)
            if isinstance(dec, ast.Name) and dec.id == 'dataclass':
                is_dataclass = True
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == 'dataclass':
                is_dataclass = True
        
        base_classes = [base.id for base in node.bases if isinstance(base, ast.Name)]
        is_event = any(cls in ['ParserEvent', 'ServiceEvent'] for cls in base_classes)
        
        if not (is_dataclass or is_event):
            return None
        
        fields = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                
                # Skip private fields
                if field_name.startswith('_'):
                    continue
                
                ts_type, is_optional = self.parse_type_hint(item.annotation)
                
                # Check for default value
                default_value = None
                if item.value:
                    if isinstance(item.value, ast.Constant):
                        default_value = repr(item.value.value)
                    elif isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name):
                        if item.value.func.id == 'field':
                            # Handle field(default_factory=...)
                            is_optional = True
                
                fields.append(FieldInfo(
                    name=field_name,
                    type_hint=ts_type,
                    optional=is_optional or default_value is not None,
                    default_value=default_value
                ))
        
        base_class = base_classes[0] if base_classes else None
        
        return ClassInfo(
            name=node.name,
            fields=fields,
            base_class=base_class,
            module_path=module_path
        )
    
    def extract_enum_info(self, node: ast.ClassDef) -> Optional[List[str]]:
        """Extract enum values from Enum class."""
        # Check if it inherits from Enum or str
        base_classes = [base.id for base in node.bases if isinstance(base, ast.Name)]
        if 'Enum' not in base_classes and 'str' not in base_classes:
            return None
        
        values = []
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith('_'):
                        values.append(target.id)
        
        return values if values else None
    
    def scan_python_files(self):
        """Scan all Python files for dataclasses and events."""
        for py_file in self.server_root.rglob('*.py'):
            # Skip __pycache__ and test files
            if '__pycache__' in str(py_file) or 'test' in py_file.name:
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                module_path = str(py_file.relative_to(self.server_root))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Try to extract class info
                        class_info = self.extract_class_info(node, module_path)
                        if class_info:
                            self.classes[class_info.name] = class_info
                        
                        # Try to extract enum info
                        enum_values = self.extract_enum_info(node)
                        if enum_values:
                            self.enums[node.name] = enum_values
            
            except Exception as e:
                print(f"Warning: Failed to parse {py_file}: {e}")
    
    def generate_typescript_interface(self, class_info: ClassInfo) -> str:
        """Generate TypeScript interface from ClassInfo."""
        lines = []
        
        # Add comment with source
        lines.append(f"// Generated from {class_info.module_path}")
        
        # Check if it extends another interface
        extends = ""
        if class_info.base_class and class_info.base_class in self.classes:
            extends = f" extends {class_info.base_class}"
        
        lines.append(f"export interface {class_info.name}{extends} {{")
        
        for field in class_info.fields:
            optional_marker = "?" if field.optional else ""
            lines.append(f"  {field.name}{optional_marker}: {field.type_hint};")
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def generate_typescript_enum(self, enum_name: str, values: List[str]) -> str:
        """Generate TypeScript enum."""
        lines = [f"export enum {enum_name} {{"]
        
        for value in values:
            lines.append(f"  {value} = '{value}',")
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def generate_all(self):
        """Generate all TypeScript files."""
        # Create output directory
        self.ui_models_dir.mkdir(parents=True, exist_ok=True)
        
        # Group classes by category
        parser_events = []
        service_events = []
        models = []
        
        for name, info in self.classes.items():
            if info.base_class == 'ParserEvent':
                parser_events.append(info)
            elif info.base_class == 'ServiceEvent':
                service_events.append(info)
            elif 'Event' in name:
                # Events without explicit base class
                if 'parsing' in info.module_path.lower():
                    parser_events.append(info)
                else:
                    service_events.append(info)
            else:
                # All other dataclasses (MapData, InventoryItem, etc.)
                models.append(info)
        
        # Generate parser events file
        if parser_events:
            self._generate_file('parser-events.ts', parser_events, ['ParserEventType'])
        
        # Generate service events file
        if service_events:
            self._generate_file('service-events.ts', service_events, ['ServiceEventType'])
        
        # Generate models file (always generate, even if empty)
        self._generate_file('models.ts', models, [])
        
        # Generate enums file
        if self.enums:
            self._generate_enums_file()
        
        print(f"✅ Generated TypeScript models in {self.ui_models_dir}")
        print(f"   - {len(parser_events)} parser events")
        print(f"   - {len(service_events)} service events")
        print(f"   - {len(models)} models")
        print(f"   - {len(self.enums)} enums")
    
    def _generate_file(self, filename: str, classes: List[ClassInfo], enums_to_include: List[str]):
        """Generate a single TypeScript file."""
        output_file = self.ui_models_dir / filename
        
        lines = [
            "// Auto-generated TypeScript models",
            "// Do not edit manually - run tools/generate_ts_models.py to regenerate",
            "",
        ]
        
        # Add enum imports if needed
        if enums_to_include:
            lines.append(f"import {{ {', '.join(enums_to_include)} }} from './enums';")
            lines.append("")
        
        # Generate interfaces
        for class_info in sorted(classes, key=lambda c: c.name):
            lines.append(self.generate_typescript_interface(class_info))
            lines.append("")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
    
    def _generate_enums_file(self):
        """Generate enums.ts file."""
        output_file = self.ui_models_dir / 'enums.ts'
        
        lines = [
            "// Auto-generated TypeScript enums",
            "// Do not edit manually - run tools/generate_ts_models.py to regenerate",
            "",
        ]
        
        for enum_name, values in sorted(self.enums.items()):
            lines.append(self.generate_typescript_enum(enum_name, values))
            lines.append("")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))


def main():
    # Get paths relative to tools directory
    script_dir = Path(__file__).parent
    server_root = script_dir.parent / "Oracle"
    ui_models_dir = script_dir.parent.parent / "ui" / "Oracle" / "src" / "app" / "models"
    
    print(f"🔍 Scanning Python files in {server_root}")
    print(f"📝 Generating TypeScript models to {ui_models_dir}")
    print()
    
    generator = TypeScriptGenerator(server_root, ui_models_dir)
    generator.scan_python_files()
    generator.generate_all()
    
    print()
    print("✨ Done!")


if __name__ == "__main__":
    main()
