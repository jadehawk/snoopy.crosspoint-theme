"""Build one self-contained installable theme ZIP for each display resolution.

Source is the generated combined authoring payload; each output rewrites
the same scene manifest to point only at that device's bitmap resources.
No device name is baked into firmware and both ZIPs keep one stable name.
"""
import argparse
import copy
import json
import re
import zipfile
from pathlib import Path

PROFILES = {"x3": (528, 792), "x4plus": (480, 800)}

def build(root: Path, output: Path, version: str) -> list[Path]:
    package = root / "snoopy.crosspoint-theme"
    master = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    original = json.loads((package / "themes/snoopy/theme.json").read_text(encoding="utf-8"))
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    assert master["name"] == "snoopy"
    results = []
    for variant, (width, height) in PROFILES.items():
        theme = copy.deepcopy(original)
        assets = theme["assets"]
        for key in tuple(assets):
            if key.endswith("_touch"):
                if variant == "x4plus":
                    root_role = key[:-6]
                    if root_role in assets:
                        assets[root_role] = copy.deepcopy(assets[key])
                else:
                    assets.pop(key)
        if variant == "x3":
            theme["styles"].pop("menu_footer_touch_asset", None)
        # A sleep gallery is a directory, not a JSON list. It can contain any
        # number of CPBs within the verified archive and expanded-size budgets.
        sleep_sources = (original["assets"]["sleep_art_touch"] if variant == "x4plus"
                         else original["assets"]["sleep_art"])
        assets.pop("sleep_art_touch", None)
        assets["sleep_art"] = "themes/snoopy/sleep"
        # Keep the other optional touch aliases: they control full-height Home
        # footer sizing and boot artwork without duplicate binary files.
        referenced = set()
        for role, value in assets.items():
            if role == "sleep_art":
                continue
            assert isinstance(value, str), role
            referenced.add(value)
        sleep_images = {}
        for source in sleep_sources:
            basename = Path(source).name.replace("-touch.cpb", ".cpb")
            target = "themes/snoopy/sleep/" + basename
            assert target not in sleep_images
            sleep_images[target] = (package / source).read_bytes()
        manifest = copy.deepcopy(master)
        manifest["version"] = version
        manifest["target_resolution"] = {"width": width, "height": height}
        rel_theme = "themes/snoopy/theme.json"
        common = [name for name in master["files"] if not name.endswith(".cpb")]
        manifest["files"] = sorted(set(common) | referenced)
        assert rel_theme in manifest["files"]
        assert all((package / file).is_file() for file in manifest["files"])
        expected = {f"themes/snoopy/assets/{p.name}" for p in
                    (package / "themes/snoopy/assets").glob("*.cpb")
                    if not p.name.startswith(("sleep-night", "sleep-scene-")) and
                    p.name.endswith("-touch.cpb") == (variant == "x4plus")}
        assert set(referenced) == expected, (variant, sorted(set(referenced)^expected))
        output.mkdir(parents=True, exist_ok=True)
        filename = output / f"snoopy-{variant}-{version}.crosspoint-theme.zip"
        def data(name):
            if name == "manifest.json":
                return (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
            if name == rel_theme:
                return (json.dumps(theme, indent=2, ensure_ascii=False) + "\n").encode()
            raw = (package / name).read_bytes()
            if name.endswith(".md"):
                return raw.replace(master["version"].encode(), version.encode())
            return raw
        with zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in sorted(set(manifest["files"]) | set(sleep_images)):
                archive.writestr(f"snoopy.crosspoint-theme/{name}",
                                 sleep_images[name] if name in sleep_images else data(name))
        with zipfile.ZipFile(filename) as archive:
            names = archive.namelist()
            assert len(names) == len(manifest["files"]) + len(sleep_images)
            assert set(names) == {f"snoopy.crosspoint-theme/{f}" for f in
                                  (set(manifest["files"]) | set(sleep_images))}
        results.append(filename)
        print(f"{variant}: {filename.name} ({filename.stat().st_size} bytes, {len(manifest['files'])} core and {len(sleep_images)} sleep CPBs)")
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "dist")
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    build(args.root, args.output, args.version)
