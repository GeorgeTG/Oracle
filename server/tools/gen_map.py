#!/usr/bin/env python3
"""
Script to generate en_id_map_table.json from map_ids.txt

Format of map_ids.txt:
--- Area Name
map_id
map_asset_name
map_en_name

(repeat)

Output format:
{
    "map_id": {
        "name": "map_en_name",
        "asset": "map_asset_name",
        "area": "Area Name"
    },
    ...
}
"""

import json
from pathlib import Path


def parse_map_ids(file_path: Path) -> dict:
    """Parse map_ids.txt and return a dictionary of map data."""
    
    maps = {}
    current_area = None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.rstrip() for line in f]
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check for area header
        if line.startswith('---'):
            current_area = line[3:].strip()
            i += 1
            continue
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Parse map entry (3 lines: id, asset, name)
        if i + 2 < len(lines):
            map_id = line
            map_asset = lines[i + 1].strip()
            map_name = lines[i + 2].strip()
            
            if map_id and map_asset and map_name:
                maps[map_id] = {
                    "name": map_name,
                    "asset": map_asset,
                    "area": current_area or "Unknown"
                }
            
            i += 3
        else:
            i += 1
    
    return maps


def main():
    # Get the server root directory (parent of tools/)
    script_dir = Path(__file__).parent
    server_root = script_dir.parent
    
    # Input and output paths
    input_file = server_root / "map_ids.txt"
    output_file = server_root / "en_id_map_table.json"
    
    if not input_file.exists():
        print(f"Error: {input_file} not found!")
        return
    
    # Parse the map data
    print(f"Reading {input_file}...")
    maps = parse_map_ids(input_file)
    
    # Write JSON output
    print(f"Writing {len(maps)} maps to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(maps, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Successfully generated {output_file}")
    print(f"  Total maps: {len(maps)}")
    
    # Show sample
    if maps:
        sample_id = list(maps.keys())[0]
        print(f"\nSample entry:")
        print(f"  {sample_id}: {maps[sample_id]}")


if __name__ == "__main__":
    main()
