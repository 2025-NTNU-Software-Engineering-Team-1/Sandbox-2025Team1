import sys
import os
import math
import itertools
import functools
import ctypes
import heapq
from collections import deque
from typing import List, Dict, Set


def fact(n: int) -> int:
    if n <= 1:
        return 1
    return n * fact(n - 1)


def mutual_a(n: int) -> int:
    if n <= 0:
        return 0
    return mutual_b(n - 1)


def mutual_b(n: int) -> int:
    if n <= 0:
        return 1
    return mutual_a(n - 1)


def sort(a: List[int]) -> None:
    n = len(a)
    for i in range(n - 1):
        j = 0
        while j + 1 < n - i:
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
            j += 1


def insertion_sort(a: List[int]) -> None:
    for i in range(1, len(a)):
        key = a[i]
        j = i
        while j > 0 and a[j - 1] > key:
            a[j] = a[j - 1]
            j -= 1
        a[j] = key


def memory_block_demo() -> None:
    N = 32
    buf = (ctypes.c_ubyte * N)()
    ctypes.memset(buf, 0xAA, N)
    tmp = (ctypes.c_ubyte * N)()
    ctypes.memmove(tmp, buf, N)
    ctypes.memmove(ctypes.byref(buf, 4), buf, 16)


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

    v = [7, 1, 5, 9, 3, 8, 2, 6, 4, 0]
    v.append(10)
    v.pop()
    sort(v)
    insertion_sort(v)

    a = list(range(10))
    a.reverse()  # 9..0

    a.sort()

    top5 = heapq.nsmallest(5, a)
    nth3 = heapq.nsmallest(4, a)[-1]

    # for_each + lambda
    a = list(map(lambda x: x + 1, a))

    stack = []  # LIFO
    stack.append(10)
    stack.append(20)
    stack.pop()

    q = deque()  # FIFO
    q.append(11)
    q.popleft()

    pq = []
    heapq.heappush(pq, 3)
    heapq.heappop(pq)

    # ---- 4) range-for（for x in a） ----
    s = 0
    for x in a:
        s += x
    print(f"sum={s}")

    n = 8
    f = fact(n)
    print(f"fact({n})={f}")

    m = 5
    r = mutual_a(m)
    print(f"mutual_a({m})={r}")

    memory_block_demo()

    s1 = "Hello"
    s1 += ", world"
    print(s1)

    val = eval("1 + 2")
    exec("x_exec_demo = 123")
    print(f"[eval] {val}, [exec var exists] { 'x_exec_demo' in globals() }")

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

    outer = Outer()
    _ = outer.method()
    _ = outer.inner.method()
    _ = pure_function(2)

    assert isinstance(top5, list)
    try:
        _ = um["not_exist"]  # KeyError
    except KeyError:
        pass

    sys.stdout.write("")


if __name__ == "__main__":
    main()
