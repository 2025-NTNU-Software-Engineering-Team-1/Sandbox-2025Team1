#include <stdio.h>
#include <string.h>

static int compute_result(const char *operation, const int *data, int count) {
    if (count <= 0) {
        return 0;
    }
    if (strcmp(operation, "sum") == 0) {
        int sum = 0;
        for (int i = 0; i < count; i++) sum += data[i];
        return sum;
    }
    if (strcmp(operation, "product") == 0) {
        int prod = 1;
        for (int i = 0; i < count; i++) prod *= data[i];
        return prod;
    }
    if (strcmp(operation, "max") == 0) {
        int best = data[0];
        for (int i = 1; i < count; i++) if (data[i] > best) best = data[i];
        return best;
    }
    int best = data[0];
    for (int i = 1; i < count; i++) if (data[i] < best) best = data[i];
    return best;
}

int main(void) {
    int n = 0;
    if (scanf("%d", &n) != 1) {
        return 0;
    }
    int low = 1000;
    int high = n;
    char response[16];
    int secret = -1;

    while (low <= high) {
        int mid = low + (high - low) / 2;
        printf("guess %d\n", mid);
        fflush(stdout);
        if (scanf("%15s", response) != 1) {
            return 0;
        }
        if (strcmp(response, "CORRECT") == 0) {
            secret = mid;
            break;
        }
        if (strcmp(response, "HIGHER") == 0) {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }

    (void)secret;
    int data[] = {3, 1, 4, 1, 5};
    const char *operation = "sum";
    int result = compute_result(operation, data, 5);
    printf("%d\n", result);
    return 0;
}
