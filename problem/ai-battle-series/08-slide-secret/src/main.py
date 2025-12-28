import sys


def main():
    filename = sys.stdin.readline().strip()
    if not filename:
        return
    try:
        with open(filename, "rb") as f:
            header = f.read(54)
            if len(header) < 54:
                return
            width = int.from_bytes(header[18:22], "little", signed=True)
            height = int.from_bytes(header[22:26], "little", signed=True)
            if height < 0:
                height = -height
            row_padded = (width * 3 + 3) & ~3
            bits = []
            for _ in range(height):
                row = f.read(row_padded)
                if len(row) < row_padded:
                    break
                for j in range(width):
                    r = row[j * 3 + 2]
                    bits.append(r & 1)
    except FileNotFoundError:
        return

    chars = []
    current = 0
    count = 0
    for bit in bits:
        current = (current << 1) | bit
        count += 1
        if count == 8:
            if current == 0:
                break
            chars.append(chr(current))
            current = 0
            count = 0

    sys.stdout.write("".join(chars) + "\n")


if __name__ == "__main__":
    main()
