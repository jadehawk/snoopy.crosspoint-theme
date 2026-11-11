"""Build publishable Snoopy X3 and X4+ ZIPs from committed theme sources.

The checked-in theme.json, manifest.json, artwork, and documentation are the
source of truth, including approved resolution-specific sleep BMPs. Release
packaging writes ZIPs only; tools/build.py is strictly for authoring artwork.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import zipfile
from pathlib import Path

try:
    from prepare_sleep_grayscale import decode_native_2bpp_bmp
except ModuleNotFoundError:
    from tools.prepare_sleep_grayscale import decode_native_2bpp_bmp

PROFILES = {"x3": (528, 792), "x4plus": (480, 800)}
PREFIX = "snoopy.crosspoint-theme/"
USB_GRAY = {
    "x3": "themes/snoopy/assets/usb-connected.bmp",
    "x4plus": "themes/snoopy/assets/usb-connected-touch.bmp",
}


def build(root: Path, output: Path, version: str | None = None) -> list[Path]:
    package = root / PREFIX.rstrip("/")
    master = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    original = json.loads((package / "themes/snoopy/theme.json").read_text(encoding="utf-8"))
    source_version = master["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", source_version):
        raise ValueError("Manifest version must be MAJOR.MINOR.PATCH")
    if version is not None and version != source_version:
        raise ValueError(f"Requested version {version} differs from manifest {source_version}")
    if master["name"] != "snoopy":
        raise ValueError("Expected Snoopy theme manifest")

    # All authored payload files must already exist; release never regenerates
    # the source config, theme art, fonts, README, or grayscale USB images.
    declared = set(master["files"])
    actual = {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file()}
    if declared != actual or len(declared) != len(master["files"]):
        raise ValueError(f"Manifest file list differs from committed payload: missing={sorted(declared-actual)}, "
                         f"undeclared={sorted(actual-declared)}")

    for profile, dimensions in PROFILES.items():
        gray = package / USB_GRAY[profile]
        image = decode_native_2bpp_bmp(gray.read_bytes())
        if image.size != dimensions or set(image.get_flattened_data()) != {0, 85, 170, 255}:
            raise ValueError(f"Invalid checked-in grayscale USB asset: {gray}")

    # Read the exact approved grayscale bytes for each display. Do not let
    # different Pillow versions silently regenerate different release images.
    sleep_variants = {}
    for profile, dimensions in PROFILES.items():
        images = {}
        for index in range(1, 11):
            filename = f"sleep-scene-{index:02d}.bmp"
            asset = root / "source-art" / "release-sleep" / profile / filename
            contents = asset.read_bytes()
            decoded = decode_native_2bpp_bmp(contents)
            if decoded.size != dimensions or set(decoded.get_flattened_data()) != {0, 85, 170, 255}:
                raise ValueError(f"Invalid approved {profile} sleep image: {asset}")
            images[f"themes/snoopy/sleep/{filename}"] = contents
        sleep_variants[profile] = images
    output.mkdir(parents=True, exist_ok=True)
    results = []

    for profile, (width, height) in PROFILES.items():
        scene = copy.deepcopy(original)
        assets = scene["assets"]
        for key in tuple(assets):
            if key.endswith("_touch"):
                if profile == "x4plus":
                    base = key[:-6]
                    if base in assets:
                        assets[base] = assets[key]
                else:
                    assets.pop(key)
        if profile == "x3":
            scene["styles"].pop("menu_footer_touch_asset", None)
        assets["sleep_art"] = "themes/snoopy/sleep"
        assets.pop("sleep_art_touch", None)
        assets["usb_gray_art"] = USB_GRAY[profile]
        # Keep the authored 528x792 reference and scale-to-fit policy on X4+.
        # Only selected assets and installed manifest resolution differ.

        referenced = {path for role, path in assets.items() if role != "sleep_art"}
        if not all(isinstance(path, str) for path in referenced):
            raise ValueError("Non-sleep artwork roles must reference a single file")
        expected_cpbs = {
            f"themes/snoopy/assets/{path.name}"
            for path in (package / "themes/snoopy/assets").glob("*.cpb")
            if path.name.endswith("-touch.cpb") == (profile == "x4plus")
        }
        if {path for path in referenced if path.endswith(".cpb")} != expected_cpbs:
            raise ValueError(f"Wrong artwork selection for {profile}")
        manifest = copy.deepcopy(master)
        manifest["target_resolution"] = {"width": width, "height": height}
        manifest["files"] = sorted(
            {name for name in declared if not name.endswith(".cpb") and name not in USB_GRAY.values()} | referenced
        )
        sleep_images = sleep_variants[profile]
        if len(sleep_images) != 10:
            raise ValueError(f"Expected ten sleep images for {profile}")

        replacements = {
            "manifest.json": (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
            "themes/snoopy/theme.json": (json.dumps(scene, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
        }
        entries = set(manifest["files"]) | set(sleep_images)
        if not all((package / name).is_file() for name in manifest["files"] if name not in replacements):
            raise ValueError(f"Manifest references missing {profile} source files")

        # X3 avoids the 32-KiB DEFLATE window on no-PSRAM devices. X4+
        # retains compressed entries. These are separate release assets.
        method = zipfile.ZIP_STORED if profile == "x3" else zipfile.ZIP_DEFLATED
        target = output / f"snoopy-{profile}-{source_version}.crosspoint-theme.zip"
        with zipfile.ZipFile(target, "w", method,
                             compresslevel=None if method == zipfile.ZIP_STORED else 9) as archive:
            for name in sorted(entries):
                info = zipfile.ZipInfo(PREFIX + name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = method
                info.external_attr = 0o100644 << 16
                blob = sleep_images.get(name)
                if blob is None:
                    blob = replacements.get(name)
                if blob is None:
                    blob = (package / name).read_bytes()
                archive.writestr(info, blob, compress_type=method,
                                 compresslevel=None if method == zipfile.ZIP_STORED else 9)
        with zipfile.ZipFile(target) as archive:
            if set(archive.namelist()) != {PREFIX + name for name in entries}:
                raise ValueError(f"Incorrect {profile} archive contents")
        results.append(target)
        print(f"{profile}: {target.name} ({target.stat().st_size} bytes, "
              f"{len(manifest['files'])} core files and {len(sleep_images)} sleep BMPs)")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "dist")
    args = parser.parse_args()
    build(args.root, args.output)


if __name__ == "__main__":
    main()
