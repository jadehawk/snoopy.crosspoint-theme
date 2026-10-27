"""Fast structural/CRC checks; official HALO contract validator is also required."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import struct
import unittest
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'snoopy.crosspoint-theme'
GALLERY=ROOT/'source-art/Snoopy_Woodstock_22_Sleep_Scenes_X3_X4Pro.zip'
VERSION='0.1.14'
ZIPDIR=ROOT/'dist'

class ThemeChecks(unittest.TestCase):
    def test_package_shape(self):
        m=json.loads((PACK/'manifest.json').read_text())
        self.assertEqual(m['kind'],'theme-pack')
        self.assertEqual(m['name'],'snoopy')
        self.assertEqual(m['version'],VERSION)
        self.assertEqual(m['themes'][0]['id'],'snoopy')
        self.assertEqual(len(m['files']),len(set(m['files'])))
        self.assertEqual(sorted(m['files']),sorted(str(p.relative_to(PACK)).replace('\\','/') for p in PACK.rglob('*') if p.is_file()))
        self.assertLess(sum((PACK/p).stat().st_size for p in m['files']),4*1024*1024)
        self.assertLessEqual((PACK/'README.md').stat().st_size,2048)
        self.assertTrue((PACK/'README.md').read_bytes().isascii())
        self.assertEqual(len(m['themes']),1)

    def test_reference_and_ops(self):
        m=json.loads((PACK/'themes/snoopy/theme.json').read_text())
        self.assertEqual(m['reference'],{'width':528,'height':792,'adapt':'scale-to-fit'})
        self.assertEqual(m['styles']['settings_navigation'],'list')
        self.assertEqual(m['styles']['header_back_style'],'both')
        self.assertIn('theme.header-back.v1', json.loads((PACK/'manifest.json').read_text())['themes'][0]['requires'])
        for role in ('header_emblem','home_hero','home_footer','screen_art','boot_art','sleep_art'):
            alternate = 'screen_art_touch' if role == 'screen_art' else role + '_touch'
            self.assertIn(role,m['assets'])
            self.assertIn(alternate,m['assets'])
        self.assertNotEqual(m['assets']['home_hero'],m['assets']['home_hero_touch'])
        self.assertEqual(m['metrics']['homeRecentBooksCount'],1)
        self.assertGreaterEqual(m['metrics']['headerHeight'],58)
        self.assertLessEqual(sum(map(len,m['regions'].values())),48)
        self.assertTrue(all(len(ops)<=16 for ops in m['regions'].values()))
        self.assertEqual(m['regions']['home'][-1]['op'],'book-card')
        self.assertEqual(set(m['fonts']['ui']), {'small','regular','large','display'})
        self.assertEqual(m['regions']['home'][-1]['variant'],'cover')
        header_emblem = next(op for op in m['regions']['header'] if op['op']=='bitmap')
        self.assertGreaterEqual(header_emblem['max_width'], 76)
        self.assertGreaterEqual(header_emblem['max_height'], 58)
        self.assertIn('theme.book-cover.v1',
                      json.loads((PACK/'manifest.json').read_text())['themes'][0]['requires'])
        self.assertEqual(m['metrics']['homeCoverTileHeight'],320)
        self.assertEqual(m['metrics']['menuRowHeight'],54)
        self.assertEqual(m['metrics']['menuSpacing'],3)
        self.assertTrue(m['styles']['menu_double_outline'])
        self.assertEqual(m['regions']['screen'][0]['asset'], 'screen_art')
        self.assertNotIn('screen_background',m['regions'])
        self.assertEqual(m['regions']['home'][1]['fit'],'contain')
        self.assertEqual(m['styles']['menu_footer_touch_asset'],'home_footer_touch')
        self.assertIn('screen_art_touch',m['assets'])
        self.assertEqual(m['regions']['screen'][0]['paint'], 'ink-only')
        self.assertLessEqual(m['regions']['screen'][0]['max_height'], 128)
        self.assertEqual(m['styles']['menu_footer_asset'],'home_footer')
        self.assertIn('theme.menu-decoration.v1',json.loads((PACK/'manifest.json').read_text())['themes'][0]['requires'])
        self.assertIn('theme.screen-decoration.v1', json.loads((PACK/'manifest.json').read_text())['themes'][0]['requires'])
        self.assertNotIn('theme.screen-background.v1', json.loads((PACK/'manifest.json').read_text())['themes'][0]['requires'])
        self.assertTrue(m['metrics']['listTitleBold'])
        caps=json.loads((PACK/'manifest.json').read_text())['themes'][0]['requires']
        self.assertIn('theme.settings-navigation.v1',caps)
        self.assertIn('theme.composition.v1',caps)

    def test_cpb_crc_dimensions(self):
        for name,wh in [('header-emblem.cpb',(76,58)),('header-emblem-touch.cpb',(76,58)),('home-hero.cpb',(528,320)),('home-hero-touch.cpb',(480,320)),('home-footer.cpb',(528,46)),('screen-decoration.cpb',(528,84)),('home-footer-touch.cpb',(480,80)),('screen-decoration-touch.cpb',(480,128)),
                        ('boot-art.cpb',(320,235)),('boot-art-touch.cpb',(480,270)),('sleep-night.cpb',(528,792)),('sleep-night-touch.cpb',(480,800))]:
            with self.subTest(name=name):
                blob=(PACK/'themes/snoopy/assets'/name).read_bytes()
                sig,version,flags,w,h,stride,length,crc=struct.unpack('<4sBBHHHII',blob[:20])
                self.assertEqual((sig,version,flags),(b'CPTB',1,1))
                self.assertEqual((w,h),wh)
                self.assertEqual(stride,(w+7)//8)
                self.assertEqual(length,stride*h)
                self.assertEqual(len(blob),length+20)
                self.assertLessEqual(length,128*1024)
                self.assertEqual(crc,zlib.crc32(blob[20:]) & 0xffffffff)
                if w % 8:
                    pad_mask=(1 << (8-(w%8))) - 1
                    self.assertTrue(all((blob[20+(y+1)*stride-1]&pad_mask)==0 for y in range(h)))

    def test_touch_art_comes_from_separate_compositions(self):
        builder=(ROOT/'tools/build.py').read_text()
        self.assertIn("touch_home = Image.new('RGB', (480, HOME_TILE_HEIGHT)",builder)
        self.assertIn("touch_boot = Image.new('RGB', (480, 270)",builder)
        self.assertIn("touch_sleep_canvas = Image.new('RGB', (480, 800)",builder)
        self.assertNotIn("touch_home = home.resize",builder)
        self.assertNotIn("touch_boot = boot.resize",builder)
        self.assertNotIn("touch_sleep = sleep_mono.resize",builder)

    def test_sleep_gallery_contract(self):
        scene=json.loads((PACK/'themes/snoopy/theme.json').read_text())
        base=scene['assets']['sleep_art']
        touch=scene['assets']['sleep_art_touch']
        if GALLERY.is_file():
            self.assertEqual(len(base),23)
            self.assertEqual(len(touch),23)
            self.assertEqual(len(set(base)),23)
            self.assertEqual(len(set(touch)),23)
            for n in range(1,23):
                for suffix,dimensions in (('',(528,792)),('-touch',(480,800))):
                    cpb=PACK/'themes/snoopy/assets'/f'sleep-scene-{n:02d}{suffix}.cpb'
                    self.assertTrue(cpb.is_file())
                    blob=cpb.read_bytes()
                    header=struct.unpack('<4sBBHHHII',blob[:20])
                    self.assertEqual(header[0],b'CPTB')
                    self.assertEqual(header[3:5],dimensions)
                    self.assertEqual(header[7],zlib.crc32(blob[20:]) & 0xffffffff)
        else:
            self.assertEqual(len(base),1)
            self.assertEqual(touch,['themes/snoopy/assets/sleep-night-touch.cpb'])

    def test_original_x3_footers_remain_byte_identical(self):
        for name, expected in (
            ('home-footer.cpb', '0bfab335609cb3a51c79ba25829dfb18c354d7faebd2343d9d6eb2d2a45aa77c'),
            ('screen-decoration.cpb', '7ae168bff79a315f58b310ee9f5ee2504afeb6ee632615bd3b0ad5fe96c17e5f'),
            ('header-emblem.cpb', '84658cee3e969a61d0afbfa82014b834474250e0ab2cad2206ad7b9febd98da2'),
            ('home-hero.cpb', '5f5f007c52dfdd4d6f056a53a72ff0c36c6e00e94674af04f863f115302dbb74'),
            ('boot-art.cpb', '4fa9020730f094862775ecc49e4bd024563fa576a0263edb778f2a6d124f3156'),
        ):
            with self.subTest(name=name):
                asset=(PACK/'themes/snoopy/assets'/name).read_bytes()
                self.assertEqual(hashlib.sha256(asset).hexdigest(), expected)

    def test_approved_sleep_art_unchanged(self):
        blob=(PACK/'themes/snoopy/assets/sleep-night.cpb').read_bytes()
        self.assertEqual(hashlib.sha256(blob).hexdigest().upper(),
                         'AC0D60975065650FBACE7ECE7E0927F192A8042B1153054BE10C2C9DA87A47AD')

    def test_dynapuff_ellipsis_in_every_ui_font(self):
        for name in ('ui-small', 'ui-regular', 'ui-large', 'display'):
            with self.subTest(name=name):
                blob=(PACK/'themes/snoopy/fonts'/f'{name}.cpfont').read_bytes()
                self.assertEqual(blob[:6], b'CPFONT')
                count=struct.unpack_from('<I', blob, 36)[0]
                intervals=[struct.unpack_from('<III', blob, 64+i*12) for i in range(count)]
                glyph_index=next((pos+0x2026-first for first,last,pos in intervals
                                  if first<=0x2026<=last), None)
                self.assertIsNotNone(glyph_index)
                glyph=struct.unpack_from('<BBHhhH2xI', blob, 64+count*12+glyph_index*16)
                self.assertGreater(glyph[0]*glyph[1], 0)
                self.assertGreater(glyph[5], 0)

    def test_touch_footer_scene_has_illustration(self):
        # The X4 footer is the enlarged X3 Snoopy doghouse, not wallpaper art.
        blob=(PACK/'themes/snoopy/assets/screen-decoration-touch.cpb').read_bytes()
        pixels=blob[20:]
        stride=60
        def ink(x0,y0,x1,y1):
            return sum(bool(pixels[y*stride+x//8] & (128 >> (x % 8)))
                       for y in range(y0,y1) for x in range(x0,x1))
        self.assertGreater(ink(290,0,480,113),900)  # doghouse at right
        self.assertGreater(ink(0,115,480,128),250)  # same grass baseline
        self.assertFalse((PACK/'themes/snoopy/assets/screen-background.cpb').exists())
        home=(PACK/'themes/snoopy/assets/home-footer-touch.cpb').read_bytes()[20:]
        def home_ink(x0,y0,x1,y1):
            return sum(bool(home[y*60+x//8] & (128 >> (x % 8)))
                       for y in range(y0,y1) for x in range(x0,x1))
        self.assertGreater(home_ink(0,8,100,78),140)  # Woodstock
        self.assertGreater(home_ink(105,21,380,59),900)  # slogan
        self.assertGreater(home_ink(380,9,480,78),140)  # cloud
        self.assertEqual(home_ink(110,0,370,19),0)  # slogan is beside the art, not above
        builder=(ROOT/'tools/build.py').read_text()
        self.assertNotIn('touch_screen = background.crop',builder)
        self.assertNotIn('touch_footer.paste(background.crop',builder)

    def test_install_zip_only_payload(self):
        for variant, size in (("x3", (528, 792)), ("x4plus", (480, 800))):
            with self.subTest(variant=variant), zipfile.ZipFile(
                ZIPDIR/f"snoopy-{variant}-{VERSION}.crosspoint-theme.zip") as archive:
                root="snoopy.crosspoint-theme/"
                manifest=json.loads(archive.read(root+"manifest.json"))
                theme=json.loads(archive.read(root+"themes/snoopy/theme.json"))
                self.assertEqual(manifest["name"],"snoopy")
                self.assertEqual(manifest["version"],VERSION)
                self.assertEqual(manifest["target_resolution"],{
                    "width":size[0],"height":size[1]})
                self.assertEqual(set(archive.namelist()),{
                    root+f for f in manifest["files"]} |
                    {n for n in archive.namelist() if "/sleep/" in n})
                self.assertEqual(theme["assets"]["sleep_art"], "themes/snoopy/sleep")
                self.assertEqual(len([n for n in archive.namelist() if "/sleep/" in n]), 23)
                self.assertEqual(len(manifest["files"]), 13)

if __name__=='__main__': unittest.main()
