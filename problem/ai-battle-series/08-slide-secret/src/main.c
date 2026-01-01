#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

int main(void) {
    char filename[256];
    if (scanf("%255s", filename) != 1) {
        return 0;
    }

    FILE *fp = fopen(filename, "rb");
    if (!fp) {
        return 0;
    }

    unsigned char header[54];
    if (fread(header, 1, 54, fp) != 54) {
        fclose(fp);
        return 0;
    }

    int32_t width = *(int32_t *)&header[18];
    int32_t height = *(int32_t *)&header[22];
    if (height < 0) {
        height = -height;
    }
    int row_padded = (width * 3 + 3) & (~3);

    unsigned char *row = (unsigned char *)malloc((size_t)row_padded);
    if (!row) {
        fclose(fp);
        return 0;
    }

    int bit_count = 0;
    unsigned char current = 0;
    int done = 0;

    for (int i = 0; i < height && !done; i++) {
        if (fread(row, 1, (size_t)row_padded, fp) != (size_t)row_padded) {
            break;
        }
        for (int j = 0; j < width; j++) {
            unsigned char r = row[j * 3 + 2];
            current = (unsigned char)((current << 1) | (r & 1));
            bit_count++;
            if (bit_count == 8) {
                if (current == 0) {
                    done = 1;
                    break;
                }
                putchar(current);
                bit_count = 0;
                current = 0;
            }
        }
    }

    putchar('\n');
    free(row);
    fclose(fp);
    return 0;
}
