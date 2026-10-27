"""Prepare crisp, bright native four-tone Snoopy sleep BMPs for each display."""
from pathlib import Path
import struct
from PIL import Image, ImageOps

PROFILES = {"x3": (528, 792), "x4plus": (480, 800)}
SOURCE = Path(__file__).resolve().parents[1] / "source-art" / "sleep-grayscale"

def source_files():
    files = sorted(p for p in SOURCE.iterdir() if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    if len(files) != 10:
        raise ValueError(f"Expected 10 approved Snoopy sleep sources, found {len(files)}")
    return files

def write_native_2bpp_bmp(indices: Image.Image, target: Path) -> None:
    """Write the same compact native-gray BMP used by the Star Wars pack.

    Packing the four pixel levels into 2 bits saves 75% of uncompressed SD
    space compared to Pillow's 8-bit indexed BMPs, with identical gray pixels.
    """
    width, height = indices.size
    assert indices.mode == "P"
    # Quantization palette indices are ordered by color frequency, not shade.
    entries = indices.getpalette()
    by_brightness = sorted(range(4), key=lambda index: entries[index * 3])
    to_native_level = {palette_index: level for level, palette_index in enumerate(by_brightness)}
    pixels = bytes(to_native_level[index] for index in indices.get_flattened_data())
    stride = ((width * 2 + 31) // 32) * 4
    pixel_data = bytearray(stride * height)
    for y in range(height):
        row = (height - 1 - y) * stride
        for x in range(width):
            pixel_data[row + x // 4] |= pixels[y * width + x] << (6 - 2 * (x % 4))
    palette = b"".join(bytes((shade, shade, shade, 0)) for shade in (0, 85, 170, 255))
    offset = 14 + 40 + len(palette)
    header = struct.pack("<2sIHHI", b"BM", offset + len(pixel_data), 0, 0, offset)
    dib = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 2, 0,
                      len(pixel_data), 2835, 2835, 4, 4)
    target.write_bytes(header + dib + palette + pixel_data)


def decode_native_2bpp_bmp(data: bytes) -> Image.Image:
    """Decode the four-tone BMP for host tests (Pillow cannot open 2bpp BMP)."""
    assert len(data) >= 70 and data[:2] == b"BM"
    file_size, offset = struct.unpack_from("<I", data, 2)[0], struct.unpack_from("<I", data, 10)[0]
    dib_size, width, height, planes, bpp, compression = struct.unpack_from("<IiiHHI", data, 14)
    assert file_size == len(data) and dib_size == 40 and planes == 1
    assert width > 0 and height > 0 and bpp == 2 and compression == 0 and offset == 70
    assert data[54:70] == b"".join(bytes((v, v, v, 0)) for v in (0, 85, 170, 255))
    stride = ((width * 2 + 31) // 32) * 4
    assert len(data) - offset == stride * height
    result = bytearray(width * height)
    for y in range(height):
        start = offset + (height - 1 - y) * stride
        for x in range(width):
            level = (data[start + x // 4] >> (6 - (x % 4) * 2)) & 0x03
            result[y * width + x] = level * 85
    return Image.frombytes("L", (width, height), bytes(result))


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
                # Match the Star Wars wallpaper contract: fill the screen with
                # a centered crop, never introduce white padding bands.
                image = ImageOps.fit(image, dimensions, method=Image.Resampling.LANCZOS,
                                     centering=(0.5, 0.5))
                gray = ImageOps.grayscale(image)
                # Gently brighten darker phone wallpapers; keep light backgrounds clean.
                gray = gray.point(lambda v: min(255, round(255 * (v / 255) ** 0.82)))
                image4 = gray.quantize(colors=4, dither=Image.Dither.FLOYDSTEINBERG)
                # Preserve the same four quantized levels but store only two
                # bits per pixel, as the hardware and Star Wars wallpaper do.
                name = f"sleep-scene-{index:02d}.bmp"
                target = root / "dist" / "sleep-grayscale" / variant / name
                target.parent.mkdir(parents=True, exist_ok=True)
                write_native_2bpp_bmp(image4, target)
                # Check dimensions, palette & brightness after encoding.
                check = decode_native_2bpp_bmp(target.read_bytes())
                if check.size != dimensions or set(check.get_flattened_data()) != set(shades):
                    raise ValueError(f"Invalid native 4-gray BMP: {target}")
                collection["themes/snoopy/sleep/" + name] = target.read_bytes()
        output[variant] = collection
    return output

if __name__ == "__main__":
    result = create(SOURCE.parents[1])
    for key, files in result.items():
        print(key, len(files), "four-tone sleep BMPs", sum(map(len, files.values())), "bytes")
