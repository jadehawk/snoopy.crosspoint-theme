from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from pathlib import Path
from prepare_usb_grayscale import create as prepare_usb_grayscale
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
  'usb-connected.cpb':ImageOps.fit(Image.open(SOURCE/'usb-connected-grayscale.png').convert('RGB'),(528,792),centering=(0.5,0.5),method=Image.Resampling.LANCZOS).convert('1'),
  'usb-connected-touch.cpb':ImageOps.fit(Image.open(SOURCE/'usb-connected-grayscale.png').convert('RGB'),(480,800),centering=(0.5,0.5),method=Image.Resampling.LANCZOS).convert('1'),
}
# Source sleep illustrations are packaged separately as four-tone BMPs.
T='themes/snoopy/assets/'
for old in ASSETS.glob('sleep-*.cpb'):
    old.unlink()

for name, img in files.items():
    print('CPB', name, img.size, write_cpb(img, ASSETS / name))
usb_gray_paths = prepare_usb_grayscale(OUT)

T='themes/snoopy/assets/'
# Theme definitions, manifest, README, and DETAILS are authored and committed
# independently. This artwork-authoring script must never recreate them;
# release packaging reads only the committed source files.
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
# Check authored payload resources after creating artwork, but do not rewrite
# the manifest or package ZIPs here. The release packer is a separate tool.
manifest = json.loads((PKG / 'manifest.json').read_text(encoding='utf-8'))
assert len(manifest['files']) == len(set(manifest['files']))
assert sum((PKG / name).stat().st_size for name in manifest['files']) < 4 * 1024 * 1024
assert (PKG / 'README.md').stat().st_size < 2048
assert all((PKG / name).is_file() for name in manifest['files'])
print('Generated artwork and preview files; theme metadata and documentation unchanged.')
