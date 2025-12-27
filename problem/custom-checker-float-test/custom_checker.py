#!/usr/bin/env python3
"""
Custom Checker for Floating Point Number Comparison
Allows small error tolerance (epsilon = 1e-6) when comparing floating point numbers.
"""
import sys


def check(input_file, output_file, answer_file):
    """
    Custom Checker for floating point comparison with tolerance.
    
    Args:
        input_file: Path to input file (contains N and numbers)
        output_file: Path to student output file
        answer_file: Path to expected answer file
    
    Returns:
        tuple: (status, message) where status is "AC" or "WA"
    """
    EPSILON = 1e-6  # Tolerance for floating point comparison

    try:
        # Read input to know expected count
        with open(input_file, 'r') as f:
            lines = f.read().strip().split('\n')
            n = int(lines[0])

        # Read student output
        with open(output_file, 'r') as f:
            student_output = f.read().strip()
            if not student_output:
                return "WA", "Empty output"
            student_lines = student_output.split('\n')
            student_nums = []
            for line in student_lines:
                line = line.strip()
                if line:
                    try:
                        student_nums.append(float(line))
                    except ValueError:
                        return "WA", f"Invalid number format: '{line}'"

        # Read expected answer
        with open(answer_file, 'r') as f:
            answer_output = f.read().strip()
            answer_lines = answer_output.split('\n')
            answer_nums = []
            for line in answer_lines:
                line = line.strip()
                if line:
                    answer_nums.append(float(line))

        # Check count
        if len(student_nums) != n:
            return "WA", f"Expected {n} numbers, got {len(student_nums)}"

        if len(student_nums) != len(answer_nums):
            return "WA", f"Line count mismatch: expected {len(answer_nums)}, got {len(student_nums)}"

        # Compare each number with tolerance
        for i, (student_val,
                answer_val) in enumerate(zip(student_nums, answer_nums), 1):
            diff = abs(student_val - answer_val)
            if diff > EPSILON:
                return "WA", (
                    f"Number {i}: expected {answer_val:.10f}, got {student_val:.10f} "
                    f"(difference = {diff:.2e}, tolerance = {EPSILON:.2e})")

        return "AC", f"All {n} numbers match within tolerance (ε = {EPSILON:.2e})"

    except FileNotFoundError as e:
        return "WA", f"File not found: {e.filename}"
    except Exception as e:
        return "WA", f"Checker error: {str(e)}"


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("STATUS: WA")
        print("MESSAGE: Invalid checker arguments (expected 3 file paths)")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    answer_file = sys.argv[3]

    status, message = check(input_file, output_file, answer_file)

    print(f"STATUS: {status}")
    print(f"MESSAGE: {message}")
