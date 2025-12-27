#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

static uint32_t read_le32(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static int32_t read_le32s(const unsigned char *p) {
    return (int32_t)read_le32(p);
}

static uint16_t read_le16(const unsigned char *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static void write_le32(unsigned char *p, uint32_t v) {
    p[0] = (unsigned char)(v & 0xff);
    p[1] = (unsigned char)((v >> 8) & 0xff);
    p[2] = (unsigned char)((v >> 16) & 0xff);
    p[3] = (unsigned char)((v >> 24) & 0xff);
}

static void write_le16(unsigned char *p, uint16_t v) {
    p[0] = (unsigned char)(v & 0xff);
    p[1] = (unsigned char)((v >> 8) & 0xff);
}

int main(void) {
    const char *input_path = "input.bmp";
    const char *output_path = "output.bmp";
    FILE *fp = fopen(input_path, "rb");
    if (!fp) {
        fprintf(stderr, "failed to open %s\n", input_path);
        return 1;
    }

    unsigned char header_min[54];
    if (fread(header_min, 1, sizeof(header_min), fp) != sizeof(header_min)) {
        fprintf(stderr, "invalid bmp header\n");
        fclose(fp);
        return 1;
    }
    if (header_min[0] != 'B' || header_min[1] != 'M') {
        fprintf(stderr, "not a bmp file\n");
        fclose(fp);
        return 1;
    }

    uint32_t data_offset = read_le32(header_min + 10);
    int32_t width = read_le32s(header_min + 18);
    int32_t height = read_le32s(header_min + 22);
    uint16_t bpp = read_le16(header_min + 28);
    uint32_t compression = read_le32(header_min + 30);
    if (bpp != 24 || compression != 0 || width <= 0 || height == 0) {
        fprintf(stderr, "unsupported bmp format\n");
        fclose(fp);
        return 1;
    }

    // rewind and read full header (may be larger than 54 bytes)
    unsigned char *header = malloc(data_offset);
    if (!header) {
        fclose(fp);
        return 1;
    }
    fseek(fp, 0, SEEK_SET);
    if (fread(header, 1, data_offset, fp) != data_offset) {
        fprintf(stderr, "failed to read bmp header\n");
        free(header);
        fclose(fp);
        return 1;
    }

    int32_t abs_height = height > 0 ? height : -height;
    size_t stride_in = ((size_t)width * 3 + 3) / 4 * 4;
    size_t pixel_bytes = (size_t)width * abs_height * 3;
    unsigned char *pixels = malloc(pixel_bytes);
    unsigned char *rowbuf = malloc(stride_in);
    if (!pixels || !rowbuf) {
        free(header);
        free(pixels);
        free(rowbuf);
        fclose(fp);
        return 1;
    }

    // Read pixel data into top-down order.
    for (int32_t row = 0; row < abs_height; ++row) {
        if (fread(rowbuf, 1, stride_in, fp) != stride_in) {
            fprintf(stderr, "unexpected eof\n");
            free(header);
            free(pixels);
            free(rowbuf);
            fclose(fp);
            return 1;
        }
        int32_t y = height > 0 ? (abs_height - 1 - row) : row;
        unsigned char *dst = pixels + (size_t)y * width * 3;
        for (int32_t x = 0; x < width; ++x) {
            dst[x * 3 + 0] = rowbuf[x * 3 + 0];
            dst[x * 3 + 1] = rowbuf[x * 3 + 1];
            dst[x * 3 + 2] = rowbuf[x * 3 + 2];
        }
    }
    free(rowbuf);
    fclose(fp);

    // Rotate 90 degrees clockwise.
    int32_t new_width = abs_height;
    int32_t new_height = width;  // keep bottom-up layout (positive height)
    size_t rotated_bytes = (size_t)new_width * new_height * 3;
    unsigned char *rotated = malloc(rotated_bytes);
    if (!rotated) {
        free(header);
        free(pixels);
        return 1;
    }
    for (int32_t y = 0; y < abs_height; ++y) {
        for (int32_t x = 0; x < width; ++x) {
            size_t src_idx = (size_t)(y * width + x) * 3;
            int32_t nx = abs_height - 1 - y;
            int32_t ny = x;
            size_t dst_idx = (size_t)(ny * new_width + nx) * 3;
            rotated[dst_idx + 0] = pixels[src_idx + 0];
            rotated[dst_idx + 1] = pixels[src_idx + 1];
            rotated[dst_idx + 2] = pixels[src_idx + 2];
        }
    }
    free(pixels);

    // Update header fields for the rotated image.
    size_t stride_out = ((size_t)new_width * 3 + 3) / 4 * 4;
    uint32_t image_size = (uint32_t)(stride_out * new_height);
    uint32_t file_size = data_offset + image_size;
    write_le32(header + 2, file_size);
    write_le32(header + 18, (uint32_t)new_width);
    write_le32(header + 22, (uint32_t)new_height);
    write_le32(header + 34, image_size);
    // keep bpp/compression unchanged

    FILE *out = fopen(output_path, "wb");
    if (!out) {
        free(header);
        free(rotated);
        return 1;
    }
    fwrite(header, 1, data_offset, out);

    unsigned char pad[3] = {0, 0, 0};
    size_t row_bytes = (size_t)new_width * 3;
    for (int32_t row = new_height - 1; row >= 0; --row) {
        const unsigned char *row_ptr = rotated + (size_t)row * row_bytes;
        fwrite(row_ptr, 1, row_bytes, out);
        if (stride_out > row_bytes) {
            fwrite(pad, 1, stride_out - row_bytes, out);
        }
    }

    free(header);
    free(rotated);
    fclose(out);
    return 0;
}
