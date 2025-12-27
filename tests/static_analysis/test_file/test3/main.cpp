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

// ====== 遞迴：階乘（用來觸發 recursive 檢查） ======
static long long fact (int n) {
    if (n <= 1) return 1;
    return n * fact (n - 1); // <- 遞迴呼叫位置
}

// ====== 兩種手刻排序：for / while 都會出現 ======
static void sort (std::vector<int> &a) {
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

    // ---- 1) vector: push_back / pop_back + 自訂排序（for/while） ----
    std::vector<int> v = {7,1,5,9,3,8,2,6,4,0};
    v.push_back (10);           // push_back
    v.pop_back ();              // pop_back
    sort (v);
    insertion_sort (v);

    // ---- 2) 標準演算法：sort / stable_sort / partial_sort / nth_element ----
    std::vector<int> a (10);
    std::iota (a.begin () , a.end () , 0);     // 0..9
    std::reverse (a.begin () , a.end ());     // 9..0

    // std::sort (a.begin () , a.end ());        // sort
    std::stable_sort (a.begin () , a.end ()); // stable_sort（此例排序鍵相同效果等同，但可測呼叫）
    std::partial_sort (a.begin () , a.begin () + 5 , a.end ()); // 部分排序
    std::nth_element (a.begin () , a.begin () + 3 , a.end ());  // 第3順位元素就定位

    // for_each + lambda（產生一個 CALL_EXPR 給分析器看）
    std::for_each (a.begin () , a.end () , [] (int &x) { x += 1; });

    // ---- 3) 容器：stack / queue / priority_queue 的 push/pop ----
    std::stack<int> st;
    st.push (10); st.push (20); st.push (30);
    st.pop (); // pop

    std::queue<int> q;
    q.push (11); q.push (22); q.push (33);
    q.pop ();   // pop

    std::priority_queue<int> pq;
    pq.push (3); pq.push (7); pq.push (1);
    pq.pop ();  // pop

    // ---- 4) range-for（CXX_FOR_RANGE_STMT） ----
    int sum = 0;
    for (int x : a) { sum += x; }  // range-for 檢查點
    std::cout << "sum=" << sum << "\n";

    // ---- 5) 遞迴呼叫 ----
    const int n = 8;
    long long f = fact (n); // 呼叫遞迴函式
    std::cout << "fact(" << n << ")=" << f << "\n";

    // ---- 6) new[]/delete[] 與 unique_ptr ----
    int *raw = new int [16];                  // new[]
    std::memset (raw , 0 , sizeof (int) * 16);
    delete [] raw;                            // delete[]

    auto up = std::make_unique<int []> (16);   // unique_ptr + 配列
    up [0] = 42;

    // ---- 7) std::string 基本操作（觸發 <string> header 檢查）----
    std::string s = "Hello";
    s += ", world";
    std::cout << s << std::endl;

    // ---- 8) 為了觸發 disallow_functions: printf/malloc/free（C 樣式）----
    std::printf ("[printf] f=%lld\n" , f);     // printf（在 <cstdio>）
    memory_block_demo ();                     // 內含 malloc/free/mem* 呼叫

    // ---- 9) Hash containers & std::hash ----
    std::unordered_map<std::string , int> um;   // <unordered_map>
    um.insert ({"alice", 1});                   // insert
    um.emplace ("bob" , 2);                      // emplace
    um.try_emplace ("carol" , 3);                // C++17 try_emplace
    auto it = um.find ("alice");                // find
    if (it != um.end ()) um.erase (it);          // erase by iterator
    um.reserve (32);                            // 擴桶以降低 rehash 機率
    um.rehash (64);                             // 強制設定桶數（可能觸發 rehash）

    std::unordered_set<int> us;                // <unordered_set>
    us.insert (42);
    us.emplace (7);
    bool has42 = (us.count (42) > 0);           // count / 存在性查詢
    if (has42) us.erase (42);

    std::size_t hv1 = std::hash<std::string> {}("hello"); // <functional> std::hash 呼叫
    // 注意：下面這行對 const char* 只會雜湊指標，不是字串內容
    const char *cs = "world";
    std::size_t hv2 = std::hash<const char *> {}(cs);
    (std::cout << "hv1=" << hv1 << " hv2=" << hv2 << "\n");

    return 0;
}
