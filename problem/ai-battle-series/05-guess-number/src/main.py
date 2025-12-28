import sys


def main():
    line = sys.stdin.readline().strip()
    if not line:
        return
    n = int(line)
    low, high = 1, n
    while low <= high:
        mid = (low + high) // 2
        print(f"guess {mid}", flush=True)
        resp = sys.stdin.readline().strip()
        if resp == "CORRECT":
            return
        if resp == "HIGHER":
            low = mid + 1
        else:
            high = mid - 1


if __name__ == "__main__":
    main()
