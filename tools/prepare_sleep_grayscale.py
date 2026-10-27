"""Prepare crisp, bright native four-tone Snoopy sleep BMPs for each display."""
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps

PROFILES = {"x3": (528, 792), "x4plus": (480, 800)}
SOURCE = Path(__file__).resolve().parents[1] / "source-art" / "sleep-grayscale"

def source_files():
    files = sorted(p for p in SOURCE.iterdir() if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    if len(files) != 10:
        raise ValueError(f"Expected 10 approved Snoopy sleep sources, found {len(files)}")
    return files

def create(root: Path):
    images = source_files()
    # Every palette entry maps exactly to one of the firmware's native gray
    # levels. These are real four-level pixels (not one-bit halftoning).
    shades = (0, 85, 170, 255)
    output = {}
    for variant, dimensions in PROFILES.items():
        collection = {}
        for index, src in enumerate(images, 1):
            with Image.open(src) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                # No cropping of characters or art; preserve white sidebands.
                image = ImageOps.pad(image, dimensions, method=Image.Resampling.LANCZOS, color="white")
                gray = ImageOps.grayscale(image)
                # Gently brighten darker phone wallpapers; keep light backgrounds clean.
                gray = gray.point(lambda v: min(255, round(255 * (v / 255) ** 0.82)))
                image4 = gray.quantize(colors=4, dither=Image.Dither.FLOYDSTEINBERG)
                # Palette quantize() with 252 duplicate white entries collapses
                # to 1-bit on some Pillow versions. Remap four distinct
                # perceptual buckets to the panel's exact four native tones.
                original_palette = image4.getpalette()
                rank = sorted(range(4), key=lambda i: original_palette[i * 3])
                native = [255] * 256
                for level, palette_index in enumerate(rank):
                    native[palette_index] = shades[level]
                image4.putpalette([v for i in range(256) for v in (native[i],) * 3])
                name = f"sleep-scene-{index:02d}.bmp"
                target = root / "dist" / "sleep-grayscale" / variant / name
                target.parent.mkdir(parents=True, exist_ok=True)
                image4.save(target, format="BMP")
                # Check dimensions, palette & brightness after encoding.
                with Image.open(target) as check:
                    if check.size != dimensions or set(check.convert("L").get_flattened_data()) != set(shades):
                        raise ValueError(f"Invalid native 4-gray BMP: {target}")
                collection["themes/snoopy/sleep/" + name] = target.read_bytes()
        output[variant] = collection
    return output

if __name__ == "__main__":
    result = create(SOURCE.parents[1])
    for key, files in result.items():
        print(key, len(files), "four-tone sleep BMPs", sum(map(len, files.values())), "bytes")
