#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int id;
    int score;
} Entry;

static int cmp_entry(const void *a, const void *b) {
    const Entry *ea = (const Entry *)a;
    const Entry *eb = (const Entry *)b;
    if (ea->score != eb->score) {
        return ea->score - eb->score;
    }
    return ea->id - eb->id;
}

int main(void) {
    Entry data[] = {
        {5, 70},
        {8, 75},
        {1, 80},
        {6, 80},
        {2, 85},
        {3, 90},
    };
    int n = (int)(sizeof(data) / sizeof(data[0]));
    qsort(data, n, sizeof(Entry), cmp_entry);
    printf("%d
", n);
    for (int i = 0; i < n; i++) {
        printf("%d
", data[i].id);
    }
    return 0;
}
