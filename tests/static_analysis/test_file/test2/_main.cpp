
// #include <iostream>      // std::cout, std::endl
// #include <vector>        // std::vector (觸發 disallow_headers: vector)
// #include <string>        // std::string (觸發 disallow_headers: string)
// #include <stack>         // std::stack
// #include <queue>         // std::queue, std::priority_queue
// #include <algorithm>     // sort, stable_sort, partial_sort, nth_element, for_each
// #include <numeric>       // iota, accumulate
// #include <memory>        // std::unique_ptr, std::make_unique
// #include <cstring>       // std::memset, std::memcpy, std::memmove
// #include <cstdio>        // std::printf
// #include <cstdlib>       // std::malloc, std::free (觸發 disallow_functions: malloc/free)
// #include <cassert>       // assert
// #include <unordered_map>
// #include <unordered_set>
// #include <functional>

// static long long fact (int n) {
//     if (n <= 1) return 1;
//     return n * fact (n - 1);
// }


// static int mutual_a (int n);
// static int mutual_b (int n);

// static int mutual_a (int n) {
//     if (n <= 0) return 0;
//     return mutual_b (n - 1);
// }

// static int mutual_b (int n) {
//     if (n <= 0) return 1;
//     return mutual_a (n - 1);
// }



// static void sort (std::vector<int> &a) {
//     const std::size_t n = a.size ();
//     for (std::size_t i = 0; i + 1 < n; ++i) {
//         std::size_t j = 0;
//         while (j + 1 < n - i) {
//             if (a [j] > a [j + 1]) std::swap (a [j] , a [j + 1]);
//             ++j;
//         }
//     }
// }

// static void insertion_sort (std::vector<int> &a) {
//     for (std::size_t i = 1; i < a.size (); ++i) {
//         int key = a [i];
//         std::size_t j = i;
//         while (j > 0 && a [j - 1] > key) {
//             --j;
//         }
//         a [j] = key;
//     }
// }

// static void memory_block_demo () {
//     const std::size_t N = 32;
//     unsigned char *buf = static_cast<unsigned char *>(std::malloc (N)); // malloc
//     assert (buf);
//     std::memset (buf , 0xAA , N);                   // memset

//     unsigned char tmp [32];
//     std::memcpy (tmp , buf , N);                    // memcpy

//     std::memmove (buf + 4 , buf , 16);              // memmove

//     std::free (buf);                               // free
// }


// int main () {

//     std::vector<int> v = {7,1,5,9,3,8,2,6,4,0};
//     v.push_back (10);
//     v.pop_back ();
//     sort (v);
//     insertion_sort (v);

//     std::vector<int> a (10);
//     std::iota (a.begin () , a.end () , 0);     // 0..9
//     std::reverse (a.begin () , a.end ());     // 9..0

//     std::sort (a.begin () , a.end ());        // disallow_functions: ["sort"] 
//     std::stable_sort (a.begin () , a.end ()); // disallow_functions: ["stable_sort"] 
//     std::partial_sort (a.begin () , a.begin () + 5 , a.end ()); // partial_sort
//     std::nth_element (a.begin () , a.begin () + 3 , a.end ());  // nth_element

//     std::for_each (a.begin () , a.end () , [] (int &x) { x += 1; });

//     // ---- 3) stack / queue / priority_queue 的 push/pop ----
//     std::stack<int> st;
//     st.push (10); st.push (20); st.push (30);
//     st.pop ();

//     std::queue<int> q;
//     q.push (11); q.push (22); q.push (33);
//     q.pop ();

//     std::priority_queue<int> pq;
//     pq.push (3); pq.push (7); pq.push (1);
//     pq.pop ();

//     // ---- 4) range-for（CXX_FOR_RANGE_STMT） ----
//     int sum = 0;
//     for (int x : a) { sum += x; }
//     std::cout << "sum=" << sum << "\n";

//     const int n = 8;
//     long long f = fact (n);
//     std::cout << "fact(" << n << ")=" << f << "\n";

//     int m = 5;
//     int r = mutual_a (m);
//     std::cout << "mutual_a(" << m << ")=" << r << "\n";



//     int *raw = new int [16];
//     std::memset (raw , 0 , sizeof (int) * 16);
//     delete [] raw;

//     auto up = std::make_unique<int []> (16);
//     up [0] = 42;

//     std::string s = "Hello";
//     s += ", world";
//     std::cout << s << std::endl;

//     std::printf ("[printf] f=%lld\n" , f);     // printf（在 <cstdio>）
//     memory_block_demo ();                     // malloc/free/mem*

//     // ---- 9) Hash containers & std::hash ----
//     std::unordered_map<std::string , int> um;
//     um.insert ({"alice", 1});
//     um.emplace ("bob" , 2);
//     um.try_emplace ("carol" , 3);
//     auto it = um.find ("alice");
//     if (it != um.end ()) um.erase (it);
//     um.reserve (32);
//     um.rehash (64);

//     std::unordered_set<int> us;
//     us.insert (42);
//     us.emplace (7);
//     bool has42 = (us.count (42) > 0);
//     if (has42) us.erase (42);

//     std::size_t hv1 = std::hash<std::string> {}("hello");
//     const char *cs = "world";
//     std::size_t hv2 = std::hash<const char *> {}(cs);
//     (std::cout << "hv1=" << hv1 << " hv2=" << hv2 << "\n");

//     return 0;
// }

// main.cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <functional>
#include <cstddef>

// ==========================================
// 4. ABA 遞迴 (Ping <-> Pong)
// ==========================================
void pong (int n); // Forward declaration

void ping (int n) {
    if (n > 0) {
        pong (n - 1);
    }
}

void pong (int n) {
    if (n > 0) {
        ping (n - 1); // Cycle here!
    }
}

// ==========================================
// 3. 使用者自定義普通函式 (Should Pass)
// ==========================================
void my_sort (std::vector<int> &v) {
    // 簡單冒泡排序
    for (int32_t i = 0; i < v.size (); ++i) {
        for (int32_t j = 0; j < v.size () - 1; ++j) {
            if (v [j] > v [j + 1]) {
                int temp = v [j];
                v [j] = v [j + 1];
                v [j + 1] = temp;
            }
        }
    }
}

// ==========================================
// 2. 使用者自定義 Class (Should Pass)
// ==========================================
class MySorter {
public:
    void sort () {
        std::cout << "MySorter::sort called" << std::endl;
    }

    void dangerous_method () {
        std::vector<int> v = {1, 2, 3};
        // 6. 類別內偷用官方 sort (Should Fail)
        std::sort (v.begin () , v.end ());
    }
};

int main () {
    std::vector<int> v = {3, 1, 4, 1, 5};

    // 1. 官方 Sort (Should Fail)
    // 這是 libstdc++ 的 std::sort，定義在 header 裡
    std::sort (v.begin () , v.end ());

    // 官方 Vector 方法 (Should Fail if "push_back" is disallowed)
    v.push_back (99);

    // 3. 使用者普通函式 (Should Pass)
    my_sort (v);

    // 2. 使用者 Class 方法 (Should Pass)
    MySorter s;
    s.sort (); // 呼叫的是定義在 main.cpp 的 MySorter::sort

    // 4. 觸發遞迴 (Should Detect Recursive)
    ping (5);

    // 5. 函數指標測試 (Function Pointer)
    // 直接指標
    void (*func_ptr)(std::vector<int>&) = my_sort;
    func_ptr (v); // 這是指向 user defined，應該 Pass

    // 6. 類別內偷用 (Should Fail)
    // s.dangerous_method 本身 Pass，但裡面呼叫了 std::sort -> Fail
    s.dangerous_method ();

    return 0;
}