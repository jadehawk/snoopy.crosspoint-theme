"""Build compact one-bit CPFONT v4 DynaPuff variants using CrossPoint's rasterizer.

Requires freetype-py and the adjacent Razor-Crest source checkout. Font artwork
is licensed under SIL OFL 1.1; source-fonts/OFL.txt is authoritative.
"""
from __future__ import annotations

import sys
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONVERTER = ROOT.parent / 'crosspoint-reader-(Razor-Crest)' / 'lib' / 'EpdFont' / 'scripts'
sys.path.insert(0, str(CONVERTER))
import fontconvert_sdcard as convert

FONT = ROOT / 'source-fonts' / 'DynaPuff-variable.ttf'
DEST = ROOT / 'snoopy.crosspoint-theme' / 'themes' / 'snoopy' / 'fonts'
# Four independently rasterized sizes as required by theme.font-family.v1.
SIZES = {'ui-small': 9, 'ui-regular': 11, 'ui-large': 13, 'display': 19}
# The firmware UI raster scale is larger than these names suggest; X3 test
# must confirm text fits especially on Settings value rows.
TOC = struct.Struct('<B3xIIBhhHHBBBI4x')
GLYPH = struct.Struct('<BBHhhH2xI')

def mono_payload(glyph, packed2):
    count = glyph.width * glyph.height
    out = bytearray((count + 7) // 8)
    for index in range(count):
        intensity = (packed2[index // 4] >> (6 - 2 * (index % 4))) & 3
        if intensity >= 2:
            out[index // 8] |= (0x80 >> (index % 8))
    return bytes(out)

def build(name, size):
    ranges = convert.resolve_intervals('ascii,latin1,(0x0100-0x017F),(0x2010-0x201F),(0x2026-0x2026)')
    data = convert.rasterize_font_style(str(FONT), size, ranges, style_id=0)
    intervals = bytearray()
    pos = 0
    for first, last in data.intervals:
        intervals.extend(struct.pack('<III', first, last, pos))
        pos += last - first + 1
    glyphs = bytearray()
    bitmap = bytearray()
    for g, pixels2 in data.all_glyphs:
        px = mono_payload(g, pixels2)
        glyphs.extend(GLYPH.pack(g.width, g.height, g.advance_x, g.left, g.top, len(px), len(bitmap)))
        bitmap.extend(px)
    offset = 64
    # Header flags zero: 1-bit black ink rather than 2-bit grayscale.
    header = struct.pack('<8sHHB19s', bytes((67, 80, 70, 79, 78, 84, 0, 0)), 4, 0, 1, bytes(19))
    toc = TOC.pack(0, len(data.intervals), len(data.all_glyphs),
                   data.advanceY, data.ascender, data.descender, 0, 0, 0, 0, 0, offset)
    dest = DEST / (name + '.cpfont')
    dest.write_bytes(header + toc + intervals + glyphs + bitmap)
    print(name, size, len(dest.read_bytes()), 'line height', data.advanceY)

if __name__ == '__main__':
    DEST.mkdir(parents=True, exist_ok=True)
    for name, size in SIZES.items():
        build(name, size)
