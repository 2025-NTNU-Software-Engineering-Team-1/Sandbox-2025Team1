import sys


def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    best = {}
    for _ in range(n):
        name = next(it)
        priority = int(next(it))
        if name not in best or priority > best[name]:
            best[name] = priority
    items = sorted(best.items(), key=lambda x: (-x[1], x[0]))
    if items:
        sys.stdout.write("\n".join(name for name, _ in items) + "\n")


if __name__ == "__main__":
    main()
