from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from pathlib import Path
import json, os, struct, zlib, zipfile, shutil, textwrap

OUT=Path(__file__).resolve().parent.parent
PKG=OUT/'snoopy.crosspoint-theme'
ASSETS=PKG/'themes/snoopy/assets'
SOURCE=OUT/'source-art'
PREV=OUT/'previews'
for folder in (ASSETS,SOURCE,PREV):folder.mkdir(parents=True,exist_ok=True)
# Cropped source art was taken from the user-provided concept and is bundled.
TOP=Image.open(SOURCE/'snoopy-reclining.png').convert('RGB')
SLEEP=Image.open(SOURCE/'snoopy-night-scene.png').convert('RGB')

def font(sz,bold=False):
    candidates=(['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','C:/Windows/Fonts/arialbd.ttf'] if bold
      else ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','C:/Windows/Fonts/arial.ttf'])
    for path in candidates:
        if Path(path).exists():return ImageFont.truetype(path,sz)
    return ImageFont.load_default()

def monochrome_ink(img,threshold=164):
    """Extract high-contrast monochrome line art on plain white."""
    gray=ImageOps.grayscale(img)
    # red/yellow accents retain their black-outline silhouette.
    return gray.point(lambda v: 255 if v>threshold else 0).convert('1')

# Soft graphic line extraction: preserve larger contour strokes while removing near-white paper.
top=monochrome_ink(TOP,171).convert('RGB')
# compact header dog icon. Take reclining silhouette, ear and heart; avoid horizontal grass line.
emblem=Image.new('RGB',(76,58),'white')
head=TOP.crop((111,12,285,132)).convert('RGB')
head=monochrome_ink(head,177).convert('RGB')
head.thumbnail((67,48),Image.Resampling.LANCZOS)
emblem.paste(head,(1,9))
# The source crop already contains the one original heart. Do not draw another one.
# Enlarging the canvas without clipping preserves that original heart.
emblem.save(SOURCE/'header-emblem.png')
# Touch header emblem: separately threshold the original large crop, not the
# reduced X3 CPB. The arrow is drawn by firmware beside this illustration.
touch_emblem = Image.new('RGB', (76, 58), 'white')
touch_head = monochrome_ink(TOP.crop((111, 12, 285, 132)), 177).convert('RGB')
touch_head = ImageOps.contain(touch_head, (70, 52), Image.Resampling.LANCZOS)
touch_emblem.paste(touch_head, (0, 3))
touch_emblem.save(SOURCE/'header-emblem-touch.png')

# X3 header is just 76 px tall: a small dog silhouette on left, title owned by firmware.
# The header uses an ink-only emblem so black is visible on the white band.

# The X3 Home tile uses the native 166px cover + compact artwork; footer is drawn below the menu.
# Its top 147px carry Snoopy and a Peanuts-inspired zigzag. The native
# 166px live cover card occupies the lower part with preserved hitboxes.
HOME_TILE_HEIGHT = 320
home = Image.new('RGB', (528, HOME_TILE_HEIGHT), 'white')
d = ImageDraw.Draw(home)
d.text((20, 12), 'GOOD BOOKS,', font=font(23, True), fill='black')
d.text((20, 44), 'GOOD DAYS.', font=font(23, True), fill='black')
d.text((23, 82), 'ANOTHER STORY AWAITS.', font=font(10, True), fill='black')
art = monochrome_ink(TOP, 176).convert('RGB')
art = ImageOps.contain(art, (283, 96), Image.Resampling.LANCZOS)
home.paste(art, (528 - art.width - 5, 5))
# Charlie Brown's iconic zigzag visually separates the actual book card.
zigzag = [(0, 115)]
for x in range(0, 529, 20):
    zigzag.append((min(528, x + 10), 121))
    zigzag.append((min(528, x + 20), 115))
d.line(zigzag, fill='black', width=5, joint='curve')
# The footer already carries this slogan; leave the zigzag separator untouched.
# The rest remains white for firmware-owned book selection and title.
home.save(SOURCE/'home-layout.png')
# Full native 480px composition for portrait touch panels; this is redrawn
# from the original illustration and typography, not scaled from home-layout.
touch_home = Image.new('RGB', (480, HOME_TILE_HEIGHT), 'white')
th = ImageDraw.Draw(touch_home)
th.text((18, 13), 'GOOD BOOKS,', font=font(22, True), fill='black')
th.text((18, 44), 'GOOD DAYS.', font=font(22, True), fill='black')
th.text((20, 82), 'ANOTHER STORY AWAITS.', font=font(10, True), fill='black')
touch_dog = monochrome_ink(TOP, 176).convert('RGB')
touch_dog = ImageOps.contain(touch_dog, (244, 104), Image.Resampling.LANCZOS)
touch_home.paste(touch_dog, (480 - touch_dog.width - 5, 3))
points = [(0, 116)]
for x in range(0, 480, 20):
    points.extend(((min(479, x + 10), 122), (min(479, x + 20), 116)))
th.line(points, fill='black', width=5, joint='curve')
touch_home.save(SOURCE/'home-layout-touch.png')

# Snoopy only uses bounded footer artwork; the firmware background capability
# remains available to other themes, not activated by this theme.
# Use Snoopy's doghouse in place of the old left-side clouds.
house=Image.open(SOURCE/'snoopy-doghouse-ink.png').convert('RGB')
house=ImageOps.contain(house,(137,78),Image.Resampling.LANCZOS)
screen=Image.new('RGB',(528,84),'white')
screen.paste(house,(528-house.width-16,1))
sd=ImageDraw.Draw(screen)
sd.line([(0,77),(527,77)],fill='black',width=1)
for cx in (15,52,83,118,170,232,303,366):
    sd.line((cx,76,cx+7,72),fill='black',width=1)
screen.save(SOURCE/'screen-decoration.png')

# Full-height monochrome illustration, never a second native UI layer.
# PSRAM gating is enforced by the firmware, not by this portable theme pack.
# No Snoopy full-screen background is generated or installed.
# This theme deliberately only paints the two approved footer designs.
# Old source-art wallpaper experiments remain separate from the payload.

# Sleep-screen image: no tablet frame, extracted moonlit Snoopy scene.
# Crop outer display frame and last row with generated artist signature.
inside=SLEEP.crop((3,0,SLEEP.width-2,SLEEP.height-12))
sleep_canvas=Image.new('RGB',(528,792),'#202020')
# art resampled to 528 x ~750 to provide a bit of sky/ground margin at X3 native resolution.
art=ImageOps.fit(inside,(528,760),Image.Resampling.LANCZOS,centering=(0.50,0.46))
sleep_canvas.paste(art,(0,16))
sleep_canvas=ImageOps.autocontrast(sleep_canvas,cutoff=1)
# 1-bit Floyd–Steinberg e-ink retains moon/cloud detail.
sleep_mono=sleep_canvas.convert('1',dither=Image.Dither.FLOYDSTEINBERG)
sleep_mono.convert('RGB').save(SOURCE/'sleep-monochrome-preview.png')
# Independently prepared portrait 480x800 sleep bitmap from the supplied
# source, preserving the approved X3 sleep-night.cpb without modifications.
touch_sleep_canvas = Image.new('RGB', (480, 800), '#202020')
touch_sleep_picture = ImageOps.fit(inside, (480, 766), Image.Resampling.LANCZOS, centering=(0.50, 0.46))
touch_sleep_canvas.paste(touch_sleep_picture, (0, 17))
touch_sleep_canvas = ImageOps.autocontrast(touch_sleep_canvas, cutoff=1)
touch_sleep = touch_sleep_canvas.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
touch_sleep.convert('RGB').save(SOURCE/'sleep-touch-preview.png')

# Boot scene is a simple framed line art illustration, separate from user controls.
boot=Image.new('RGB',(320,235),'white');bd=ImageDraw.Draw(boot)
art=monochrome_ink(TOP,175).convert('RGB')
art=ImageOps.contain(art,(305,115),Image.Resampling.LANCZOS)
boot.paste(art,((320-art.width)//2,35))
bd.text((68,171),'A COZY READING DAY',font=font(13,True),fill='black')
boot.save(SOURCE/'boot-art.png')
# Touch boot art is re-laid-out from the source, not resampled from X3 boot.
touch_boot = Image.new('RGB', (480, 270), 'white')
tb = ImageDraw.Draw(touch_boot)
touch_boot_dog = monochrome_ink(TOP, 175).convert('RGB')
touch_boot_dog = ImageOps.contain(touch_boot_dog, (435, 163), Image.Resampling.LANCZOS)
touch_boot.paste(touch_boot_dog, ((480 - touch_boot_dog.width) // 2, 25))
tb.text((116, 210), 'A COZY READING DAY', font=font(16, True), fill='black')
touch_boot.save(SOURCE/'boot-art-touch.png')

# CPB1: little endian 20-byte header, one-bit black=1, row-major MSB-first.
def write_cpb(source,dest:Path):
    mono=source.convert('1')
    w,h=mono.size
    stride=(w+7)//8
    raw=bytearray(mono.tobytes())
    for i,x in enumerate(raw):raw[i]=x ^ 255
    # CPB requires trailing row padding bits to be ZERO (Pillow uses zero
    # padding for white-bit mode, so inversion alone would set those bits).
    if w % 8:
        pad_mask=(1 << (8 - (w % 8))) - 1
        for y in range(h):
            raw[(y+1)*stride-1] &= 255 ^ pad_mask
    header=struct.pack('<4sBBHHHII',b'CPTB',1,1,w,h,stride,len(raw),zlib.crc32(raw)&0xffffffff)
    dest.write_bytes(header+raw)
    assert len(raw)==stride*h and len(raw)<=131072
    return len(raw)+len(header)

# Keep the original Woodstock and grass footer, but replace illegibly small
# lettering in the center with a larger DynaPuff line.
footer=Image.open(SOURCE/'footer-home.png').convert('RGB')
fd=ImageDraw.Draw(footer)
fd.rectangle((114,2,421,34),fill='white')
footer_font=ImageFont.truetype(str(OUT/'source-fonts/DynaPuff-variable.ttf'),18)
slogan='SAME DOG. MORE GOOD BOOKS.'
bounds=fd.textbbox((0,0),slogan,font=footer_font,stroke_width=0)
fd.text(((528-(bounds[2]-bounds[0]))//2,7),slogan,fill='black',font=footer_font)
footer.save(SOURCE/'footer-legible.png')

# X4 Pro footers enlarge the SAME X3 Woodstock/slogan/cloud and doghouse art.
# The original X3 artwork, height, and packaging remain byte-identical.
def paste_ink(canvas, artwork, xy):
    canvas.paste(artwork, xy, ImageOps.invert(artwork.convert('L')))

def tight_art(image):
    # Crop surrounding paper before composing target-resolution art.
    bounds = ImageOps.invert(image.convert('L')).getbbox()
    return image.crop(bounds) if bounds else image

touch_screen = Image.new('RGB', (480, 128), 'white')
house_large = tight_art(monochrome_ink(Image.open(SOURCE/'snoopy-doghouse-ink.png'), 175).convert('RGB'))
house_large = ImageOps.contain(house_large, (160, 114), Image.Resampling.LANCZOS)
paste_ink(touch_screen, house_large, (480 - house_large.width - 9, 5))
grass = ImageDraw.Draw(touch_screen)
grass.line((0, 120, 479, 120), fill='black', width=1)
for cx in (14, 51, 87, 123, 169, 224, 282):
    grass.line((cx, 119, cx + 8, 114), fill='black', width=1)
touch_screen.save(SOURCE/'screen-decoration-touch.png')
touch_footer = Image.new('RGB', (480, 80), 'white')
original_footer = Image.open(SOURCE/'footer-home.png').convert('RGB')
woodstock = ImageOps.contain(tight_art(original_footer.crop((8, 0, 69, 41))), (75, 65), Image.Resampling.LANCZOS)
cloud = ImageOps.contain(tight_art(original_footer.crop((433, 0, 517, 42))), (77, 50), Image.Resampling.LANCZOS)
paste_ink(touch_footer, woodstock, (10, 8))
paste_ink(touch_footer, cloud, (480 - cloud.width - 9, 16))
tf = ImageDraw.Draw(touch_footer)
touch_font = ImageFont.truetype(str(OUT/'source-fonts/DynaPuff-variable.ttf'), 17)
touch_bounds = tf.textbbox((0, 0), slogan, font=touch_font)
tf.text(((480 - (touch_bounds[2] - touch_bounds[0])) // 2, 26), slogan, fill='black', font=touch_font)
tf.line((0, 76, 479, 76), fill='black', width=1)
for cx in (9, 58, 112, 169, 235, 299, 372):
    tf.line((cx, 75, cx + 7, 72), fill='black', width=1)
touch_footer.save(SOURCE/'home-footer-touch.png')
# Drop obsolete installable background asset while retaining its source art.
(ASSETS / 'screen-background.cpb').unlink(missing_ok=True)

files={
  'header-emblem.cpb':emblem,
  'header-emblem-touch.cpb':touch_emblem,
  'home-hero.cpb':home,
  'home-hero-touch.cpb':touch_home,
  'home-footer.cpb':footer,
  'screen-decoration.cpb':screen,
  'home-footer-touch.cpb':touch_footer,
  'screen-decoration-touch.cpb':touch_screen,
  'boot-art.cpb':boot,
  'boot-art-touch.cpb':touch_boot,
  'sleep-night.cpb':sleep_mono,
  'sleep-night-touch.cpb':touch_sleep,
}
# Maximum 22-scene paired gallery, in addition to the original sleep artwork.
# Place the companion ZIP in source-art before rebuilding the test theme.
T='themes/snoopy/assets/'
GALLERY_ZIP = SOURCE/'Snoopy_Woodstock_22_Sleep_Scenes_X3_X4Pro.zip'
sleep_base_paths = [T+'sleep-night.cpb']
sleep_touch_paths = [T+'sleep-night-touch.cpb']
if GALLERY_ZIP.is_file():
    with zipfile.ZipFile(GALLERY_ZIP) as gallery:
        for n in range(1, 23):
            for suffix, collection, dimensions in (('', sleep_base_paths, (528,792)),
                                                   ('-touch', sleep_touch_paths, (480,800))):
                name=f'sleep-scene-{n:02d}{suffix}.cpb'
                payload=gallery.read('assets/'+name)
                magic,version,flags,w,h,stride,nbytes,crc=struct.unpack('<4sBBHHHII',payload[:20])
                assert (magic,version,flags,w,h,stride,nbytes)==(b'CPTB',1,1,*dimensions,(w+7)//8,stride*h)
                assert len(payload)==20+nbytes and zlib.crc32(payload[20:]) & 0xffffffff == crc
                (ASSETS/name).write_bytes(payload)
                collection.append(T+name)
else:
    print('NOTE: Snoopy 22-scene companion archive not imported; preserving single sleep art')

for name, img in files.items():
    if name == 'sleep-night.cpb' and (ASSETS / name).is_file():
        print('PRESERVED sleep-night.cpb (hardware-approved artwork)')
        continue
    print('CPB', name, img.size, write_cpb(img, ASSETS / name))

T='themes/snoopy/assets/'
# The renderer owns navigation, actual book card, covers, lists, button input, and status.
scene={
 'schema_version':1,'base':'classic',
 'reference':{'width':528,'height':792,'adapt':'scale-to-fit'},
 'metrics':{
     'topPadding':0,'batteryBarHeight':20,'headerHeight':76,
     'homeTopPadding':76,'homeCoverHeight':146,'homeCoverTileHeight':HOME_TILE_HEIGHT,
     'homeRecentBooksCount':1,'homeContinueReadingInMenu':False,'homeMenuTopOffset':12,
     'contentSidePadding':14,'previewPadding':10,'verticalSpacing':8,
     'headerSidePadding':14,'headerUnderlineSize':1,'headerTitleAlign':0,
     'headerBatterySide':0,'headerShowsClock':False,'headerClockCentered':False,
     'menuRowHeight':54,'menuSpacing':3,'listRowHeight':62,
     'listWithSubtitleRowHeight':72,'listRowGap':8,'listRowRadius':16,
     'listInset':14,'listSidePadding':17,'listSeparators':False,'listTitleBold':True,
     'listSelectionStyle':1,'buttonHintsHeight':40,'progressBarHeight':8,
     'controlRadius':14,'sheetRadius':14,'capsuleRadius':16
  },
 'styles':{
    'header_background':'white','header_foreground':'black',
    'selection':'pill','row_separators':False,'corners':'rounded',
    'chamfer_cut':0,'chamfer_row_cut':11,'menu_double_outline':True,
    'menu_footer_asset':'home_footer','menu_footer_touch_asset':'home_footer_touch',
    'settings_navigation':'list','header_back_style':'both'
  },
 'assets':{
    'header_emblem':T+'header-emblem.cpb','header_emblem_touch':T+'header-emblem-touch.cpb',
    'home_hero':T+'home-hero.cpb','home_hero_touch':T+'home-hero-touch.cpb',
    'home_footer':T+'home-footer.cpb','home_footer_touch':T+'home-footer-touch.cpb',
    'screen_art':T+'screen-decoration.cpb','screen_art_touch':T+'screen-decoration-touch.cpb',
     
    'boot_art':T+'boot-art.cpb','boot_art_touch':T+'boot-art-touch.cpb',
    'sleep_art':sleep_base_paths,'sleep_art_touch':sleep_touch_paths
  },
 'regions':{
   'header':[
      {'op':'fill','color':'white'},
      {'op':'bitmap','asset':'header_emblem','anchor':'left','offset':[8,0],
       'paint':'ink-only','fit':'native','max_width':76,'max_height':58},
      {'op':'text','source':'screen_title','font':'ui_bold','color':'black',
       'anchor':'left','offset':[100,0],'max_width':265},
      {'op':'line','anchor':'bottom','color':'black','thickness':2}
   ],
   'home':[
      {'op':'fill','color':'white'},
      {'op':'bitmap','asset':'home_hero','anchor':'top','fit':'contain'},
      {'op':'book-card','variant':'cover','anchor':'bottom','offset':[0,-7]}
   ],
   'boot':[
      {'op':'fill','color':'white'},
      {'op':'bitmap','asset':'boot_art','anchor':'center','fit':'native',
       'paint':'ink-only','max_width':320,'max_height':235},
      {'op':'progress','source':'loading_percent','anchor':'bottom',
       'offset':[0,-95],'color':'black','thickness':5}
   ],
   'sleep':[
      {'op':'fill','color':'black'},
      {'op':'bitmap','asset':'sleep_art','anchor':'center','fit':'native'}
   ],
   'hints':[],
   'screen':[
      {'op':'bitmap','asset':'screen_art','anchor':'bottom','fit':'contain',
       'paint':'ink-only','max_width':528,'max_height':84}
   ]
  }
}
scene["fonts"] = {"ui": {
    "small": "themes/snoopy/fonts/ui-small.cpfont",
    "regular": "themes/snoopy/fonts/ui-regular.cpfont",
    "large": "themes/snoopy/fonts/ui-large.cpfont",
    "display": "themes/snoopy/fonts/display.cpfont"
}}
(PKG/'themes/snoopy/theme.json').write_text(json.dumps(scene,indent=2)+'\n')
readme='''Snoopy - cozy reading theme (X3-first preview)

A monochrome Peanuts-inspired theme for theme-capable CrossPoint firmware.
Each installable ZIP contains only the native-resolution artwork for its target display,
small decorative drawings, and a moonlit sleep screen.

Use Settings > Display > UI Theme to select Snoopy.
Requires the SD theme, metrics, images, composition, and settings-navigation
capabilities. Normal reader and navigation controls remain firmware-owned.

Unofficial non-commercial fan theme with AI-generated artwork. Snoopy and Woodstock
are Peanuts characters owned by their respective rights holders. This
fan-made theme is not an official or endorsed Peanuts product.
DynaPuff typeface is by The DynaPuff Project Authors and distributed under
SIL Open Font License 1.1; see DETAILS.md for the complete OFL text.
'''
(PKG/'README.md').write_text(readme)
(PKG/'DETAILS.md').write_text('''# Snoopy - Cozy Reading (v0.1.13)

Unofficial concept based on the user-provided Snoopy e-reader mockup.

- X3 reference panel: **528 x 792**. Monochrome, 1-bit images.
- Home shows a native dynamic cover, title/author, optional EPUB series and index beneath the author, dark-only-when-focused hero card, and inline saved progress; the top Snoopy hero illustration stays at the same height.
- Home menu uses outlined cut-corner frames and the Woodstock footer from the supplied art. Settings retains navigable rows, DynaPuff and the original-scale Snoopy head with one tiny heart.
- Snoopy uses only bounded footer artwork, not a full-screen background. X3 retains both original footer images byte-for-byte; touch panels display taller compositions using the SAME Woodstock/slogan/cloud and Snoopy doghouse/grass-line artwork. Other themes can still use the firmware background capability.
- Sleep artwork comes from the theme (Dark/Light), not a Custom wallpaper pack. The source-art gallery ZIP adds twenty-two Snoopy & Woodstock scenes plus the approved original to **each** device's dedicated gallery, with random selection and no immediate repeats on matching firmware. The original sleep image remains in the gallery.
- The source defines six device-sized artwork pairs for header emblem, Home hero, Home footer, list footer, boot and sleep. Each installable ZIP contains **only** the matching display's artwork; the X3 CPBs remain byte-identical to the original approved assets. The same installed theme ID is retained for both resolutions. Snoopy requests the firmware-owned Back arrow plus the header emblem on touch push screens (`theme.header-back.v1`); root Home still has no Back arrow. Native Back routing is unchanged. X4 Pro hardware validation is pending.
- The home mockup's multi-book gallery, custom apps, red doghouse and yellow character are **not** theme-contract features; they are not promised by this package.

Unofficial, non-commercial fan-made theme using AI-generated illustrations. Snoopy, Woodstock and Peanuts remain trademarks and copyrighted characters of their respective owners. This is not an official or endorsed Peanuts product.
''')
# Include the DynaPuff license in the installed catalog details, not just
# the development source, so every distributed raster subset carries its OFL.
details_path = PKG/'DETAILS.md'
details_path.write_text(details_path.read_text(encoding='utf-8') +
    "\n## DynaPuff font license (SIL OFL 1.1)\n\n" +
    (OUT/'source-fonts/OFL.txt').read_text(encoding='utf-8'), encoding='utf-8')

manifest={
 'kind':'theme-pack','name':'snoopy','title':'Snoopy','description':'Cozy monochrome Snoopy-inspired reading theme for device-sized e-ink screens.',
 'author':'Jadehawk (concept adaptation)','version':'0.1.13',
 'license':'Unofficial non-commercial fan theme; Peanuts character rights belong to their respective owners.',
 'themes':[{'id':'snoopy','title':'Snoopy','path':'themes/snoopy/theme.json',
            'requires':['theme.sd.v1','theme.metrics.v1','theme.images.v1','theme.composition.v1','theme.settings-navigation.v1','theme.book-cover.v1','theme.menu-decoration.v1','theme.screen-decoration.v1','theme.header-back.v1','theme.fonts.v1','theme.font-family.v1']}],
 'files':['manifest.json','README.md','DETAILS.md','themes/snoopy/theme.json']+
         [T+x for x in files] + sleep_base_paths[1:] + sleep_touch_paths[1:] + ['themes/snoopy/fonts/'+role+'.cpfont' for role in ('ui-small','ui-regular','ui-large','display')]
}
(PKG/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(OUT/'README.md').write_text('''# Snoopy CrossPoint Theme (X3-first prototype)

An **unofficial, non-commercial fan-made theme** with AI-generated Snoopy and Woodstock illustrations. It is a CrossPoint theme pack, not a plugin or firmware.

## Install

Download the device-matched `snoopy-x3-0.1.13.crosspoint-theme.zip` or `snoopy-x4plus-0.1.13.crosspoint-theme.zip` via The Cantina Store, or extract either ZIP to SD path:

```
/.crosspoint/themes/snoopy.crosspoint-theme/
```

Then use **Settings -> Display -> UI Theme -> Snoopy** and return to Home.
Select a firmware Dark/Light sleep screen to test the theme's sleep image; Custom sleep pools take precedence.

## X3-specific corrections to the concept

1. The X3 is 528 x 792 and has no touch interface. This version uses one native Continue Reading card and a navigable list, not the concept's four-cover touchscreen grid.
2. A 76px Home/Settings header leaves space for firmware-owned battery, title and Back actions; the Snoopy heart is now inset fully within the emblem.
3. The Home tile expands into previously unused X3 space to restore a real cached cover, book title, author, and actual progress bar when available; firmware keeps book selection and menu behavior.
4. All graphics are CPB v1, 1-bit black/white. Colors in the source artwork become e-ink grayscale/dithered monochrome.
5. Sleep art is a fixed X3-sized 528 x 792 background. Preview it on-device before adopting for other displays.
6. DynaPuff is bundled as four size-specific one-bit v4 CPFONT files. Stock fonts remain the firmware fallback.

## Limitations

- Theme schemas cannot replace the firmware's core Home layout, add new menu actions, draw live book grids, or add touch control on X3.
- Full-screen theme sleep galleries are used for Dark/Light regular sleep entries, not the independent timed sleep refresh pool.
- This unofficial, non-commercial theme uses Snoopy and Woodstock characters; all Peanuts character trademarks and copyrights remain with their respective rights holders. It is not endorsed by them.
- Version 0.1.13 ships independent X3 and X4+ archives under one Snoopy theme identity, each with 23 randomly rotated sleep scenes. X3 artwork is unchanged; hardware testing is ongoing.

## Files

- `snoopy.crosspoint-theme/` is the only installable payload. It contains no executable scripts.
- `source-art/` contains the approved X3 Home and doghouse art. The two larger touch-footer CPBs are recomposed directly from those original sources; the experimental full-page Woodstock image is not included or activated.
- `source-fonts/` contains the upstream DynaPuff TTF and SIL OFL license. Run `python tools/build_fonts.py` before `python tools/build.py` when updating font assets.
- `previews/` has illustrative X3-size previews, not exact firmware screenshots.

Compatibility is capability-based. Snoopy v0.1.13 additionally requires `theme.book-cover.v1`, `theme.screen-decoration.v1`, `theme.fonts.v1`, and `theme.font-family.v1`; older firmware must reject this feature rather than degrade to a fake book cover. No branded firmware name is a requirement.
''')
# Approximate X3 previews only. Keep firmware-owned book/menu labels, touch
# targets, real battery, and row selection distinct from static theme artwork.
x3home=Image.new('RGB',(528,792),'white');d=ImageDraw.Draw(x3home)
x3home.paste(emblem,(10,8))
d.text((91,24),'HOME',font=font(23,True),fill='black')
d.text((456,22),'85%',font=font(14,True),fill='black')
d.line((0,75,527,75),fill='black',width=2)
x3home.paste(home,(0,76))
card_y=76+HOME_TILE_HEIGHT-166-7
d.rectangle((18,card_y,510,card_y+166),outline='black',width=2,fill='white')
d.rectangle((28,card_y+9,130,card_y+157),outline='black',width=2)
d.text((44,card_y+59),'COVER',font=font(15,True),fill='black')
d.text((160,card_y+25),'YOUR CURRENT BOOK',font=font(16,True),fill='black')
d.text((160,card_y+58),'Book author',font=font(15),fill='black')
d.text((160,card_y+89),'Series Name #1',font=font(13),fill='black')
d.rectangle((160,card_y+132,360,card_y+144),outline='black',width=1)
d.rectangle((162,card_y+134,272,card_y+142),fill='black')
for i,label in enumerate(['Browse Files','Library','Plugins','File Transfer','Settings']):
 y=76+HOME_TILE_HEIGHT+12+i*57
 x0,x1=18,510
 # Double-cut frame drawn by firmware; preview shows the intended silhouette.
 pts=[(x0+11,y),(x1-1,y),(x1-1,y+42),(x1-12,y+52),(x0,y+52),(x0,y+11)]
 d.polygon(pts,outline='black',width=3)
 inner=[(x0+17,y+5),(x1-6,y+5),(x1-6,y+39),(x1-17,y+47),(x0+6,y+47),(x0+6,y+17)]
 d.polygon(inner,outline='black',width=1)
 d.text((184,y+15),label,font=font(19),fill='black')
footer=Image.open(SOURCE/'footer-home.png').convert('RGB')
x3home.paste(footer,(0,702))
d.text((35,761),'RESUME       SELECT          UP          DOWN',font=font(14),fill='black')
x3home.save(PREV/'x3-home-layout-preview.png')

settings=Image.new('RGB',(528,792),'white');d=ImageDraw.Draw(settings)
settings.paste(emblem,(10,8));d.text((91,24),'SETTINGS',font=font(23,True),fill='black')
d.line((0,75,527,75),fill='black',width=2)
for i,label in enumerate(['System','Display','Reader','Controls','Library','Connectivity']):
 y=88+i*70
 if i==0:d.rounded_rectangle((18,y,510,y+61),radius=16,fill='#dddddd')
 d.text((47,y+18),label,font=font(21,True),fill='black')
# Short Settings lists leave a conservative blank zone above button hints.
# This optional CPB is the same decoration generic firmware uses elsewhere.
settings.paste(screen,(0,661))
d.text((85,761),'BACK      SELECT        UP        DOWN',font=font(15),fill='black')
settings.save(PREV/'x3-settings-layout-preview.png')
sleep_mono.convert('RGB').save(PREV/'x3-sleep-preview.png')

# Validate artifacts with byte-level checks and package in deterministic order.
def inspect_cpb(path):
    data=path.read_bytes()
    sig,vers,flags,w,h,stride,length,crc=struct.unpack('<4sBBHHHII',data[:20])
    assert (sig,vers,flags)==(b'CPTB',1,1)
    assert 1<=w<=1024 and 1<=h<=1024
    assert stride==(w+7)//8 and length==stride*h
    assert len(data)==20+length and length<=131072
    assert zlib.crc32(data[20:])&0xffffffff==crc
    if w % 8:
        pad_mask=(1 << (8 - (w % 8))) - 1
        assert all((data[20+(y+1)*stride-1]&pad_mask)==0 for y in range(h))
for path in ASSETS.glob('*.cpb'):inspect_cpb(path)
assert len(manifest['files'])==len(set(manifest['files']))
assert sum((PKG/f).stat().st_size for f in manifest['files'])<4*1024*1024
assert (PKG/'README.md').stat().st_size<2048
assert all((PKG/f).is_file() for f in manifest['files'])
for generated in (PKG/'README.md', PKG/'DETAILS.md', OUT/'README.md'):
    generated.write_text(generated.read_text(encoding='utf-8').replace('0.1.11','0.1.13'),encoding='utf-8')
# Source payload stays combined for authoring and regression tests; the
# installable packages each contain only one resolution's CPBs.
from pack_theme_variants import build as pack_resolution_variants
outputs = pack_resolution_variants(OUT, OUT/'dist', manifest['version'])
print('Validated and packaged:', ', '.join(str(p) for p in outputs))
