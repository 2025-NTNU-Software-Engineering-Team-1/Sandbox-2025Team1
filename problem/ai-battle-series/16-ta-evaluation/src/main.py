import json
import sys


def main():
    payload = {
        "evaluations": [
            {
                "ta_name": "ChatGPT",
                "score": 8,
                "comment": "Clear and helpful explanations.",
                "strengths": ["Fast", "Friendly"],
                "improvements": ["Be more concise"],
            },
            {
                "ta_name": "Gemini",
                "score": 7,
                "comment": "Useful but sometimes inconsistent.",
                "strengths": ["Creative"],
                "improvements": ["Stay consistent"],
            },
            {
                "ta_name": "Opus",
                "score": 9,
                "comment": "Deep and structured guidance.",
                "strengths": ["Thorough"],
                "improvements": ["Shorten responses"],
            },
        ],
        "overall_comment":
        "Great support overall.",
        "would_recommend":
        True,
    }

    with open("evaluation.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    sys.stdout.write("Evaluation submitted successfully!\n")


if __name__ == "__main__":
    main()
