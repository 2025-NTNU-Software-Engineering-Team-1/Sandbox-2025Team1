#!/usr/bin/env python3
"""
Custom Scorer for Partial Credit Test Problem
Demonstrates partial scoring based on case correctness and time efficiency.
"""
import json
import sys


def calculate_score(scoring_input):
    """
    計算部分計分，支援新版 Sandbox payload（tasks 為 dict，含 results 陣列）。
    """
    tasks = scoring_input.get("tasks", [])
    stats = scoring_input.get("stats", {})
    late_seconds = scoring_input.get("lateSeconds", 0)

    total_score = 0
    task_scores = []
    messages = []

    # 題目滿分設定，需與 meta.json 對齊
    task_weights = [30, 40, 30]

    for task_idx, task in enumerate(tasks):
        results = task.get("results", []) if isinstance(task, dict) else task
        task_weight = task_weights[task_idx] if task_idx < len(
            task_weights) else 0
        correct_count = sum(
            1 for case in results
            if isinstance(case, dict) and case.get("status") == "AC")
        total_count = len(results)
        if total_count > 0:
            task_score = int(task_weight * (correct_count / total_count))
        else:
            task_score = 0

        task_scores.append(task_score)
        total_score += task_score
        messages.append(
            f"Task {task_idx + 1}: {correct_count}/{total_count} cases correct → {task_score} points"
        )

    # 時間加分：平均時間 < 500ms 加 5%
    avg_time = stats.get("avgRunTime", 0)
    time_bonus = 0
    if avg_time > 0 and avg_time < 500:
        time_bonus = int(total_score * 0.05)
        total_score += time_bonus
        messages.append(
            f"Time Bonus: avg={avg_time:.0f}ms < 500ms → +{time_bonus} points")

    # 遲交扣分：每天扣 10%，最多 30%
    late_penalty = 0
    if isinstance(late_seconds, (int, float)) and late_seconds > 0:
        late_days = late_seconds / 86400
        penalty_rate = min(0.3, late_days * 0.1)
        late_penalty = int(total_score * penalty_rate)
        total_score -= late_penalty
        messages.append(
            f"Late Penalty: {late_seconds}s ({late_days:.1f} days) → -{late_penalty} points"
        )

    # 總分界限
    total_score = max(0, min(100, total_score))

    return {
        "score": total_score,
        "message": " | ".join(messages),
        "breakdown": {
            "taskScores": task_scores,
            "timeBonus": time_bonus,
            "latePenalty": late_penalty,
            "finalScore": total_score
        }
    }


if __name__ == "__main__":
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        # Calculate score
        result = calculate_score(input_data)

        # Output JSON to stdout
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    except Exception as e:
        # Error handling: return 0 score with error message
        error_result = {
            "score": 0,
            "message": f"Scorer Error: {str(e)}",
            "breakdown": {}
        }
        print(json.dumps(error_result, ensure_ascii=False))
        sys.exit(1)
