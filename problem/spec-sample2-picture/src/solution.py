import struct
from pathlib import Path


def read_bmp(path: Path):
    data = path.read_bytes()
    if data[:2] != b"BM":
        raise ValueError("not a bmp")
    data_offset = struct.unpack_from("<I", data, 10)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    bpp = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    if bpp != 24 or compression != 0:
        raise ValueError("unsupported bmp format")
    abs_h = abs(height)
    stride = ((width * 3 + 3) // 4) * 4
    pixels = bytearray(width * abs_h * 3)
    mv = memoryview(data)[data_offset:]
    # normalize to top-down order
    for row in range(abs_h):
        src = mv[row * stride:row * stride + width * 3]
        y = abs_h - 1 - row if height > 0 else row
        start = y * width * 3
        pixels[start:start + width * 3] = src
    header = bytearray(data[:data_offset])
    return width, abs_h, pixels, header, data_offset


def rotate_clockwise(width: int, height: int, pixels: bytearray):
    new_w, new_h = height, width
    rotated = bytearray(new_w * new_h * 3)
    for y in range(height):
        for x in range(width):
            src_idx = (y * width + x) * 3
            nx = height - 1 - y
            ny = x
            dst_idx = (ny * new_w + nx) * 3
            rotated[dst_idx:dst_idx + 3] = pixels[src_idx:src_idx + 3]
    return new_w, new_h, rotated


def write_bmp(path: Path, width: int, height: int, pixels: bytearray,
              header: bytearray, data_offset: int):
    row_bytes = width * 3
    stride = ((row_bytes + 3) // 4) * 4
    image_size = stride * height
    struct.pack_into("<I", header, 2, data_offset + image_size)
    struct.pack_into("<i", header, 18, width)
    struct.pack_into("<i", header, 22, height)
    struct.pack_into("<I", header, 34, image_size)
    pad = b"\x00" * (stride - row_bytes) if stride > row_bytes else b""
    with path.open("wb") as f:
        f.write(header)
        for row in range(height - 1, -1, -1):  # bottom-up
            start = row * row_bytes
            f.write(pixels[start:start + row_bytes])
            if pad:
                f.write(pad)


def main():
    input_path = Path("input.bmp")
    output_path = Path("output.bmp")
    width, height, pixels, header, data_offset = read_bmp(input_path)
    new_w, new_h, rotated = rotate_clockwise(width, height, pixels)
    write_bmp(output_path, new_w, new_h, rotated, header, data_offset)


if __name__ == "__main__":
    main()
