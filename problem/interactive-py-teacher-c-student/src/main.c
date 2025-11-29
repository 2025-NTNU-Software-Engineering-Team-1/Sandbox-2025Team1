#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int q;
    if (scanf("%d", &q) != 1) {
        return 0;
    }
    long long running = 0;
    for (int i = 1; i <= q; ++i) {
        long long val;
        if (scanf("%lld", &val) != 1) {
            return 0;
        }
        running += val * i;
        printf("%lld\n", running);
        fflush(stdout);
    }
    return 0;
}
