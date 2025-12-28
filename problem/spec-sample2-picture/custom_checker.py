#!/usr/bin/env python3
import sys
from pathlib import Path


def main():
    solution_name = Path('/workspace/answer.out').read_text().strip()
    student_out = Path('/workspace/student/output.bmp')
    solution = Path('/workspace/teacher') / solution_name
    if not student_out.exists():
        print('STATUS:WA')
        print('MESSAGE:output.bmp missing')
        return
    if not solution.exists():
        print('STATUS:JE')
        print('MESSAGE:solution missing')
        return
    if student_out.read_bytes() == solution.read_bytes():
        print('STATUS:AC')
        print('MESSAGE:ok')
    else:
        print('STATUS:WA')
        print('MESSAGE:output.bmp differs from solution')


if __name__ == '__main__':
    main()
