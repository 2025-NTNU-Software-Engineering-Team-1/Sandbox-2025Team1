#include <stdio.h>

int main(void) {
    FILE *fp = fopen("testcase.in", "r");
    if (!fp) {
        return 1;
    }
    long long n = 0;
    if (fscanf(fp, "%lld", &n) != 1) {
        fclose(fp);
        return 1;
    }
    fclose(fp);

    // Send the value to the student process.
    printf("%lld\n", n);
    fflush(stdout);

    long long received = 0;
    if (scanf("%lld", &received) != 1) {
        return 1;
    }

    FILE *out = fopen("Check_Result", "w");
    if (!out) {
        return 1;
    }
    if (received == n * n) {
        fprintf(out, "STATUS: AC\nMESSAGE: ok\n");
    } else {
        fprintf(out,
                "STATUS: WA\nMESSAGE: expected %lld got %lld\n",
                n * n,
                received);
    }
    fclose(out);
    return 0;
}
