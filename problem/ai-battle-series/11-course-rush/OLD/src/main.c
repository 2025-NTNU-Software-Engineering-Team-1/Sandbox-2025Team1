#include <stdio.h>
#include <string.h>
#include <stdlib.h>

typedef struct {
    const char *name;
    const char *professor;
    const char *title;
    int capacity;
    int enrolled;
    const char *dept;
} Course;

typedef struct {
    const Course *course;
    double popularity;
} Result;

static int cmp_result(const void *a, const void *b) {
    const Result *ra = (const Result *)a;
    const Result *rb = (const Result *)b;
    if (ra->popularity < rb->popularity) return 1;
    if (ra->popularity > rb->popularity) return -1;
    return strcmp(ra->course->name, rb->course->name);
}

int main(void) {
    char dept[32];
    int threshold = 0;
    if (scanf("%31s", dept) != 1) {
        return 0;
    }
    if (scanf("%d", &threshold) != 1) {
        return 0;
    }

    Course courses[] = {
        {"進階機器學習", "陳教授", "教授", 30, 28, "CS"},
        {"資料結構", "王教授", "副教授", 50, 45, "CS"},
        {"計算機組織", "李教授", "助理教授", 40, 12, "CS"},
        {"微積分", "張教授", "教授", 60, 50, "MATH"},
    };

    Result results[8];
    int result_count = 0;
    int total = (int)(sizeof(courses) / sizeof(courses[0]));

    for (int i = 0; i < total; i++) {
        if (strcmp(courses[i].dept, dept) != 0) {
            continue;
        }
        double popularity = (double)courses[i].enrolled * 100.0 / (double)courses[i].capacity;
        if (popularity + 1e-9 < threshold) {
            continue;
        }
        results[result_count].course = &courses[i];
        results[result_count].popularity = popularity;
        result_count++;
    }

    if (result_count == 0) {
        printf("No matching courses\n");
        return 0;
    }

    qsort(results, result_count, sizeof(Result), cmp_result);

    for (int i = 0; i < result_count; i++) {
        const Course *c = results[i].course;
        printf("%s by %s (%s) - %.1f%% (%d/%d)\n",
               c->name,
               c->professor,
               c->title,
               results[i].popularity,
               c->enrolled,
               c->capacity);
    }
    return 0;
}
