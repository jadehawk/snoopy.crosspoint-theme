"""Build one verified device-sized Snoopy theme ZIP per display profile.

The 10 source sleep images are translated to compact native 2bpp BMPs separately for
each resolution. USB grayscale images and CPB fallback remain ordinary manifest
assets. No cross-resolution galleries or legacy 1-bit sleep art are distributed.
"""
import argparse
import copy
import json
import re
import zipfile
from pathlib import Path

try:
    from prepare_sleep_grayscale import create as prepare_sleep_grayscale
except ModuleNotFoundError:  # Importlib-loaded unit tests use the repository root.
    from tools.prepare_sleep_grayscale import create as prepare_sleep_grayscale

PROFILES = {"x3": (528, 792), "x4plus": (480, 800)}


def build(root: Path, output: Path, version: str) -> list[Path]:
    package = root / "snoopy.crosspoint-theme"
    master = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    original = json.loads((package / "themes/snoopy/theme.json").read_text(encoding="utf-8"))
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    assert master["name"] == "snoopy"
    sleep_variants = prepare_sleep_grayscale(root)
    # Generate each screen's real four-tone USB BMP from the original illustration.
    try:
        from prepare_usb_grayscale import create as prepare_usb_grayscale
    except ModuleNotFoundError:
        from tools.prepare_usb_grayscale import create as prepare_usb_grayscale
    usb_gray_paths = prepare_usb_grayscale(root)
    results = []
    for variant, (width, height) in PROFILES.items():
        theme = copy.deepcopy(original)
        assets = theme["assets"]
        for key in tuple(assets):
            if key.endswith("_touch"):
                if variant == "x4plus":
                    role = key[:-6]
                    if role in assets:
                        assets[role] = copy.deepcopy(assets[key])
                else:
                    assets.pop(key)
        if variant == "x3":
            theme["styles"].pop("menu_footer_touch_asset", None)
        assets["sleep_art"] = "themes/snoopy/sleep"
        assets.pop("sleep_art_touch", None)
        assets["usb_gray_art"] = usb_gray_paths[variant]
        referenced = {value for role, value in assets.items() if role != "sleep_art"}
        assert all(isinstance(value, str) for value in referenced)
        sleep_images = sleep_variants[variant]
        assert len(sleep_images) == 10
        manifest = copy.deepcopy(master)
        manifest["version"] = version
        manifest["target_resolution"] = {"width": width, "height": height}
        theme_path = "themes/snoopy/theme.json"
        common = [name for name in master["files"]
                  if not name.endswith(".cpb") and name not in usb_gray_paths.values()]
        manifest["files"] = sorted(set(common) | referenced)
        assert theme_path in manifest["files"]
        assert all((package / file).is_file() for file in manifest["files"])
        expected = {
            f"themes/snoopy/assets/{p.name}"
            for p in (package / "themes/snoopy/assets").glob("*.cpb")
            if (p.name.endswith("-touch.cpb") == (variant == "x4plus"))
        }
        assert {v for v in referenced if v.endswith(".cpb")} == expected
        output.mkdir(parents=True, exist_ok=True)
        archive_path = output / f"snoopy-{variant}-{version}.crosspoint-theme.zip"

        def data(name):
            if name == "manifest.json":
                return (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
            if name == theme_path:
                return (json.dumps(theme, indent=2, ensure_ascii=False) + "\n").encode()
            raw = (package / name).read_bytes()
            if name.endswith(".md"):
                return raw.replace(master["version"].encode(), version.encode())
            return raw

        # X3 has no PSRAM; its streaming DEFLATE path needs a contiguous
        # 32-KiB inflate window, which often cannot be allocated after TLS.
        # Stored entries copy directly to SD in 1-KiB chunks. Compact 2bpp
        # BMPs keep the uncompressed archive well within firmware limits.
        method = zipfile.ZIP_STORED if variant == "x3" else zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(archive_path, "w", method,
                             compresslevel=None if method == zipfile.ZIP_STORED else 9) as archive:
            for name in sorted(set(manifest["files"]) | set(sleep_images)):
                archive.writestr(
                    "snoopy.crosspoint-theme/" + name,
                    sleep_images[name] if name in sleep_images else data(name),
                )
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            expected_names = {
                "snoopy.crosspoint-theme/" + name
                for name in set(manifest["files"]) | set(sleep_images)
            }
            assert names == expected_names
        results.append(archive_path)
        print(
            f"{variant}: {archive_path.name} ({archive_path.stat().st_size} bytes, "
            f"{len(manifest['files'])} core files and {len(sleep_images)} grayscale sleep BMPs)"
        )
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "dist")
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    build(args.root, args.output, args.version)
