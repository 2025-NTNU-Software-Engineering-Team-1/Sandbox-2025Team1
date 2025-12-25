# Fail Code - 違反 SA (使用 for)
n = int(input())
result = 0
for i in range(1, n + 1):  # 違反: for
    result += i
print(result)
