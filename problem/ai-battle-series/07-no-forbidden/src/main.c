#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int value;
    int digit_sum;
} Item;

static int calc_digit_sum(int v) {
    int n = v < 0 ? -v : v;
    int sum = 0;
    if (n == 0) {
        return 0;
    }
    while (n > 0) {
        sum += n % 10;
        n /= 10;
    }
    return sum;
}

static int less_item(const Item *a, const Item *b) {
    if (a->digit_sum != b->digit_sum) {
        return a->digit_sum < b->digit_sum;
    }
    return a->value < b->value;
}

static void merge_step(Item *arr, Item *tmp, int left, int mid, int right) {
    int i = left;
    int j = mid;
    int k = left;
    while (i < mid && j < right) {
        if (less_item(&arr[i], &arr[j])) {
            tmp[k++] = arr[i++];
        } else {
            tmp[k++] = arr[j++];
        }
    }
    while (i < mid) {
        tmp[k++] = arr[i++];
    }
    while (j < right) {
        tmp[k++] = arr[j++];
    }
    for (i = left; i < right; i++) {
        arr[i] = tmp[i];
    }
}

static void merge_order(Item *arr, Item *tmp, int left, int right) {
    if (right - left <= 1) {
        return;
    }
    int mid = left + (right - left) / 2;
    merge_order(arr, tmp, left, mid);
    merge_order(arr, tmp, mid, right);
    merge_step(arr, tmp, left, mid, right);
}

int main(void) {
    int n = 0;
    if (scanf("%d", &n) != 1) {
        return 0;
    }
    if (n <= 0) {
        return 0;
    }

    Item *arr = (Item *)malloc(sizeof(Item) * (size_t)n);
    Item *tmp = (Item *)malloc(sizeof(Item) * (size_t)n);
    if (!arr || !tmp) {
        free(arr);
        free(tmp);
        return 0;
    }

    for (int i = 0; i < n; i++) {
        int v = 0;
        scanf("%d", &v);
        arr[i].value = v;
        arr[i].digit_sum = calc_digit_sum(v);
    }

    merge_order(arr, tmp, 0, n);

    for (int i = 0; i < n; i++) {
        if (i) {
            printf(" ");
        }
        printf("%d", arr[i].value);
    }
    printf("
");

    free(arr);
    free(tmp);
    return 0;
}
