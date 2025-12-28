import csv
import sys


def compute_gpa(path):
    total_points = 0.0
    total_credits = 0.0
    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                credits = int(row.get("credits", 0))
                grade = int(row.get("grade", 0))
                total_points += credits * grade
                total_credits += credits
    except FileNotFoundError:
        return 0.0
    if total_credits == 0:
        return 0.0
    return total_points / total_credits


def write_certificate(student_id, name, department, year, gpa):
    with open("certificate.txt", "w", encoding="utf-8") as f:
        f.write("GRADUATION CERTIFICATE\n")
        f.write(f"Student ID: {student_id}\n")
        f.write(f"Name: {name}\n")
        f.write(f"Department: {department}\n")
        f.write(f"GPA: {gpa:.2f}\n")
        f.write(f"Graduation Year: {year}\n")


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

    gpa = compute_gpa("transcript.csv")
    write_certificate("B12345678", "王小明", "資訊工程學系", 2024, gpa)
    sys.stdout.write(f"GPA: {gpa:.6f}\n")


if __name__ == "__main__":
    main()
