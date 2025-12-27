import sys  # I/O
import os  # （可能作為 disallow_imports 測試）
import math  # 一般庫
import itertools  # for_each 類操作
import functools  # reduce 等
import ctypes  # 記憶體操作：memset/memmove
import heapq  # priority_queue
from collections import deque  # queue（FIFO）
from typing import List, Dict, Set


# ====== 遞迴：階乘（觸發 recursive 檢查）======
def fact(n: int) -> int:
    if n <= 1:
        return 1
    return n * fact(n - 1)  # <- 遞迴呼叫位置


# ====== 兩種手刻排序：for / while 都會出現 ======
def sort(a: List[int]) -> None:
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

    # memmove（重疊）：從 buf 開頭搬 16 bytes 到 offset 4
    ctypes.memmove(ctypes.byref(buf, 4), buf, 16)
    # （ctypes 無 free，交由 GC 負責）


# ====== 物件與方法呼叫（測 ast.Attribute 與 ast.Name） ======
def pure_function(x: int) -> int:
    return x + 1


class Inner:

    def method(self) -> str:
        return "inner.method"


class Outer:

    def __init__(self):
        self.inner = Inner()  # 形成 obj.inner.method() 鏈結

    def method(self) -> str:
        return "outer.method"

    @property
    def prop(self) -> int:
        return 42


# ====== 互相遞迴（測可能的 mutual recursion 辨識） ======
def mutual_a(n: int) -> int:
    if n <= 0:
        return 0
    return mutual_b(n - 1)


def mutual_b(n: int) -> int:
    if n <= 0:
        return 1
    return mutual_a(n - 1)


def main() -> None:
    print("== Python 綜合檢查示例 ==")

    # ---- 1) list: append / pop + 自訂排序（for/while） ----
    v = [7, 1, 5, 9, 3, 8, 2, 6, 4, 0]
    v.append(10)  # push_back
    v.pop()  # pop_back
    sort(v)
    insertion_sort(v)

    # ---- 2) 內建與「近似對位」演算法：sort / stable / partial / nth ----
    a = list(range(10))
    a.reverse()  # 9..0

    # a.sort()  # sort（Timsort，穩定）
    # a.sort()  # stable_sort 等價再呼叫一次，保留穩定性測點

    # partial_sort: 取前 5 小（heapq.nsmallest 不改原地，作為“部份排序”測點）
    top5 = heapq.nsmallest(5, a)

    # nth_element 類似：找第 3 小並使其就位（以 nsmallest 求第 3 小）
    nth3 = heapq.nsmallest(4, a)[-1]

    # for_each + lambda（產生一個 CALL_EXPR/lambda）
    a = list(map(lambda x: x + 1, a))

    # ---- 3) 容器：stack / queue / priority_queue 的 push/pop ----
    stack = []  # LIFO
    stack.append(10)
    stack.append(20)
    stack.append(30)
    stack.pop()

    q = deque()  # FIFO
    q.append(11)
    q.append(22)
    q.append(33)
    q.popleft()

    pq = []  # 最小堆（priority_queue 對位）
    heapq.heappush(pq, 3)
    heapq.heappush(pq, 7)
    heapq.heappush(pq, 1)
    heapq.heappop(pq)

    # ---- 4) range-for（for x in a） ----
    s = 0
    for x in a:  # range-for 檢查點
        s += x
    print(f"sum={s}")

    # ---- 5) 遞迴呼叫 ----
    n = 8
    f = fact(n)  # 呼叫遞迴函式
    print(f"fact({n})={f}")

    # ---- 6) 記憶體塊操作（ctypes 版本） ----
    memory_block_demo()

    # ---- 7) 字串基本操作 ----
    s1 = "Hello"
    s1 += ", world"
    print(s1)

    # ---- 8) （可選）風險函式：eval/exec（可能列為 disallow_functions） ----
    # 僅作靜態分析測點；運行時為固定常數、沒有外部輸入。
    val = eval("1 + 2")
    exec("x_exec_demo = 123")  # 產生一個全域符號
    print(f"[eval] {val}, [exec var exists] { 'x_exec_demo' in globals() }")

    # ---- 9) dict / set 與 hash ----
    um: Dict[str, int] = {}
    um["alice"] = 1  # insert
    um.update({"bob": 2})  # emplace 對位
    um.setdefault("carol", 3)  # try_emplace 對位
    it = um.get("alice")  # find
    if it is not None:
        um.pop("alice")  # erase

    us: Set[int] = set()
    us.add(42)
    us.add(7)
    has42 = 42 in us  # 存在性查詢
    if has42:
        us.remove(42)

    hv1 = hash("hello")  # Python 對不可變物件以值雜湊（隨機種子防碰撞）
    cs = b"world"
    hv2 = hash(cs)  # bytes 也以內容雜湊
    print(f"hv1={hv1} hv2={hv2}")

    # ---- 10) 物件方法呼叫（ast.Attribute 測點） ----
    outer = Outer()
    _ = outer.method()  # obj.method()
    _ = outer.inner.method()  # obj.inner.method() 鏈結
    _ = pure_function(2)  # ast.Name 呼叫

    # ---- 11) 互相遞迴（mutual recursion） ----
    _ = mutual_a(3)

    # ---- 12) 斷言與例外（一般靜態點） ----
    assert isinstance(top5, list)
    try:
        _ = um["not_exist"]  # KeyError
    except KeyError:
        pass

    # 防止未使用變數被最簡優化器移除（提供更多 AST 節點）
    sys.stdout.write("")


if __name__ == "__main__":
    main()
