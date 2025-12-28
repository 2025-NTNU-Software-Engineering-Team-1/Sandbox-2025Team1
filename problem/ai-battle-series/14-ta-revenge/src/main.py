import sys


def compute_result(operation, data):
    if not data:
        return 0
    if operation == "sum":
        return sum(data)
    if operation == "product":
        result = 1
        for x in data:
            result *= x
        return result
    if operation == "max":
        return max(data)
    return min(data)


def main():
    line = sys.stdin.readline().strip()
    if not line:
        return
    n = int(line)
    low, high = 1000, n
    while low <= high:
        mid = (low + high) // 2
        print(f"guess {mid}", flush=True)
        resp = sys.stdin.readline().strip()
        if resp == "CORRECT":
            break
        if resp == "HIGHER":
            low = mid + 1
        else:
            high = mid - 1

    data = [3, 1, 4, 1, 5]
    operation = "sum"
    result = compute_result(operation, data)
    sys.stdout.write(str(result) + "\n")


if __name__ == "__main__":
    main()
