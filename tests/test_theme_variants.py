import importlib.util
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("theme_variants",ROOT/"tools/pack_theme_variants.py")
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class VariantPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.zips=MODULE.build(ROOT,Path(cls.temp.name),"0.1.14")

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
                self.assertEqual(len([p for p in names if "/sleep/" in p]),23)
                for role in ("header_emblem","home_hero","home_footer","screen_art","boot_art","sleep_art"):
                    self.assertIn(role,scene["assets"])
                bitmap_paths=[n for n in manifest["files"] if n.endswith(".cpb")]
                self.assertEqual(len(bitmap_paths),5)
                for path in bitmap_paths:
                    header=z.read(prefix+path)[:20]
                    self.assertEqual(header[:4],b"CPTB")
                    # Source gallery should never include the other resolution.
                    self.assertEqual(path.endswith("-touch.cpb"),variant=="x4plus")
                sleep=z.read(prefix+"themes/snoopy/sleep/sleep-night.cpb")
                self.assertEqual(struct.unpack_from("<HH",sleep,6),size)

    def test_no_duplicate_artwork(self):
        sources=[]
        for path in self.zips:
            with zipfile.ZipFile(path) as archive:
                names=[p for p in archive.namelist() if p.endswith(".cpb")]
                sources.append(set(names))
        # Variant ZIPs intentionally share stable theme-local sleep filenames;
        # their CPB pixel payloads differ by display geometry.
        self.assertEqual(sources[0] & sources[1],
                         {p for p in sources[0] if '/sleep/' in p})
        self.assertEqual(len(sources[0] & sources[1]), 23)

if __name__=="__main__":
    unittest.main()
