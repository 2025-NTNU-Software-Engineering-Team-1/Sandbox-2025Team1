import sys
from pathlib import Path


def wa(msg: str):
    Path("Check_Result").write_text(f"STATUS: WA\nMESSAGE: {msg}\n")
    sys.exit(0)


def ac(msg: str = "OK"):
    Path("Check_Result").write_text(f"STATUS: AC\nMESSAGE: {msg}\n")
    sys.exit(0)


def main():
    # teacher sends a few queries, student must reply with (val * idx) + prev_sum
    queries = [3, 5, 2, 9]
    running = 0
    print(len(queries), flush=True)
    for idx, val in enumerate(queries, start=1):
        print(val, flush=True)
        line = sys.stdin.readline()
        if not line:
            wa(f"no response for query {idx}")
        try:
            ans = int(line.strip())
        except ValueError:
            wa(f"non-integer response on query {idx}: {line!r}")
        expected = running + val * idx
        if ans != expected:
            wa(f"wrong answer on query {idx}, expect {expected}, got {ans}")
        running = ans
    ac()


if __name__ == "__main__":
    main()
