// to_test.cpp — C++ 版本「常見靜態分析檢查點」示例

#include <iostream>      // std::cout, std::endl
#include <vector>        // std::vector (觸發 disallow_headers: vector)
#include <string>        // std::string (觸發 disallow_headers: string)
#include <stack>         // std::stack
#include <queue>         // std::queue, std::priority_queue
#include <algorithm>     // sort, stable_sort, partial_sort, nth_element, for_each
#include <numeric>       // iota, accumulate
#include <memory>        // std::unique_ptr, std::make_unique
#include <cstring>       // std::memset, std::memcpy, std::memmove
#include <cstdio>        // std::printf (觸發 disallow_functions: printf)
#include <cstdlib>       // std::malloc, std::free (觸發 disallow_functions: malloc/free)
#include <cassert>       // assert
#include <unordered_map>
#include <unordered_set>
#include <functional>

// ====== 遞迴 1：階乘（直接遞迴） ======
static long long fact (int n) {
    if (n <= 1) return 1;
    return n * fact (n - 1); // <- 觸發「直接遞迴」檢查
}

// ====== 遞迴 2：交互遞迴 (Mutual Recursion) ======
// 宣告
static int mutual_a (int n);
static int mutual_b (int n);

static int mutual_a (int n) {
    if (n <= 0) return 0;
    return mutual_b (n - 1); // <- 呼叫 B
}

static int mutual_b (int n) {
    if (n <= 0) return 1;
    return mutual_a (n - 1); // <- 呼叫 A (應觸發「交互遞迴」)
}


// ====== 兩種手刻排序 (自訂函式，不應被禁) ======
static void sort (std::vector<int> &a) { // 自訂一個也叫 sort 的函式
    const std::size_t n = a.size ();
    for (std::size_t i = 0; i + 1 < n; ++i) {           // for 檢查點
        std::size_t j = 0;
        while (j + 1 < n - i) {                         // while 檢查點
            if (a [j] > a [j + 1]) std::swap (a [j] , a [j + 1]);
            ++j;
        }
    }
}

static void insertion_sort (std::vector<int> &a) {
    for (std::size_t i = 1; i < a.size (); ++i) {        // for 檢查點
        int key = a [i];
        std::size_t j = i;
        while (j > 0 && a [j - 1] > key) {               // while 檢查點
            a [j] = a [j - 1];
            --j;
        }
        a [j] = key;
    }
}

// ====== 記憶體操作：memset/memcpy/memmove ======
static void memory_block_demo () {
    const std::size_t N = 32;
    unsigned char *buf = static_cast<unsigned char *>(std::malloc (N)); // malloc
    assert (buf);
    std::memset (buf , 0xAA , N);                   // memset

    unsigned char tmp [32];
    std::memcpy (tmp , buf , N);                    // memcpy（非重疊）

    std::memmove (buf + 4 , buf , 16);              // memmove（重疊）

    std::free (buf);                               // free
}


int main () {
    std::cout << "== C++ 綜合檢查示例 ==\n";

    // ---- 1) vector: push_back / pop_back + 自訂排序 (不應被抓) ----
    std::vector<int> v = {7,1,5,9,3,8,2,6,4,0};
    v.push_back (10);
    v.pop_back ();
    sort (v); // 呼叫自訂的 sort
    insertion_sort (v);

    // ---- 2) 標準演算法 (應被抓) ----
    std::vector<int> a (10);
    std::iota (a.begin () , a.end () , 0);     // 0..9
    std::reverse (a.begin () , a.end ());     // 9..0

    std::sort (a.begin () , a.end ());        // 應被 disallow_functions: ["sort"] 抓到
    std::stable_sort (a.begin () , a.end ()); // 應被 disallow_functions: ["stable_sort"] 抓到
    std::partial_sort (a.begin () , a.begin () + 5 , a.end ()); // partial_sort
    std::nth_element (a.begin () , a.begin () + 3 , a.end ());  // nth_element

    std::for_each (a.begin () , a.end () , [] (int &x) { x += 1; });

    // ---- 3) 容器：stack / queue / priority_queue 的 push/pop ----
    std::stack<int> st;
    st.push (10); st.push (20); st.push (30);
    st.pop ();

    std::queue<int> q;
    q.push (11); q.push (22); q.push (33);
    q.pop ();

    std::priority_queue<int> pq;
    pq.push (3); pq.push (7); pq.push (1);
    pq.pop ();

    // ---- 4) range-for（CXX_FOR_RANGE_STMT） ----
    int sum = 0;
    for (int x : a) { sum += x; }
    std::cout << "sum=" << sum << "\n";

    // ---- 5) 遞迴呼叫 ----
    const int n = 8;
    long long f = fact (n); // 直接遞迴
    std::cout << "fact(" << n << ")=" << f << "\n";

    int m = 5;
    int r = mutual_a (m); // 交互遞迴
    std::cout << "mutual_a(" << m << ")=" << r << "\n";


    // ---- 6) new[]/delete[] 與 unique_ptr ----
    int *raw = new int [16];
    std::memset (raw , 0 , sizeof (int) * 16);
    delete [] raw;

    auto up = std::make_unique<int []> (16);
    up [0] = 42;

    // ---- 7) std::string 基本操作 (應觸發 <string> header 檢查)----
    std::string s = "Hello";
    s += ", world";
    std::cout << s << std::endl;

    // ---- 8) 為了觸發 disallow_functions: printf/malloc/free (C 樣式)----
    std::printf ("[printf] f=%lld\n" , f);     // printf（在 <cstdio>）
    memory_block_demo ();                     // 內含 malloc/free/mem* 呼叫

    // ---- 9) Hash containers & std::hash ----
    std::unordered_map<std::string , int> um;
    um.insert ({"alice", 1});
    um.emplace ("bob" , 2);
    um.try_emplace ("carol" , 3);
    auto it = um.find ("alice");
    if (it != um.end ()) um.erase (it);
    um.reserve (32);
    um.rehash (64);

    std::unordered_set<int> us;
    us.insert (42);
    us.emplace (7);
    bool has42 = (us.count (42) > 0);
    if (has42) us.erase (42);

    std::size_t hv1 = std::hash<std::string> {}("hello");
    const char *cs = "world";
    std::size_t hv2 = std::hash<const char *> {}(cs);
    (std::cout << "hv1=" << hv1 << " hv2=" << hv2 << "\n");

    return 0;
}