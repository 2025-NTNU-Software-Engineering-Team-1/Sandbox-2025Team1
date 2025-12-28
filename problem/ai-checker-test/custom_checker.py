#!/usr/bin/env python3
"""
AI-Powered Custom Checker Example

This checker demonstrates how to use the AI API for grading.
It receives AI_API_KEY and AI_MODEL as environment variables and
uses them to call the Google Gemini API for semantic evaluation.

Note: This is a demonstration - in production, you would implement
actual AI API calls using the google-generativeai library.
"""
import sys
import os

DEBUG = os.environ.get("CHECKER_DEBUG", "1").strip().lower() not in (
    "",
    "0",
    "false",
    "no",
    "off",
)


def debug_log(message):
    if DEBUG:
        print(f"[DEBUG] {message}", file=sys.stderr)


def check(input_file, output_file, answer_file):
    """
    AI-Powered Custom Checker.
    
    Uses Gemini API to semantically evaluate student answers.
    Falls back to exact matching if AI is not available.
    
    Args:
        input_file: Path to input file (contains the question)
        output_file: Path to student output file
        answer_file: Path to expected answer file
    
    Returns:
        tuple: (status, message) where status is "AC" or "WA"
    """
    # Get AI configuration from environment
    api_key = os.environ.get('AI_API_KEY')
    model = os.environ.get('AI_MODEL', 'gemini-2.5-flash')

    try:
        debug_log("files: input=%s output=%s answer=%s" %
                  (input_file, output_file, answer_file))
        debug_log("ai_config: api_key_present=%s model=%s" %
                  (bool(api_key), model))
        # Read files
        with open(input_file, 'r') as f:
            question = f.read().strip()

        with open(output_file, 'r') as f:
            student_answer = f.read().strip()

        with open(answer_file, 'r') as f:
            expected_answer = f.read().strip()

        debug_log("lengths: question=%d student=%d expected=%d" %
                  (len(question), len(student_answer), len(expected_answer)))
        debug_log("question_preview=%r" % question[:160])
        debug_log("student_preview=%r" % student_answer[:160])
        debug_log("expected_preview=%r" % expected_answer[:160])

        if not student_answer:
            debug_log("empty student output")
            return "WA", "Empty output"

        # If AI API is available, use semantic evaluation
        if api_key:
            try:
                debug_log("ai_eval: starting")
                result = evaluate_with_ai(api_key, model, question,
                                          student_answer, expected_answer)
                debug_log("ai_eval: result=%s message=%r" % result)
                return result
            except Exception as e:
                # Fall back to exact matching on AI failure
                print(f"AI evaluation failed: {e}", file=sys.stderr)

        # Fallback: exact matching (case-insensitive, whitespace-normalized)
        student_normalized = ' '.join(student_answer.lower().split())
        expected_normalized = ' '.join(expected_answer.lower().split())
        debug_log("fallback: normalized_student=%r" % student_normalized[:200])
        debug_log("fallback: normalized_expected=%r" %
                  expected_normalized[:200])

        if student_normalized == expected_normalized:
            return "AC", "Exact match (AI disabled or failed)"
        else:
            debug_log("fallback: mismatch")
            return "WA", f"Answer mismatch. Expected: '{expected_answer[:50]}...'"

    except FileNotFoundError as e:
        debug_log("file_not_found: %s" % e.filename)
        return "WA", f"File not found: {e.filename}"
    except Exception as e:
        debug_log("checker_error: %s" % str(e))
        return "WA", f"Checker error: {str(e)}"


def evaluate_with_ai(api_key, model, question, student_answer,
                     expected_answer):
    """
    Use Google Gemini API to semantically evaluate the answer.
    
    Returns:
        tuple: (status, message)
    """
    # Note: In production, you would use the actual google-generativeai library:
    #
    # import google.generativeai as genai
    # genai.configure(api_key=api_key)
    # model = genai.GenerativeModel(model)
    # response = model.generate_content(prompt)
    #
    # For this demo, we simulate the AI evaluation:

    prompt = f"""
            You are a grading assistant. Evaluate if the student's answer is semantically correct.

            Question: {question}

            Expected Answer: {expected_answer}

            Student Answer: {student_answer}

            Is the student's answer correct? Reply with only "CORRECT" or "INCORRECT" followed by a brief explanation.
            """
    debug_log("ai_prompt_len=%d" % len(prompt))

    # Simulated AI response for demo (remove in production)
    # In production, call the actual Gemini API here

    # For demo purposes, do semantic comparison
    student_words = set(student_answer.lower().split())
    expected_words = set(expected_answer.lower().split())

    # Check for significant word overlap (simple semantic check)
    overlap = len(student_words & expected_words)
    total = len(expected_words)
    ratio = (overlap / total) if total else 0.0
    debug_log(
        "ai_eval_demo: student_words=%d expected_words=%d overlap=%d ratio=%.4f"
        % (len(student_words), len(expected_words), overlap, ratio))

    if total > 0 and ratio >= 0.7:
        return "AC", f"AI Evaluation: Semantically correct (model: {model})"
    else:
        return "WA", f"AI Evaluation: Answer does not match expected semantics"


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
