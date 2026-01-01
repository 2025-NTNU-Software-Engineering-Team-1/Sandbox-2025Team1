def calculate_weighted_gpa(scores, credits):
    total = sum(s * c for s, c in zip(scores, credits))
    total_credits = sum(credits)
    return total / total_credits if total_credits else 0.0


def calculate_percentile_rank(all_scores, my_score):
    n = len(all_scores)
    if n == 0:
        return 0
    less = sum(1 for s in all_scores if s < my_score)
    equal = sum(1 for s in all_scores if s == my_score)
    wins = less + (equal - 1) * 0.5 if equal > 0 else less
    pr = wins * 100.0 / n
    return int(pr + 0.5)


def score_to_gpa_points(score):
    if score >= 90:
        return 4.3
    if score >= 85:
        return 4.0
    if score >= 80:
        return 3.7
    if score >= 77:
        return 3.3
    if score >= 73:
        return 3.0
    if score >= 70:
        return 2.7
    if score >= 67:
        return 2.3
    if score >= 63:
        return 2.0
    if score >= 60:
        return 1.7
    if score >= 50:
        return 1.0
    return 0.0


def check_graduation(gpa, total_credits, required_credits, failed_subjects,
                     max_failed):
    if (gpa >= 3.8 and total_credits * 10 >= required_credits * 11
            and failed_subjects == 0):
        return 2
    if total_credits >= required_credits and failed_subjects <= max_failed:
        return 1
    return 0
