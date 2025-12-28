import sys
import csv


def solve():
    # Read from stdin (which will be redirected from the input file)
    reader = csv.DictReader(sys.stdin)
    scores = []
    for row in reader:
        try:
            scores.append(float(row['score']))
        except ValueError:
            continue

    if scores:
        print(f"{sum(scores) / len(scores):.1f}")
    else:
        print("0.0")


if __name__ == '__main__':
    solve()
