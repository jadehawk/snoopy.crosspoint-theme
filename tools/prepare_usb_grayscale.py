"""Generate firmware-native USB grayscale BMPs from the approved Snoopy drawing.

Ships one image per device; the existing CPB scene remains a monochrome fallback.
"""
from pathlib import Path
from PIL import Image, ImageOps

try:
    from prepare_sleep_grayscale import write_native_2bpp_bmp, decode_native_2bpp_bmp
except ModuleNotFoundError:
    from tools.prepare_sleep_grayscale import write_native_2bpp_bmp, decode_native_2bpp_bmp

PROFILES = {"x3": (528, 792), "x4plus": (480, 800)}
SOURCE = Path(__file__).resolve().parents[1] / "source-art" / "usb-connected-grayscale.png"
SHADES = (0, 85, 170, 255)


def four_tone(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    gray = ImageOps.grayscale(image)
    gray = gray.point(lambda value: min(255, round(255 * (value / 255) ** 0.88)))
    image4 = gray.quantize(colors=4, dither=Image.Dither.FLOYDSTEINBERG)
    return image4  # Native 2-bit writer maps quantized palette indices to grayscale.


def create(root: Path) -> dict[str, str]:
    assets = root / "snoopy.crosspoint-theme" / "themes" / "snoopy" / "assets"
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Missing approved Snoopy USB source: {SOURCE}")
    paths = {}
    with Image.open(SOURCE) as original:
        for variant, dimensions in PROFILES.items():
            image = four_tone(original, dimensions)
            name = "usb-connected.bmp" if variant == "x3" else "usb-connected-touch.bmp"
            target = assets / name
            write_native_2bpp_bmp(image, target)
            data = target.read_bytes()
            actual = decode_native_2bpp_bmp(data)
            if actual.size != dimensions or actual.getbbox() is None:
                raise ValueError(f"USB grayscale BMP invalid: {target}")
            levels = set(actual.get_flattened_data())
            if levels != set(SHADES):
                raise ValueError(f"USB illustration lost grayscale detail: {target}: {levels}")
            paths[variant] = "themes/snoopy/assets/" + name
    return paths


if __name__ == "__main__":
    root = SOURCE.parents[1]
    for variant, path in create(root).items():
        print(f"{variant} {path}")
