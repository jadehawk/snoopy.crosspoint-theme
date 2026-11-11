import hashlib
import importlib.util
import json
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from PIL import Image, ImageOps
from tools.prepare_sleep_grayscale import decode_native_2bpp_bmp
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("theme_variants",ROOT/"tools/pack_theme_variants.py")
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class VariantPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        # Release packaging must not generate or alter checked-in artwork,
        # theme metadata, README files, or approved sleep BMPs.
        sources = [ROOT / "README.md", *(
            path for directory in ("snoopy.crosspoint-theme", "source-art/release-sleep")
            for path in (ROOT / directory).rglob("*") if path.is_file()
        )]
        before = {path: hashlib.sha256(path.read_bytes()).digest() for path in sources}
        cls.zips = MODULE.build(ROOT, Path(cls.temp.name))
        after = {path: hashlib.sha256(path.read_bytes()).digest() for path in sources}
        assert before == after, "Release packaging changed committed source files"

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_paired_assets_and_one_stable_id(self):
        for variant, size in (("x3",(528,792)),("x4plus",(480,800))):
            with self.subTest(variant=variant), zipfile.ZipFile(next(p for p in self.zips if f"-{variant}-" in p.name)) as z:
                prefix="snoopy.crosspoint-theme/"
                names=set(z.namelist())
                manifest=json.loads(z.read(prefix+"manifest.json"))
                scene=json.loads(z.read(prefix+"themes/snoopy/theme.json"))
                self.assertEqual(manifest["name"],"snoopy")
                self.assertEqual(scene["reference"], {"width":528,"height":792,"adapt":"scale-to-fit"})
                self.assertEqual(manifest["target_resolution"],dict(zip(("width","height"),size)))
                self.assertEqual(names,{prefix+n for n in manifest["files"]} |
                                 {n for n in names if "/sleep/" in n})
                # All non-metadata payload bytes must be the checked-in files,
                # never output silently recreated by an artwork generator.
                package = ROOT / "snoopy.crosspoint-theme"
                for name in manifest["files"]:
                    if name not in {"manifest.json", "themes/snoopy/theme.json"}:
                        self.assertEqual(z.read(prefix + name), (package / name).read_bytes())
                self.assertLessEqual(len(names),64)
                self.assertEqual(scene["assets"]["sleep_art"],"themes/snoopy/sleep")
                self.assertEqual(len([p for p in names if "/sleep/" in p]),10)
                for index in range(1, 11):
                    filename = f"sleep-scene-{index:02d}.bmp"
                    approved = ROOT / "source-art" / "release-sleep" / variant / filename
                    self.assertEqual(
                        z.read(prefix + "themes/snoopy/sleep/" + filename),
                        approved.read_bytes(),
                    )
                for role in ("header_emblem","home_hero","home_footer","screen_art","boot_art","sleep_art","usb_art","usb_gray_art"):
                    self.assertIn(role,scene["assets"])
                bitmap_paths=[n for n in manifest["files"] if n.endswith(".cpb")]
                self.assertEqual(len(bitmap_paths),6)
                for path in bitmap_paths:
                    header=z.read(prefix+path)[:20]
                    self.assertEqual(header[:4],b"CPTB")
                    # Source gallery should never include the other resolution.
                    self.assertEqual(path.endswith("-touch.cpb"),variant=="x4plus")
                sleep_path=prefix+"themes/snoopy/sleep/sleep-scene-01.bmp"
                sleep=z.read(sleep_path)
                self.assertEqual(sleep[:2], b'BM')
                self.assertEqual(int.from_bytes(sleep[28:30], 'little'), 2)
                if variant == "x3":
                    self.assertTrue(all(item.compress_type == zipfile.ZIP_STORED for item in z.infolist()))
                    self.assertLess(z.fp.seek(0, 2), 2 * 1024 * 1024)
                self.assertIn('theme.usb-grayscale.v1', manifest['themes'][0]['requires'])
                self.assertIn('theme.sleep-grayscale.v1', manifest['themes'][0]['requires'])
                gray_path=scene['assets']['usb_gray_art']
                self.assertIn(gray_path, manifest['files'])
                self.assertEqual(gray_path.endswith('-touch.bmp'), variant=='x4plus')
                usb_bytes = z.read(prefix + gray_path)
                bmp = decode_native_2bpp_bmp(usb_bytes)
                self.assertEqual(bmp.size, size)
                self.assertEqual(set(bmp.get_flattened_data()), {0, 85, 170, 255})
                self.assertEqual(int.from_bytes(usb_bytes[28:30], "little"), 2)
                # X3 must avoid 32-KiB inflate windows, USB included.
                if variant == "x3":
                    self.assertEqual(z.getinfo(prefix + gray_path).compress_type, zipfile.ZIP_STORED)

    def test_usb_converter_crops_not_pads(self):
        from tools import prepare_usb_grayscale
        with Image.open(prepare_usb_grayscale.SOURCE) as original, \
             patch.object(ImageOps, "pad", side_effect=AssertionError("USB must not be letterboxed")), \
             patch.object(ImageOps, "fit", wraps=ImageOps.fit) as cover:
            for size in MODULE.PROFILES.values():
                image = prepare_usb_grayscale.four_tone(original, size)
                self.assertEqual(image.size, size)
            self.assertEqual(cover.call_count, 2)

    def test_source_version_is_authoritative(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "differs from manifest"):
                MODULE.build(ROOT, Path(directory), "0.0.0")

    def test_workflows_match_halo_release_contract(self):
        release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        validate = (ROOT / ".github/workflows/validate-theme.yml").read_text(encoding="utf-8")
        self.assertIn('tags:\n      - "v*"', release)
        self.assertIn('gh release create', release)
        self.assertIn('git diff --exit-code', release)
        self.assertIn('python tools/pack_theme_variants.py', release)
        self.assertNotIn('tools/build.py', release)
        self.assertIn("pull_request:", validate)
        self.assertIn("git diff --exit-code", validate)
        self.assertFalse((ROOT / ".github/workflows/prepare-theme-variants.yml").exists())

    def test_no_duplicate_artwork(self):
        sources=[]
        for path in self.zips:
            with zipfile.ZipFile(path) as archive:
                names=[p for p in archive.namelist() if p.endswith(".cpb")]
                sources.append(set(names))
        # Core CPBs differ per display; sleep BMPs share filenames but not pixels.
        self.assertEqual(sources[0] & sources[1],
                         {p for p in sources[0] if '/sleep/' in p})
        self.assertEqual(len(sources[0] & sources[1]), 0)

if __name__=="__main__":
    unittest.main()
