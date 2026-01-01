#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int n = 0;
    if (scanf("%d", &n) != 1) {
        return 0;
    }
    if (n <= 0) {
        printf("0\n");
        return 0;
    }

    int *nums = (int *)malloc(sizeof(int) * (size_t)n);
    int *tails = (int *)malloc(sizeof(int) * (size_t)n);
    if (!nums || !tails) {
        free(nums);
        free(tails);
        return 0;
    }

    for (int i = 0; i < n; i++) {
        scanf("%d", &nums[i]);
    }

    int len = 0;
    for (int i = 0; i < n; i++) {
        int x = nums[i];
        int lo = 0;
        int hi = len;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            if (tails[mid] < x) {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        }
        if (lo == len) {
            tails[len++] = x;
        } else {
            tails[lo] = x;
        }
    }

    printf("%d\n", len);
    free(nums);
    free(tails);
    return 0;
}
