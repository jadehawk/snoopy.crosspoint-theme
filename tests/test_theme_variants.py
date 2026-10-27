import importlib.util
import json
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from PIL import ImageOps
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
        # The Star Wars conversion uses ImageOps.fit to crop edge-to-edge.
        # Any return to ImageOps.pad would produce white sleep-screen borders.
        prepare_sleep = MODULE.prepare_sleep_grayscale
        def checked_sleep(root):
            with patch.object(ImageOps, "pad", side_effect=AssertionError("sleep screens must not be letterboxed")), \
                 patch.object(ImageOps, "fit", wraps=ImageOps.fit) as cover:
                images = prepare_sleep(root)
                assert cover.call_count == 20, "all 10 sleep scenes need an X3 and X4+ full-bleed crop"
                return images
        with patch.object(MODULE, "prepare_sleep_grayscale", side_effect=checked_sleep):
            cls.zips=MODULE.build(ROOT,Path(cls.temp.name),"0.1.19")

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
                self.assertEqual(manifest["target_resolution"],dict(zip(("width","height"),size)))
                self.assertEqual(names,{prefix+n for n in manifest["files"]} |
                                 {n for n in names if "/sleep/" in n})
                self.assertLessEqual(len(names),64)
                self.assertEqual(scene["assets"]["sleep_art"],"themes/snoopy/sleep")
                self.assertEqual(len([p for p in names if "/sleep/" in p]),10)
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
        with patch.object(ImageOps, "pad", side_effect=AssertionError("USB must not be letterboxed")), \
             patch.object(ImageOps, "fit", wraps=ImageOps.fit) as cover:
            paths = prepare_usb_grayscale.create(ROOT)
            self.assertEqual(cover.call_count, 2)
        self.assertEqual(set(paths), {"x3", "x4plus"})

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
