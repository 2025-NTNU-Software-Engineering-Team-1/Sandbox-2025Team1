def main():
    try:
        with open("image.ppm", "r") as f:
            # Simple PPM P3 parser
            lines = f.readlines()
            # Filter out comments
            data = []
            for line in lines:
                parts = line.split('#')[0].split()
                data.extend(parts)

            if not data or data[0] != 'P3':
                print("Invalid PPM")
                return

            width = int(data[1])
            height = int(data[2])
            print(f"{width} {height}")
    except FileNotFoundError:
        print("Image not found")


if __name__ == "__main__":
    main()
