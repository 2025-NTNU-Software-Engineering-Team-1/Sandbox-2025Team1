import csv
import sys


def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    k = int(next(it))
    if k <= 0:
        print(0)
        return
    subjects = [next(it) for _ in range(k)]
    subject_set = set(subjects)
    need_help = {s: set() for s in subjects}

    try:
        with open("grades.csv", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                subject = row.get("subject", "")
                status = row.get("status", "")
                student = row.get("student_id", "")
                if subject in subject_set and status == "NEED_HELP":
                    need_help[subject].add(student)
    except FileNotFoundError:
        print(0)
        return

    if not subjects:
        print(0)
        return

    result = []
    for student in need_help[subjects[0]]:
        if all(student in need_help[subj] for subj in subjects[1:]):
            result.append(student)

    result.sort()
    print(len(result))
    for student in result:
        print(student)


if __name__ == "__main__":
    main()
