#!/usr/bin/env python3
"""
Void LegendSmith vanilla model/texture scaffolder.

For every weapon in manifest.json, this COPIES (never moves) the existing
CIT art into the vanilla-native locations needed by the 1.21.4+ item-override
system (the one legendsmithCITgen-v2.py writes assets/minecraft/items/*.json
for):

    cit/items/weapons/<id>/<id>.json   -->  assets/minecraft/models/item/<id>.json
    cit/items/weapons/<id>/<id>.png    -->  assets/minecraft/textures/item/<id>.png

The original CIT files are left completely untouched -- they're still needed
for pre-1.21.4 versions via CIT Resewn's .properties files.

Two model styles are auto-detected from the source CIT model JSON:

  * "elements" style (full Blockbench Java Block/Item export): the elements/
    display blocks are copied over as-is, with just the texture reference
    swapped to point at the new vanilla texture path. Geometry, rotations,
    and display transforms are preserved exactly.

  * "generated" style (flat single-layer sprite, no "elements" key): emits
    a minimal {"parent": "minecraft:item/generated", "textures": {"layer0": ...}}
    model instead, since there's no geometry to carry over.

Emissive weapons (manifest "emissive": true) have their base texture AND
their CIT emissive texture (<id>_e.png) both copied over, keeping the same
"_e" suffix. The emissive texture is NOT yet wired into the generated model
JSON -- there's no confirmed vanilla mechanism to attach a second emissive
layer to an item model today -- but having the asset already in place means
only the model JSON needs a follow-up edit once/if vanilla adds native
support, rather than a full re-scaffold. If a weapon is marked emissive but
no matching <id>_e.png exists next to its CIT source, this is flagged and
only the base texture is copied.

Optionally, pass --namespace-subfolder (e.g. "legendsmith") to nest all
generated models/textures under models/item/<subfolder>/<id>.json and
textures/item/<subfolder>/<id>.png instead of directly under models/item/
and textures/item/. This keeps LegendSmith's files visually separated from
vanilla's own item files, and from any other pack/mod that also writes into
assets/minecraft/. The item-override files legendsmithCITgen-v2.py writes
into assets/minecraft/items/ are NOT affected by this -- those must stay at
a fixed path -- but their internal "model" field needs to reference the
subfolder too, so pass the SAME --namespace-subfolder value to both scripts
to keep everything in sync.

Usage:
    python legendsmithCITgen-v3.py
    python legendsmithCITgen-v3.py --manifest manifest.json \\
        --cit-root cit/items --assets-root assets/minecraft
    python legendsmithCITgen-v3.py --namespace-subfolder legendsmith
"""

import argparse
import json
import shutil
from pathlib import Path


def is_placeholder(name: str) -> bool:
    return "PUT" in name.upper() and "HERE" in name.upper()


def find_cit_source(cit_root: Path, category: str, wid: str):
    """Return (model_path, texture_path, emissive_texture_path_or_None)."""
    weapon_dir = cit_root / category / wid
    model_path = weapon_dir / f"{wid}.json"
    texture_path = weapon_dir / f"{wid}.png"
    if not model_path.exists() or not texture_path.exists():
        return None, None, None
    emissive_path = weapon_dir / f"{wid}_e.png"
    if not emissive_path.exists():
        emissive_path = None
    return model_path, texture_path, emissive_path


def build_vanilla_model(source_model: dict, texture_ref: str) -> dict:
    """Translate a CIT model JSON into a vanilla items/models/item model JSON.

    texture_ref is the full namespaced resource id the texture should be
    referenced by, e.g. "minecraft:item/hornet_needle" or
    "minecraft:item/legendsmith/hornet_needle" if using a subfolder.
    """
    if "elements" in source_model:
        # Full Blockbench export -- carry geometry + display over untouched,
        # just repoint every texture variable to the new path.
        new_model = dict(source_model)
        new_model["textures"] = {
            key: texture_ref
            for key in source_model.get("textures", {"0": None}).keys()
        }
        # Blockbench exports commonly use "particle" too -- keep it pointed
        # at the same texture if present.
        if "particle" in source_model.get("textures", {}):
            new_model["textures"]["particle"] = texture_ref
        return new_model
    else:
        # Flat sprite -- simplest possible vanilla model.
        return {
            "parent": "minecraft:item/generated",
            "textures": {
                "layer0": texture_ref
            }
        }


def process_weapon(weapon: dict, cit_root: Path, assets_root: Path, subfolder: str):
    wid = weapon["id"]
    name = weapon["name"]
    category = weapon.get("category", "weapons")
    emissive = weapon.get("emissive", False)

    if is_placeholder(name):
        print(f"  ! skip '{wid}' -- placeholder name")
        return "skipped"

    model_src, texture_src, emissive_src = find_cit_source(cit_root, category, wid)
    if model_src is None:
        print(f"  ! skip '{wid}' -- no CIT art found at {cit_root / category / wid}")
        return "missing"

    if emissive and emissive_src is None:
        print(f"  ! flag '{wid}' -- emissive=true but no {wid}_e.png found next to "
              f"the CIT source; copying base texture only.")

    # subfolder="" keeps the old flat layout (models/item/<id>.json). A
    # non-empty subfolder gives each weapon its own folder, mirroring the
    # existing cit/items/weapons/<id>/<id>.json layout:
    #   models/item/<subfolder>/<id>/<id>.json
    #   textures/item/<subfolder>/<id>/<id>.png
    # -- and the model's own texture reference must match the same path.
    rel = f"{subfolder}/{wid}/{wid}" if subfolder else wid
    texture_ref = f"minecraft:item/{rel}"

    models_out = assets_root / "models" / "item" / subfolder / wid if subfolder \
        else assets_root / "models" / "item"
    textures_out = assets_root / "textures" / "item" / subfolder / wid if subfolder \
        else assets_root / "textures" / "item"
    models_out.mkdir(parents=True, exist_ok=True)
    textures_out.mkdir(parents=True, exist_ok=True)

    # Copy base texture.
    shutil.copy2(texture_src, textures_out / f"{wid}.png")

    # Copy the emissive texture too, keeping the same "_e" suffix CIT uses,
    # so it's already sitting in place the moment vanilla adds a native
    # emissive-layer mechanism. It's not wired into the model below yet --
    # there's no confirmed vanilla mechanism to attach it to today -- but
    # having the asset copied now means only the model JSON needs updating
    # later, not a full re-scaffold.
    emissive_copied = False
    if emissive and emissive_src is not None:
        shutil.copy2(emissive_src, textures_out / f"{wid}_e.png")
        emissive_copied = True

    # Translate + write model.
    source_model = json.loads(model_src.read_text(encoding="utf-8"))
    vanilla_model = build_vanilla_model(source_model, texture_ref)
    (models_out / f"{wid}.json").write_text(
        json.dumps(vanilla_model, indent=2) + "\n", encoding="utf-8"
    )

    style = "elements" if "elements" in source_model else "generated"
    emissive_note = " (+ emissive texture copied, not yet wired into model)" if emissive_copied else ""
    print(f"  [{category}] '{wid}' -- {style} model -> models/item/{rel}.json, "
          f"texture -> textures/item/{rel}.png{emissive_note}")
    return "ok"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="manifest.json", type=Path)
    parser.add_argument("--cit-root", default="cit/items", type=Path,
                         help="Existing CIT folder to READ from (never modified)")
    parser.add_argument("--assets-root", default="assets/minecraft", type=Path,
                         help="Vanilla assets/minecraft folder to WRITE into")
    parser.add_argument("--namespace-subfolder", default="", type=str,
                         help="Optional subfolder to nest models/textures under "
                              "(e.g. 'legendsmith'). Pass the SAME value to "
                              "legendsmithCITgen-v2.py to keep model references in sync.")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    weapons = manifest.get("weapons", [])

    dest_desc = (f"{args.assets_root}/models/item/{args.namespace_subfolder}/ + "
                 f"{args.assets_root}/textures/item/{args.namespace_subfolder}/"
                 if args.namespace_subfolder else
                 f"{args.assets_root}/models/item/ + {args.assets_root}/textures/item/")
    print(f"Scaffolding {len(weapons)} weapon(s) from {args.cit_root}/ into {dest_desc} ...")

    counts = {"ok": 0, "skipped": 0, "missing": 0}
    for weapon in weapons:
        result = process_weapon(weapon, args.cit_root, args.assets_root, args.namespace_subfolder)
        counts[result] = counts.get(result, 0) + 1

    print(f"Done. {counts['ok']} scaffolded, {counts['skipped']} skipped "
          f"(placeholder), {counts['missing']} missing CIT source art.")
    print("Reminder: original cit/items/ files were NOT touched.")


if __name__ == "__main__":
    main()