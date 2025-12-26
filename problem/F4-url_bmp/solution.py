import struct
from pathlib import Path
import urllib.request
import ssl  # 新增 ssl 模組


def read_bmp(path: Path):
    """
    從 spec-sample2-picture/src/solution.py 保留的讀取函式。
    讀取 BMP 並正規化為 top-down 的 RGB bytearray。
    """
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
        src = mv[row * stride : row * stride + width * 3]
        y = abs_h - 1 - row if height > 0 else row
        start = y * width * 3
        pixels[start : start + width * 3] = src
    header = bytearray(data[:data_offset])
    return width, abs_h, pixels, header, data_offset


def write_bmp(
    path: Path,
    width: int,
    height: int,
    pixels: bytearray,
    header: bytearray,
    data_offset: int,
):
    """
    從 spec-sample2-picture/src/solution.py 保留的寫入函式。
    將 RGB bytearray 寫回 BMP 檔案 (處理 padding 與 bottom-up 順序)。
    """
    row_bytes = width * 3
    stride = ((row_bytes + 3) // 4) * 4
    image_size = stride * height
    # 更新檔頭資訊
    struct.pack_into("<I", header, 2, data_offset + image_size)
    struct.pack_into("<i", header, 18, width)
    struct.pack_into("<i", header, 22, height)
    struct.pack_into("<I", header, 34, image_size)
    pad = b"\x00" * (stride - row_bytes) if stride > row_bytes else b""

    with path.open("wb") as f:
        f.write(header)
        for row in range(height - 1, -1, -1):  # bottom-up
            start = row * row_bytes
            f.write(pixels[start : start + row_bytes])
            if pad:
                f.write(pad)


def download_file(url: str, dest_path: Path):
    """
    下載檔案的函式 (已修正 SSL 錯誤)
    """
    print(f"Downloading from {url}...")
    try:
        # 處理 GitHub blob URL，轉換為 raw URL 以獲取原始圖片
        if "github.com" in url and "/blob/" in url:
            url = url.replace("github.com", "raw.githubusercontent.com").replace(
                "/blob/", "/"
            )
            print(f"Converted to raw URL: {url}")

        # 建立一個不驗證 SSL 憑證的 context
        ssl_context = ssl._create_unverified_context()

        # 傳入 context 參數來忽略憑證錯誤
        with urllib.request.urlopen(
            url, context=ssl_context
        ) as response, dest_path.open("wb") as out_file:
            out_file.write(response.read())
        print(f"Saved to {dest_path}")
    except Exception as e:
        print(f"Error downloading file: {e}")
        raise


def draw_on_image(width: int, height: int, pixels: bytearray):
    """
    在圖片上隨便畫點東西。
    這裡是畫一個紅色的正方形。
    """
    # 設定繪圖顏色 (B, G, R)
    color = (0, 0, 255)  # 紅色

    # 在左上角 (10, 10) 的位置畫一個 50x50 的方塊
    start_x, start_y = 10, 10
    rect_w, rect_h = 50, 50

    for y in range(start_y, min(start_y + rect_h, height)):
        for x in range(start_x, min(start_x + rect_w, width)):
            idx = (y * width + x) * 3
            pixels[idx] = color[0]  # Blue
            pixels[idx + 1] = color[1]  # Green
            pixels[idx + 2] = color[2]  # Red


def main():
    # 1. 設定路徑與 URL
    bmp_url = "https://github.com/max52015/BMP_Download/blob/main/BLACK.bmp"
    input_filename = Path("downloaded.bmp")
    output_filename = Path("output.bmp")

    # 2. 下載 BMP
    download_file(bmp_url, input_filename)

    # 3. 讀取 BMP
    width, height, pixels, header, data_offset = read_bmp(input_filename)

    # 4. 修改圖片
    draw_on_image(width, height, pixels)

    # 5. 輸出結果
    write_bmp(output_filename, width, height, pixels, header, data_offset)
    print(f"Done! Output saved to {output_filename}")


if __name__ == "__main__":
    main()
