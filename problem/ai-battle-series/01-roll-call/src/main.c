#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char name[32];
    int priority;
    int order;
} Record;

static int cmp_by_name(const void *a, const void *b) {
    const Record *ra = (const Record *)a;
    const Record *rb = (const Record *)b;
    int cmp = strcmp(ra->name, rb->name);
    if (cmp != 0) {
        return cmp;
    }
    if (ra->priority != rb->priority) {
        return (ra->priority < rb->priority) ? 1 : -1;
    }
    if (ra->order != rb->order) {
        return (ra->order > rb->order) ? 1 : -1;
    }
    return 0;
}

static int cmp_by_priority(const void *a, const void *b) {
    const Record *ra = (const Record *)a;
    const Record *rb = (const Record *)b;
    if (ra->priority != rb->priority) {
        return (ra->priority < rb->priority) ? 1 : -1;
    }
    int cmp = strcmp(ra->name, rb->name);
    if (cmp != 0) {
        return cmp;
    }
    if (ra->order != rb->order) {
        return (ra->order > rb->order) ? 1 : -1;
    }
    return 0;
}

int main(void) {
    int n = 0;
    if (scanf("%d", &n) != 1) {
        return 0;
    }
    if (n <= 0) {
        return 0;
    }

    Record *records = (Record *)malloc(sizeof(Record) * (size_t)n);
    if (!records) {
        return 0;
    }

    for (int i = 0; i < n; i++) {
        scanf("%31s %d", records[i].name, &records[i].priority);
        records[i].order = i;
    }

    qsort(records, n, sizeof(Record), cmp_by_name);

    Record *unique = (Record *)malloc(sizeof(Record) * (size_t)n);
    if (!unique) {
        free(records);
        return 0;
    }

    int count = 0;
    for (int i = 0; i < n; i++) {
        if (i == 0 || strcmp(records[i].name, records[i - 1].name) != 0) {
            unique[count++] = records[i];
        }
    }

    qsort(unique, count, sizeof(Record), cmp_by_priority);

    for (int i = 0; i < count; i++) {
        printf("%s\n", unique[i].name);
    }

    free(records);
    free(unique);
    return 0;
}
