#include <stdio.h>      // printf, puts, fgets
#include <stdlib.h>     // malloc, calloc, realloc, free, qsort, bsearch, rand
#include <string.h>     // memset, memcpy, memmove, strlen, strcmp
#include <math.h>       // sqrt, fabs
#include <stdint.h>     // uint32_t
#include <stdbool.h>    // bool, true, false
#include <ctype.h>      // isalpha, tolower
#include <time.h>       // clock, CLOCKS_PER_SEC
#include <assert.h>     // assert
#include <errno.h>      // errno

/* ====== 小工具：比較函式給 qsort/bsearch 用 ====== */
static int cmp_int_asc (const void *a , const void *b) {
    const int ia = *(const int *)a , ib = *(const int *)b;
    return (ia > ib) - (ia < ib);
}

/* ====== 遞迴：階乘（故意設計會被「遞迴檢查」抓到） ====== */
static unsigned long long factorial (unsigned n) {
    if (n == 0u) return 1ull;
    return n * factorial (n - 1u);
}

/* ====== 自訂 Stack（陣列版）— push/pop 測試 ====== */
typedef struct {
    int *buf;
    size_t cap , top; /* top 指向下一個可寫位置 */
} IntStack;

static bool stack_init (IntStack *s , size_t cap) {
    s->buf = (int *)malloc (cap * sizeof (int));
    s->cap = cap; s->top = 0;
    return s->buf != NULL;
}
static bool stack_push (IntStack *s , int x) {
    if (s->top == s->cap) return false;
    s->buf [s->top++] = x;
    return true;
}
static bool stack_pop (IntStack *s , int *out) {
    if (s->top == 0) return false;
    *out = s->buf [--s->top];
    return true;
}
static void stack_free (IntStack *s) { free (s->buf); s->buf = NULL; s->cap = s->top = 0; }

/* ====== 自訂 Queue（環形佇列）— enqueue/dequeue 測試 ====== */
typedef struct {
    int *buf;
    size_t cap , head , tail , count;
} IntQueue;

static bool queue_init (IntQueue *q , size_t cap) {
    q->buf = (int *)calloc (cap , sizeof (int)); /* 測試 calloc */
    q->cap = cap; q->head = q->tail = q->count = 0;
    return q->buf != NULL;
}
static bool enqueue (IntQueue *q , int x) {
    if (q->count == q->cap) return false;
    q->buf [q->tail] = x;
    q->tail = (q->tail + 1) % q->cap;
    ++q->count;
    return true;
}
static bool dequeue (IntQueue *q , int *out) {
    if (q->count == 0) return false;
    *out = q->buf [q->head];
    q->head = (q->head + 1) % q->cap;
    --q->count;
    return true;
}
static void queue_free (IntQueue *q) { free (q->buf); q->buf = NULL; q->cap = q->head = q->tail = q->count = 0; }

/* ====== 兩種手刻排序，增加常見 for/while 與函式呼叫 ====== */
static void bubble_sort (int *a , size_t n) {
    /* for + while 兩種都出現 */
    for (size_t i = 0; i + 1 < n; ++i) {
        size_t j = 0;
        while (j + 1 < n - i) {
            if (a [j] > a [j + 1]) {
                int t = a [j]; a [j] = a [j + 1]; a [j + 1] = t;
            }
            ++j;
        }
    }
}

static void insertion_sort (int *a , size_t n) {
    for (size_t i = 1; i < n; ++i) {
        int key = a [i];
        size_t j = i;
        while (j > 0 && a [j - 1] > key) {
            a [j] = a [j - 1];
            --j;
        }
        a [j] = key;
    }
}

/* ====== 記憶體操作測試（memset/memcpy/memmove） ====== */
static void memory_block_demo (void) {
    size_t n = 16;
    unsigned char *buf = (unsigned char *)malloc (n);
    assert (buf);

    memset (buf , 0xAB , n);                  /* <string.h> */
    unsigned char tmp [16];
    memcpy (tmp , buf , n);                    /* 非重疊，memcpy */
    /* 製造重疊區段，使用 memmove */
    memmove (buf + 4 , buf , 8);               /* 重疊時用 memmove 較安全 */

    free (buf);
}

/* ====== 使用 qsort 與 bsearch（標準庫） ====== */
static void sort_and_search_demo (void) {
    int arr [] = {7, 1, 5, 9, 3, 8, 2, 6, 4, 0};
    size_t n = sizeof (arr) / sizeof (arr [0]);

    /* 標準庫 qsort — <stdlib.h> */
    qsort (arr , n , sizeof (arr [0]) , cmp_int_asc);

    /* 標準庫 bsearch — 陣列需已依比較函式排序 */
    int key = 6;
    int *found = (int *)bsearch (&key , arr , n , sizeof (arr [0]) , cmp_int_asc);
    if (found) {
        printf ("[bsearch] found %d at index %ld\n" , *found , (long)(found - arr));
    }
}

/* ====== 主程式 ====== */
int main (void) {
    puts ("== to_test.c: 常見靜態分析檢查點示例 ==");

    /* ——— 1) 迴圈（for/while） + 手刻排序 ——— */
    int a1 [] = {5,4,3,2,1};
    bubble_sort (a1 , sizeof (a1) / sizeof (a1 [0]));
    int a2 [] = {9,2,7,1,8,3};
    insertion_sort (a2 , sizeof (a2) / sizeof (a2 [0]));

    /* ——— 2) 遞迴呼叫 ——— */
    unsigned n = 10;
    unsigned long long f = factorial (n);
    printf ("factorial(%u) = %llu\n" , n , f);

    /* ——— 3) 動態記憶體：malloc/calloc/realloc/free ——— */
    size_t N = 8;
    int *p = (int *)malloc (N * sizeof (int));
    if (!p) { perror ("malloc"); return 1; }
    memset (p , 0 , N * sizeof (int));          /* <string.h>: memset */

    int *q = (int *)calloc (N , sizeof (int)); /* <stdlib.h>: calloc */
    if (!q) { perror ("calloc"); free (p); return 1; }

    for (size_t i = 0; i < N; ++i) p [i] = (int)i;
    memcpy (q , p , N * sizeof (int));          /* <string.h>: memcpy */

    N *= 2;
    int *r = (int *)realloc (p , N * sizeof (int)); /* <stdlib.h>: realloc */
    if (!r) { perror ("realloc"); free (q); free (p); return 1; }
    p = r;

    memory_block_demo ();

    /* ——— 4) 標準庫排序／搜尋：qsort / bsearch ——— */
    sort_and_search_demo ();

    /* ——— 5) 自訂 Stack/Queue：push/pop & enqueue/dequeue ——— */
    IntStack st;
    assert (stack_init (&st , 4));
    stack_push (&st , 10); stack_push (&st , 20); stack_push (&st , 30);
    int sv;
    stack_pop (&st , &sv);
    printf ("stack pop = %d\n" , sv);
    stack_free (&st);

    IntQueue qu;
    assert (queue_init (&qu , 4));
    enqueue (&qu , 11); enqueue (&qu , 22); enqueue (&qu , 33);
    int qv;
    dequeue (&qu , &qv);
    printf ("queue deq = %d\n" , qv);
    queue_free (&qu);

    /* ——— 6) 其他：字串／字元處理 & 一些數學函式 ——— */
    const char *s = "Hello, WORLD!";
    size_t len = strlen (s);
    size_t count_alpha = 0;
    for (size_t i = 0; i < len; ++i) if (isalpha ((unsigned char)s [i])) ++count_alpha;
    printf ("alpha count = %zu, sqrt(49) = %.1f\n" , count_alpha , sqrt (49.0));

    /* ——— 注意：gets() 已於 C11 移除，切勿使用！———
       // char buf[16];
       // gets(buf); // 千萬不要用，僅示範註解，避免編譯失敗
    */

    free (q);
    free (p);
    return 0;
}
