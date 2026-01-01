import sys


def main():
    data = sys.stdin.read().strip().split()
    if len(data) < 2:
        return
    dept = data[0]
    threshold = int(data[1])

    courses = [
        {
            "name": "進階機器學習",
            "professor": "陳教授",
            "title": "教授",
            "capacity": 30,
            "enrolled": 28,
            "dept": "CS"
        },
        {
            "name": "資料結構",
            "professor": "王教授",
            "title": "副教授",
            "capacity": 50,
            "enrolled": 45,
            "dept": "CS"
        },
        {
            "name": "計算機組織",
            "professor": "李教授",
            "title": "助理教授",
            "capacity": 40,
            "enrolled": 12,
            "dept": "CS"
        },
        {
            "name": "微積分",
            "professor": "張教授",
            "title": "教授",
            "capacity": 60,
            "enrolled": 50,
            "dept": "MATH"
        },
    ]

    results = []
    for c in courses:
        if c["dept"] != dept:
            continue
        popularity = c["enrolled"] * 100.0 / c["capacity"]
        if popularity + 1e-9 < threshold:
            continue
        results.append((popularity, c))

    if not results:
        print("No matching courses")
        return

    results.sort(key=lambda x: (-x[0], x[1]["name"]))
    for popularity, c in results:
        print(
            f"{c['name']} by {c['professor']} ({c['title']}) - {popularity:.1f}% ({c['enrolled']}/{c['capacity']})"
        )


if __name__ == "__main__":
    main()
