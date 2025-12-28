import sys


def main() -> int:
    data = sys.stdin.read().strip().split()
    if not data:
        return 0
    try:
        n = int(data[0])
    except ValueError:
        return 0

    best_priority = {}
    idx = 1
    for _ in range(n):
        if idx + 1 >= len(data):
            break
        name = data[idx]
        try:
            priority = int(data[idx + 1])
        except ValueError:
            priority = 0
        idx += 2
        prev = best_priority.get(name)
        if prev is None or priority > prev:
            best_priority[name] = priority

    items = sorted(best_priority.items(), key=lambda x: (-x[1], x[0]))
    out = "\n".join(name for name, _ in items)
    if out:
        out += "\n"
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
