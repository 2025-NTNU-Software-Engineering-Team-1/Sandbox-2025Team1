def main():
    data = [(5, 70), (8, 75), (1, 80), (6, 80), (2, 85), (3, 90)]
    data.sort(key=lambda x: (x[1], x[0]))
    print(len(data))
    for student_id, _ in data:
        print(student_id)


if __name__ == "__main__":
    main()
