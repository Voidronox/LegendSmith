#!/usr/bin/env python3
"""
Void LegendSmith CIT generator.

Reads manifest.json (the source of truth) and writes out, for every weapon:
  cit/items/weapons/<id>/<id>.properties          (components-based, 1.20.5+)
  cit/items/weapons/<id>/<id>-legacy.properties    (nbt-based, pre-1.20.5)

It does NOT touch the .json model, .png texture, or .mcmeta files -- those
are hand-made art assets and are left completely alone.

Every run fully overwrites the two generated .properties files for every
weapon in the manifest. Do not hand-edit those two files directly; edit
manifest.json and rerun instead.

Usage:
    python generate_cit.py
    python generate_cit.py --manifest path/to/manifest.json --out path/to/cit/items/weapons
"""

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Item registry: for every weapon "type" this pack supports, list which
# materials exist and whether that (material, type) combo is old enough to
# exist in pre-1.20.5 NBT-naming versions ("legacy") or is components-only
# ("components" -- 1.20.5+, e.g. because the material or type itself was
# added after the components system existed).
#
# None as a material means the item has no material variants at all
# (e.g. mace is just "mace", not "iron_mace").
#
# Update this table when Mojang adds new materials or weapon types.
# ---------------------------------------------------------------------------

LEGACY = "legacy"
COMPONENTS_ONLY = "components"

ITEM_REGISTRY = {
    "sword": {
        "wooden": LEGACY, "stone": LEGACY, "iron": LEGACY,
        "golden": LEGACY, "diamond": LEGACY, "netherite": LEGACY,
        "copper": COMPONENTS_ONLY,
    },
    "axe": {
        "wooden": LEGACY, "stone": LEGACY, "iron": LEGACY,
        "golden": LEGACY, "diamond": LEGACY, "netherite": LEGACY,
        "copper": COMPONENTS_ONLY,
    },
    "pickaxe": {
        "wooden": LEGACY, "stone": LEGACY, "iron": LEGACY,
        "golden": LEGACY, "diamond": LEGACY, "netherite": LEGACY,
        "copper": COMPONENTS_ONLY,
    },
    "hoe": {
        "wooden": LEGACY, "stone": LEGACY, "iron": LEGACY,
        "golden": LEGACY, "diamond": LEGACY, "netherite": LEGACY,
        "copper": COMPONENTS_ONLY,
    },
    "shovel": {
        "wooden": LEGACY, "stone": LEGACY, "iron": LEGACY,
        "golden": LEGACY, "diamond": LEGACY, "netherite": LEGACY,
        "copper": COMPONENTS_ONLY,
    },
    # Spear was added in 1.21.11 -- entirely components-only, no legacy form.
    "spear": {
        "wooden": COMPONENTS_ONLY, "stone": COMPONENTS_ONLY,
        "copper": COMPONENTS_ONLY, "iron": COMPONENTS_ONLY,
        "golden": COMPONENTS_ONLY, "diamond": COMPONENTS_ONLY,
        "netherite": COMPONENTS_ONLY,
    },
    # Mace has no material variants -- single item id "mace".
    # Added in 1.20.5, same update that introduced components -- components-only.
    "mace": {
        None: COMPONENTS_ONLY,
    },
    # Bow and crossbow also have no material variants, but unlike mace they've
    # existed since well before 1.20.5, so they're valid in the legacy
    # NBT-naming era too.
    "bow": {
        None: LEGACY,
    },
    "crossbow": {
        None: LEGACY,
    },
    # Totem of Undying has no material variants -- single item id
    # "totem_of_undying" (not "totem"; the weapon "type" key IS the item id
    # here since item_id() just returns weapon_type when material is None).
    # Added in 1.11, long before components -- legacy-eligible.
    "totem_of_undying": {
        None: LEGACY,
    },
}


def item_id(weapon_type: str, material) -> str:
    if material is None:
        return weapon_type
    return f"{material}_{weapon_type}"


def collect_match_items(types: list[str]):
    """Return (components_items, legacy_items) for a weapon's allowed types."""
    components_items = []
    legacy_items = []
    for t in types:
        if t not in ITEM_REGISTRY:
            print(f"  ! warning: unknown type '{t}' -- skipping", file=sys.stderr)
            continue
        for material, era in ITEM_REGISTRY[t].items():
            iid = item_id(t, material)
            components_items.append(iid)
            if era == LEGACY:
                legacy_items.append(iid)
    return components_items, legacy_items


def build_properties(match_items, name_line):
    lines = [
        "type=item",
        f"matchItems={' '.join(match_items)}",
    ]
    return "\n".join(lines) + "\n"


def write_weapon(weapon: dict, out_dir: Path):
    wid = weapon["id"]
    name = weapon["name"]
    types = weapon.get("types", [])
    emissive = weapon.get("emissive", False)
    category = weapon.get("category", "weapons")

    if "PUT" in name.upper() and "HERE" in name.upper():
        print(f"  ! warning: '{wid}' still has a placeholder name -- skipping", file=sys.stderr)
        return

    components_items, legacy_items = collect_match_items(types)
    if not components_items:
        print(f"  ! warning: '{wid}' resolved to zero matchItems -- skipping", file=sys.stderr)
        return

    weapon_dir = out_dir / category / wid
    weapon_dir.mkdir(parents=True, exist_ok=True)

    asset_lines = [
        f"model=./{wid}.json",
        f"texture=./{wid}.png",
    ]
    if emissive:
        asset_lines.append(f"texture.emissive=./{wid}_e.png")

    # Components-based (1.20.5+) -- always written.
    components_path = weapon_dir / f"{wid}.properties"
    components_content = "\n".join([
        "type=item",
        f"matchItems={' '.join(components_items)}",
        *asset_lines,
        f"components.minecraft\\:custom_name=ipattern:*{name}*",
    ]) + "\n"
    components_path.write_text(components_content, encoding="utf-8")

    # Legacy NBT-based -- only written if this weapon has at least one
    # type/material combo old enough to exist pre-components.
    legacy_path = weapon_dir / f"{wid}-legacy.properties"
    if legacy_items:
        legacy_content = "\n".join([
            "type=item",
            f"matchItems={' '.join(legacy_items)}",
            *asset_lines,
            f"nbt.display.Name=ipattern:*{name}*",
        ]) + "\n"
        legacy_path.write_text(legacy_content, encoding="utf-8")
        print(f"  [{category}] wrote {wid}.properties ({len(components_items)} items) "
              f"+ {wid}-legacy.properties ({len(legacy_items)} items)")
    else:
        # No legacy-eligible items -- remove any stale legacy file from a
        # previous run instead of leaving outdated content behind.
        if legacy_path.exists():
            legacy_path.unlink()
        print(f"  [{category}] wrote {wid}.properties ({len(components_items)} items) "
              f"-- no legacy file (all types are components-only)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="manifest.json", type=Path)
    parser.add_argument("--out", default="cit/items", type=Path,
                         help="Output root -- point this at your optifine/cit/items folder. "
                              "Each weapon is written to <out>/<category>/<id>/, matching your "
                              "existing weapons/, bows/, etc. layout.")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    weapons = manifest.get("weapons", [])

    print(f"Generating {len(weapons)} weapon(s) into {args.out}/ ...")
    for weapon in weapons:
        write_weapon(weapon, args.out)
    print("Done.")


if __name__ == "__main__":
    main()
