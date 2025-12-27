#include <stdio.h>

// Simple placeholder for tests: echoes the first integer input.
int main(void) {
    int x = 0;
    if (scanf("%d", &x) != 1) {
        return 0;
    }
    printf("%d\n", x);
    return 0;
}
