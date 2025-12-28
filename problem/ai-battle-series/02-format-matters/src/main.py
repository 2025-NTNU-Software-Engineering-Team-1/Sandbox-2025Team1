import sys


def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    q = int(next(it))

    prefix_score = [0.0] * (n + 1)
    prefix_weight = [0.0] * (n + 1)

    for i in range(1, n + 1):
        score = float(next(it))
        weight = float(next(it))
        prefix_score[i] = prefix_score[i - 1] + score * weight
        prefix_weight[i] = prefix_weight[i - 1] + weight

    out_lines = []
    for _ in range(q):
        l = int(next(it))
        r = int(next(it))
        sum_score = prefix_score[r] - prefix_score[l - 1]
        sum_weight = prefix_weight[r] - prefix_weight[l - 1]
        avg = sum_score / sum_weight if sum_weight else 0.0
        out_lines.append(f"{avg:.6f}")
    sys.stdout.write("\n".join(out_lines) + "\n")


if __name__ == "__main__":
    main()
