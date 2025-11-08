import sys  # I/O
import os  # （可能作為 disallow_imports 測試）
import math  # 一般庫
import itertools  # for_each 類操作
import functools  # reduce 等
import ctypes  # 記憶體操作：memset/memmove
import heapq  # priority_queue
from collections import deque  # queue（FIFO）
from typing import List, Dict, Set


# ====== 遞迴 1：階乘（觸發 direct recursive 檢查）======
def fact(n: int) -> int:
    if n <= 1:
        return 1
    return n * fact(n - 1)  # <- 遞迴呼叫位置


# ====== 遞迴 2：交互遞迴 (Mutual Recursion) ======
def mutual_a(n: int) -> int:
    if n <= 0:
        return 0
    return mutual_b(n - 1)  # <- 呼叫 B


def mutual_b(n: int) -> int:
    if n <= 0:
        return 1
    return mutual_a(n - 1)  # <- 呼叫 A (應觸發「交互遞迴」)


# ====== 兩種手刻排序 (自訂函式，不應被禁) ======
def sort(a: List[int]) -> None:  # 自訂一個也叫 sort 的函式
    n = len(a)
    for i in range(n - 1):  # for 檢查點
        j = 0
        while j + 1 < n - i:  # while 檢查點
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
            j += 1


def insertion_sort(a: List[int]) -> None:
    for i in range(1, len(a)):  # for 檢查點
        key = a[i]
        j = i
        while j > 0 and a[j - 1] > key:  # while 檢查點
            a[j] = a[j - 1]
            j -= 1
        a[j] = key


# ====== 記憶體操作：memset/memmove（以 ctypes 模擬 C 的行為） ======
def memory_block_demo() -> None:
    N = 32
    buf = (ctypes.c_ubyte * N)()  # 等價於 malloc N bytes
    ctypes.memset(buf, 0xAA, N)  # memset
    tmp = (ctypes.c_ubyte * N)()
    ctypes.memmove(tmp, buf, N)  # memcpy（非重疊）
    ctypes.memmove(ctypes.byref(buf, 4), buf, 16)  # memmove（重疊）


# ====== 物件與方法呼叫（測 ast.Attribute 與 ast.Name） ======
def pure_function(x: int) -> int:
    return x + 1


class Inner:

    def method(self) -> str:
        return "inner.method"


class Outer:

    def __init__(self):
        self.inner = Inner()

    def method(self) -> str:
        return "outer.method"


def main() -> None:
    print("== Python 綜合檢查示例 ==")

    # ---- 1) list: append / pop + 自訂排序 (不應被抓) ----
    v = [7, 1, 5, 9, 3, 8, 2, 6, 4, 0]
    v.append(10)  # push_back
    v.pop()  # pop_back
    sort(v)  # 呼叫自訂的 sort
    insertion_sort(v)

    # ---- 2) 內建演算法 (應被抓) ----
    a = list(range(10))
    a.reverse()  # 9..0

    # 應被 disallow_functions: ["sort"] 抓到
    a.sort()

    # partial_sort: 取前 5 小
    top5 = heapq.nsmallest(5, a)
    # nth_element 類似：找第 3 小並使其就位
    nth3 = heapq.nsmallest(4, a)[-1]

    # for_each + lambda
    a = list(map(lambda x: x + 1, a))

    # ---- 3) 容器：stack / queue / priority_queue 的 push/pop ----
    stack = []  # LIFO
    stack.append(10)
    stack.append(20)
    stack.pop()

    q = deque()  # FIFO
    q.append(11)
    q.popleft()

    pq = []  # 最小堆（priority_queue 對位）
    heapq.heappush(pq, 3)
    heapq.heappop(pq)

    # ---- 4) range-for（for x in a） ----
    s = 0
    for x in a:  # range-for 檢查點
        s += x
    print(f"sum={s}")

    # ---- 5) 遞迴呼叫 ----
    n = 8
    f = fact(n)  # 呼叫「直接遞迴」函式
    print(f"fact({n})={f}")

    m = 5
    r = mutual_a(m)  # 呼叫「交互遞迴」函式
    print(f"mutual_a({m})={r}")

    # ---- 6) 記憶體塊操作（ctypes 版本） ----
    memory_block_demo()

    # ---- 7) 字串基本操作 ----
    s1 = "Hello"
    s1 += ", world"
    print(s1)

    # ---- 8) 風險函式 (應被抓) ----
    val = eval("1 + 2")  # 應被 disallow_functions: ["eval"] 抓到
    exec("x_exec_demo = 123")  # 應被 disallow_functions: ["exec"] 抓到
    print(f"[eval] {val}, [exec var exists] { 'x_exec_demo' in globals() }")

    # ---- 9) dict / set 與 hash ----
    um: Dict[str, int] = {}
    um["alice"] = 1
    um.update({"bob": 2})
    um.setdefault("carol", 3)
    it = um.get("alice")
    if it is not None:
        um.pop("alice")

    us: Set[int] = set()
    us.add(42)
    has42 = 42 in us
    if has42:
        us.remove(42)

    hv1 = hash("hello")
    cs = b"world"
    hv2 = hash(cs)
    print(f"hv1={hv1} hv2={hv2}")

    # ---- 10) 物件方法呼叫 ----
    outer = Outer()
    _ = outer.method()
    _ = outer.inner.method()
    _ = pure_function(2)

    # ---- 11) 斷言與例外 ----
    assert isinstance(top5, list)
    try:
        _ = um["not_exist"]  # KeyError
    except KeyError:
        pass

    sys.stdout.write("")


if __name__ == "__main__":
    main()
