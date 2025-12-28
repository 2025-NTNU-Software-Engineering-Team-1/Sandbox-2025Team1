import math
import sys


def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    p = int(next(it))
    nums = [int(next(it)) for _ in range(n)]

    nums_sorted = sorted(nums)
    max_val = nums_sorted[-1]
    min_val = nums_sorted[0]
    mean = sum(nums) / n

    if n % 2 == 1:
        median = nums_sorted[n // 2]
    else:
        median = (nums_sorted[n // 2 - 1] + nums_sorted[n // 2]) / 2.0

    variance = sum((x - mean)**2 for x in nums) / n
    stddev = math.sqrt(variance)

    position = p * (n + 1) / 100.0
    if position <= 1:
        percentile = nums_sorted[0]
    elif position >= n:
        percentile = nums_sorted[-1]
    else:
        k = int(math.floor(position))
        d = position - k
        lower = nums_sorted[k - 1]
        upper = nums_sorted[k]
        percentile = lower + d * (upper - lower)

    print(f"Max: {max_val}")
    print(f"Min: {min_val}")
    print(f"Mean: {mean:.2f}")
    print(f"Median: {median:.2f}")
    print(f"StdDev: {stddev:.2f}")
    print(f"P{p}: {percentile:.2f}")


if __name__ == "__main__":
    main()
