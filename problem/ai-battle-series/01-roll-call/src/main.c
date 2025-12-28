#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char name[21];
    int priority;
    int index;
} Record;

static int cmp_by_name(const void *a, const void *b) {
    const Record *ra = (const Record *)a;
    const Record *rb = (const Record *)b;
    int name_cmp = strcmp(ra->name, rb->name);
    if (name_cmp != 0) {
        return name_cmp;
    }
    if (ra->priority != rb->priority) {
        return (rb->priority - ra->priority);
    }
    return (ra->index - rb->index);
}

static int cmp_by_priority_name(const void *a, const void *b) {
    const Record *ra = (const Record *)a;
    const Record *rb = (const Record *)b;
    if (ra->priority != rb->priority) {
        return (rb->priority - ra->priority);
    }
    return strcmp(ra->name, rb->name);
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
        if (scanf("%20s %d", records[i].name, &records[i].priority) != 2) {
            records[i].name[0] = '\0';
            records[i].priority = 0;
        }
        records[i].index = i;
    }

    qsort(records, (size_t)n, sizeof(Record), cmp_by_name);

    Record *unique = (Record *)malloc(sizeof(Record) * (size_t)n);
    if (!unique) {
        free(records);
        return 0;
    }

    int unique_count = 0;
    for (int i = 0; i < n; i++) {
        if (i == 0 || strcmp(records[i].name, records[i - 1].name) != 0) {
            unique[unique_count++] = records[i];
        }
    }

    qsort(unique, (size_t)unique_count, sizeof(Record), cmp_by_priority_name);

    for (int i = 0; i < unique_count; i++) {
        printf("%s\n", unique[i].name);
    }

    free(records);
    free(unique);
    return 0;
}
