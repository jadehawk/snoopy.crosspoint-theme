"""Compose the optional full-height Woodstock underlay for PSRAM-enabled readers.

All artwork is generated offline for the .crosspoint-theme package. The
runtime receives a single 1-bit ink-only CPB and owns all text and controls.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


CANVAS = (528, 792)


def cloud(scene: Image.Image, source: Path, x: int, y: int, w: int, h: int) -> None:
    """Place a genuine rounded comic-cloud cutout, ink-only on white."""
    art = Image.open(source / "comic-cloud.png").convert("L")
    art.paste(255, (0, 80, 17, art.height))  # clean stray line from source crop
    art = art.resize((w, h), Image.Resampling.LANCZOS)
    art = art.point(lambda value: 0 if value < 170 else 255)
    scene.paste(art, (x, y), ImageOps.invert(art))


def leafy_bough(draw: ImageDraw.ImageDraw) -> None:
    """A branching canopy enters from the right without filling the UI center."""
    # The cut-off outer edge suggests the tree continues beyond the page.
    draw.line([(530, 355), (508, 315), (504, 260), (513, 213), (521, 143)],
              fill=0, width=5, joint="curve")
    draw.line([(513, 214), (481, 182), (449, 169)], fill=0, width=4, joint="curve")
    draw.line([(508, 304), (478, 275), (453, 259)], fill=0, width=3, joint="curve")
    # Loose foliage in light irregular outlines, concentrated at the edge.
    for cx, cy, radius in ((512, 111, 37), (478, 118, 28), (438, 134, 23),
                           (518, 188, 31), (488, 206, 22), (522, 268, 29),
                           (488, 292, 20), (508, 335, 19)):
        points = []
        for i in range(97):
            a = 2 * math.pi * i / 96
            r = radius * (1 + .045 * math.sin(7 * a) + .025 * math.sin(11 * a))
            points.append((round(cx + r * math.cos(a)),
                           round(cy + r * .74 * math.sin(a))))
        draw.line(points, fill=0, width=2, joint="curve")
    # Sparse dangling leaves.
    for x, y in ((447, 196), (479, 235), (460, 301)):
        draw.line((x - 6, y - 8, x + 5, y + 8, x - 6, y - 8), fill=0, width=1)
        draw.line((x - 7, y - 5, x + 6, y + 9), fill=0, width=1)


def render(source: Path) -> Image.Image:
    """Return a 528x792 binary-friendly white-backed illustration."""
    scene = Image.new("L", CANVAS, 255)
    draw = ImageDraw.Draw(scene)

    # Sky opens above and between native controls; no status text or ornaments
    # masquerade as buttons or directory rows.
    cloud(scene, source, 37, 102, 167, 105)
    cloud(scene, source, 254, 181, 118, 76)
    cloud(scene, source, 19, 331, 125, 80)
    cloud(scene, source, 330, 497, 103, 68)
    leafy_bough(draw)

    # Character extracted from the approved illustration, not a fake UI icon.
    bird = Image.open(source / "woodstock-flight-sprite.png").convert("L")
    bird = ImageOps.contain(bird, (137, 158), Image.Resampling.LANCZOS)
    bird = bird.point(lambda value: 0 if value < 175 else 255)
    # Transparent white makes the flying character a pure ink overlay.
    mask = ImageOps.invert(bird)
    scene.paste(bird, (326, 349), mask)

    # An airy flight trail leads through blank space without becoming a rule
    # across any native row. Dashes remain part of the artwork only.
    trail = []
    for index in range(66):
        t = index / 65
        x = 165 + 163 * t
        y = 434 - 51 * math.sin(math.pi * t) + 16 * math.sin(3 * math.pi * t)
        trail.append((int(x), int(y)))
    for i in range(0, len(trail) - 2, 5):
        draw.line((trail[i], trail[min(i + 2, len(trail) - 1)]), fill=0, width=2)

    # Full-width illustrated ground, including a second Woodstock and Snoopy's
    # house, from the approved concept. It is deliberately BELOW normal rows,
    # which may obscure it on crowded lists.
    meadow = Image.open(source / "woodstock-meadow.png").convert("L")
    meadow = meadow.resize((528, 176), Image.Resampling.LANCZOS)
    meadow = meadow.point(lambda value: 0 if value < 165 else 255)
    scene.paste(meadow, (0, 616))

    # Use hard 1-bit pixels so the shared CPB writer can stream without
    # dithering/gray layers or allocating a second full screen at runtime.
    return scene.convert("1").convert("RGB")
