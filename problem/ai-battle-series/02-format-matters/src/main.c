#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int n = 0;
    int q = 0;
    if (scanf("%d %d", &n, &q) != 2) {
        return 0;
    }
    if (n <= 0) {
        return 0;
    }

    double *prefix_score = (double *)calloc((size_t)n + 1, sizeof(double));
    double *prefix_weight = (double *)calloc((size_t)n + 1, sizeof(double));
    if (!prefix_score || !prefix_weight) {
        free(prefix_score);
        free(prefix_weight);
        return 0;
    }

    for (int i = 1; i <= n; i++) {
        double score = 0.0;
        double weight = 0.0;
        scanf("%lf %lf", &score, &weight);
        prefix_score[i] = prefix_score[i - 1] + score * weight;
        prefix_weight[i] = prefix_weight[i - 1] + weight;
    }

    for (int i = 0; i < q; i++) {
        int l = 0;
        int r = 0;
        scanf("%d %d", &l, &r);
        double sum_score = prefix_score[r] - prefix_score[l - 1];
        double sum_weight = prefix_weight[r] - prefix_weight[l - 1];
        double avg = 0.0;
        if (sum_weight != 0.0) {
            avg = sum_score / sum_weight;
        }
        printf("%.6f\n", avg);
    }

    free(prefix_score);
    free(prefix_weight);
    return 0;
}
