#include <math.h>

double calculate_weighted_gpa(int scores[], int credits[], int n) {
    long long sum = 0;
    long long credit_sum = 0;
    for (int i = 0; i < n; i++) {
        sum += (long long)scores[i] * (long long)credits[i];
        credit_sum += credits[i];
    }
    if (credit_sum == 0) {
        return 0.0;
    }
    return (double)sum / (double)credit_sum;
}

int calculate_percentile_rank(int all_scores[], int n, int my_score) {
    int less = 0;
    int equal = 0;
    for (int i = 0; i < n; i++) {
        if (all_scores[i] < my_score) {
            less++;
        } else if (all_scores[i] == my_score) {
            equal++;
        }
    }
    double wins = less + (equal > 0 ? (equal - 1) / 2.0 : 0.0);
    double pr = wins * 100.0 / (double)n;
    int result = (int)(pr + 0.5);
    return result;
}

double score_to_gpa_points(int score) {
    if (score >= 90) return 4.3;
    if (score >= 85) return 4.0;
    if (score >= 80) return 3.7;
    if (score >= 77) return 3.3;
    if (score >= 73) return 3.0;
    if (score >= 70) return 2.7;
    if (score >= 67) return 2.3;
    if (score >= 63) return 2.0;
    if (score >= 60) return 1.7;
    if (score >= 50) return 1.0;
    return 0.0;
}

int check_graduation(double gpa, int total_credits, int required_credits,
                     int failed_subjects, int max_failed) {
    if (gpa >= 3.8 && total_credits >= required_credits * 1.1 - 1e-9 && failed_subjects == 0) {
        return 2;
    }
    if (total_credits >= required_credits && failed_subjects <= max_failed) {
        return 1;
    }
    return 0;
}
