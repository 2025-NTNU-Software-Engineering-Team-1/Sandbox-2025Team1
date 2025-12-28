import sys


def calc_digit_sum(v):
    n = -v if v < 0 else v
    if n == 0:
        return 0
    total = 0
    while n > 0:
        total += n % 10
        n //= 10
    return total


def less_item(a, b):
    if a[1] != b[1]:
        return a[1] < b[1]
    return a[0] < b[0]


def merge_step(arr, temp, left, mid, right):
    i = left
    j = mid
    k = left
    while i < mid and j < right:
        if less_item(arr[i], arr[j]):
            temp[k] = arr[i]
            i += 1
        else:
            temp[k] = arr[j]
            j += 1
        k += 1
    while i < mid:
        temp[k] = arr[i]
        i += 1
        k += 1
    while j < right:
        temp[k] = arr[j]
        j += 1
        k += 1
    for idx in range(left, right):
        arr[idx] = temp[idx]


def merge_order(arr, temp, left, right):
    if right - left <= 1:
        return
    mid = left + (right - left) // 2
    merge_order(arr, temp, left, mid)
    merge_order(arr, temp, mid, right)
    merge_step(arr, temp, left, mid, right)


def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    values = [int(next(it)) for _ in range(n)]
    arr = [(v, calc_digit_sum(v)) for v in values]
    temp = arr.copy()
    merge_order(arr, temp, 0, len(arr))
    sys.stdout.write(" ".join(str(v) for v, _ in arr) + "\n")


if __name__ == "__main__":
    main()
