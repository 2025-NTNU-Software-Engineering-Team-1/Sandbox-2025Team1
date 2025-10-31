# to_test.py  → 請存成 main.py 以符合分析器的檔名規則

# 觸發 disallow_imports
import os
from sys import version_info as _py_ver  # node.module == "sys" → 也會被紀錄

# 一些無害的頂層呼叫，讓 function_calls 也有內容（非必要）
print("Start Python static-analysis test")  # 會被 facts["function_calls"] 記到


def fact(n: int) -> int:
    """簡單遞迴：會被判定為 recursive（名稱直接相同的自呼叫）"""
    if n <= 1:
        return 1
    return n * fact(n - 1)  # ← 這行應該會出現在 facts["recursive_calls"]


def loops_demo():
    # for 迴圈（觸發 disallow_syntax: for）
    total = 0
    for i in range(3):  # ← facts["for_loops"] 會記這一行
        total += i

    # while 迴圈（觸發 disallow_syntax: while）
    k = 0
    while k < 3:  # ← facts["while_loops"] 會記這一行
        k += 1

    return total + k


def import_usage_demo():
    # 用到 os / sys（只是避免未使用警告；靜態分析重點在 import）
    _ = os.getenv("PATH")  # Attribute 呼叫不一定會被記入 function_calls（OK）
    # sys.* 是從 ImportFrom 來的別名，這裡只讀值即可
    _ = (_py_ver.major, _py_ver.minor)
    return _


def main():
    print("loops_demo =", loops_demo())
    print("fact(5) =", fact(5))
    import_usage_demo()


if __name__ == "__main__":
    main()
