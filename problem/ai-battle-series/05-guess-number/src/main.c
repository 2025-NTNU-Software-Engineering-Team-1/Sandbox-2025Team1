#include <stdio.h>
#include <string.h>

int main(void) {
    int n = 0;
    if (scanf("%d", &n) != 1) {
        return 0;
    }
    int low = 1;
    int high = n;
    char response[16];

    while (low <= high) {
        int mid = low + (high - low) / 2;
        printf("guess %d\n", mid);
        fflush(stdout);
        if (scanf("%15s", response) != 1) {
            return 0;
        }
        if (strcmp(response, "CORRECT") == 0) {
            return 0;
        }
        if (strcmp(response, "HIGHER") == 0) {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    return 0;
}
