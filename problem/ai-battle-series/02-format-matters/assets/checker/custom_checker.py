#!/usr/bin/env python3
"""
Custom Checker (Token-based with Float Tolerance)

- Compares expected and student outputs token-by-token.
- If both tokens are numbers, compare with epsilon.
- Otherwise compare as exact string tokens.
"""
import math
import sys

EPSILON = 1e-6


def _is_number(token: str):
    try:
        value = float(token)
    except ValueError:
        return False, None
    if math.isnan(value) or math.isinf(value):
        return False, None
    return True, value


def check(input_file, output_file, answer_file):
    try:
        with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
            output_tokens = f.read().strip().split()
        with open(answer_file, 'r', encoding='utf-8', errors='ignore') as f:
            answer_tokens = f.read().strip().split()
    except FileNotFoundError as e:
        return "WA", f"File not found: {e.filename}"
    except Exception as e:
        return "WA", f"Checker error: {e}"

    if len(output_tokens) != len(answer_tokens):
        return "WA", (
            f"Token count mismatch: expected {len(answer_tokens)}, got {len(output_tokens)}"
        )

    for idx, (out_tok, ans_tok) in enumerate(zip(output_tokens, answer_tokens),
                                             1):
        out_is_num, out_val = _is_number(out_tok)
        ans_is_num, ans_val = _is_number(ans_tok)
        if out_is_num and ans_is_num:
            if abs(out_val - ans_val) > EPSILON:
                return "WA", (
                    f"Token {idx} numeric mismatch: expected {ans_val:.10f}, got {out_val:.10f}"
                )
        else:
            if out_tok != ans_tok:
                return "WA", f"Token {idx} mismatch: expected '{ans_tok}', got '{out_tok}'"

    return "AC", "Tokens match within tolerance"


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("STATUS: WA")
        print("MESSAGE: Invalid checker arguments (expected 3 file paths)")
        sys.exit(1)

    status, message = check(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"STATUS: {status}")
    print(f"MESSAGE: {message}")
