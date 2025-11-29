#include <stdio.h>

static long long square(long long n) {
    return n * n;
}

int main(void) {
    long long n;
    if (scanf("%lld", &n) != 1) {
        return 0;
    }
    printf("%lld\n", square(n));
    return 0;
}
