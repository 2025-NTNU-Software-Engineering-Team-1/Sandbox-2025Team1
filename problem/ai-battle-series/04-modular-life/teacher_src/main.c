#include <stdio.h>
#include "function.h"

int main(void) {
    int test_type;
    if (scanf("%d", &test_type) != 1) {
        return 1;
    }

    if (test_type == 1) {
        // 測試 calculate_weighted_gpa
        int n;
        scanf("%d", &n);
        int scores[100], credits[100];
        for (int i = 0; i < n; i++) {
            scanf("%d %d", &scores[i], &credits[i]);
        }
        printf("%.2f\n", calculate_weighted_gpa(scores, credits, n));
    }
    else if (test_type == 2) {
        // 測試 calculate_percentile_rank
        int n, my_score;
        scanf("%d %d", &n, &my_score);
        int all_scores[1000];
        for (int i = 0; i < n; i++) {
            scanf("%d", &all_scores[i]);
        }
        printf("%d\n", calculate_percentile_rank(all_scores, n, my_score));
    }
    else if (test_type == 3) {
        // 測試 score_to_gpa_points
        int score;
        scanf("%d", &score);
        printf("%.1f\n", score_to_gpa_points(score));
    }
    else if (test_type == 4) {
        // 測試 check_graduation
        double gpa;
        int total, required, failed, max_failed;
        scanf("%lf %d %d %d %d", &gpa, &total, &required, &failed, &max_failed);
        int result = check_graduation(gpa, total, required, failed, max_failed);
        if (result == 0) printf("NOT QUALIFIED\n");
        else if (result == 1) printf("QUALIFIED\n");
        else printf("EARLY GRADUATION\n");
    }

    return 0;
}
