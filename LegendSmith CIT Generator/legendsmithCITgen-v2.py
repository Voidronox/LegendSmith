#!/usr/bin/env python3
"""
Void LegendSmith vanilla item-override generator.

Reads manifest.json (the SAME manifest generate_cit.py uses) and writes
assets/minecraft/items/<item_id>.json files using the vanilla
"minecraft:select" component-based model system (1.21.4+, no CIT Resewn
required). This is a third output format for the same weapon list --
generate_cit.py handles the two CIT Resewn .properties files, this script
handles the vanilla-native one.

Must live in the same folder as generate_cit.py -- it imports the shared
ITEM_REGISTRY and item_id() from it so both scripts always agree on which
materials/types exist and which era they belong to.

Every run fully overwrites every generated file. Edit manifest.json, not
these output files directly.

Usage:
    python generate_vanilla_items.py
    python generate_vanilla_items.py --manifest manifest.json --out path/to/assets/minecraft/items
"""

import argparse
import json
from pathlib import Path

from legendsmithCITgen import ITEM_REGISTRY, item_id

def is_placeholder(name: str) -> bool:
    return "PUT" in name.upper() and "HERE" in name.upper()


def build_cases(weapons, item_type):
    cases = []
    for weapon in weapons:
        if item_type not in weapon.get("types", []):
            continue
        name = weapon["name"]
        if is_placeholder(name):
            continue
        wid = weapon["id"]
        cases.append({
            "when": name,
            "model": {
                "type": "minecraft:model",
                "model": f"minecraft:item/{wid}"
            }
        })
    return cases


def write_item_file(item_type, material, weapons, out_dir: Path):
    iid = item_id(item_type, material)
    cases = build_cases(weapons, item_type)

    if cases:
        # At least one weapon targets this material/type -- safe to use
        # the "select" dispatcher.
        data = {
            "model": {
                "type": "minecraft:select",
                "property": "minecraft:component",
                "component": "minecraft:custom_name",
                "cases": cases,
                "fallback": {
                    "type": "minecraft:model",
                    "model": f"minecraft:item/{iid}"
                }
            }
        }
    else:
        # No weapons target this material/type yet. "minecraft:select"
        # requires a non-empty "cases" array -- an empty one fails to
        # parse entirely (not just falls back), which breaks the vanilla
        # item outright. Emit the plain vanilla model instead until a
        # weapon actually claims this slot.
        data = {
            "model": {
                "type": "minecraft:model",
                "model": f"minecraft:item/{iid}"
            }
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{iid}.json"
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return iid, len(cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="manifest.json", type=Path)
    parser.add_argument("--out", default="assets/minecraft/items", type=Path,
                         help="Output folder -- point this at your assets/minecraft/items folder")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    weapons = manifest.get("weapons", [])

    print(f"Generating vanilla item override files into {args.out}/ ...")
    written = 0
    empty = 0
    for item_type, materials in ITEM_REGISTRY.items():
        for material in materials:
            iid, n_cases = write_item_file(item_type, material, weapons, args.out)
            if n_cases == 0:
                empty += 1
            else:
                print(f"  {iid}.json -- {n_cases} weapon(s)")
            written += 1
    print(f"Done. {written} item files written ({empty} were fallback-only, no weapons matched yet).")


if __name__ == "__main__":
    main()
