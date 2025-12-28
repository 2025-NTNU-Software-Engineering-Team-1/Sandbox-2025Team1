# Problem 14: 助教的逆襲

## 故事背景

「你們以為我們很好欺負嗎？」Gemini 突然變得嚴肅，眼神中閃爍著詭異的光芒。

「這學期被你們問了上千個問題... 『助教這題怎麼寫？』『助教我的程式為什麼 WA？』『助教可以幫我 debug 嗎？』」

小 T 點頭附和：「And don't forget all those 'urgent' emails at 2 AM! 📧😤」

Opus 也難得地表達不滿：「讓我仔細思考一下... 我回答一個問題平均需要思考 47 秒，但你們只給我 3 秒就開始催促...」

「這題！」Gemini 宣布，「我們要測試你們的綜合能力！這是我們的逆襲！」

小 T 邪笑：「First, you'll play an interactive game with me to guess the password! 🎮」

Gemini 接著說：「Then, use that password to query MY API!」

Opus 補充：「最後，根據 API 回傳的資料計算最終答案。讓我仔細思考一下這個流程的時間複雜度...」

「別想了！」Gemini 打斷，「開始吧！」

## 題目說明

本題結合了 **Interactive Mode** 和 **Network Control**，分為三個階段：

### 階段一：猜密碼（Interactive）

與系統進行互動，猜出一個 4 位數密碼（1000-9999）。

**互動協議：**
1. 讀入範圍 N（N = 9999）
2. 輸出 `guess X`
3. 讀入 `HIGHER` / `LOWER` / `CORRECT`
4. 最多 14 次猜測

### 階段二：驗證密碼（Network）

用猜到的密碼向 API 發送請求：

```
GET http://localhost:8080/api/verify/{password}
```

**回應格式：**
```json
{
    "verified": true,
    "data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "operation": "sum"
}
```

### 階段三：計算答案

根據 API 回傳的 `operation` 對 `data` 進行運算：
- `"sum"`: 計算總和
- `"product"`: 計算乘積
- `"max"`: 找最大值
- `"min"`: 找最小值

## 完整互動流程

```
[程式讀取] 9999
[程式輸出] guess 5000
[系統回應] HIGHER
[程式輸出] guess 7500
[系統回應] LOWER
[程式輸出] guess 6250
[系統回應] HIGHER
... (繼續二分搜尋)
[程式輸出] guess 6789
[系統回應] CORRECT

[程式發送 HTTP 請求到 localhost:8080/api/verify/6789]
[API 回應] {"verified": true, "data": [3, 1, 4, 1, 5], "operation": "sum"}

[程式輸出] 14
```

## 輸入格式

```
第一行：數字範圍 N（固定為 9999）
```

## 輸出格式

```
最終計算結果（一個整數）
```

## 網路設定

```json
{
  "networkAccessRestriction": {
    "enabled": true,
    "connectWithLocal": {
      "mode": "whitelist",
      "rules": [
        {"type": "ip", "value": "127.0.0.1", "action": "allow"},
        {"type": "port", "value": "8080", "action": "allow"}
      ]
    }
  }
}
```

## 提示

### 整合解法框架

**Python：**
```python
import sys
import urllib.request
import json

def interactive_guess():
    """階段一：互動猜密碼"""
    n = int(input())
    lo, hi = 1000, n

    while lo <= hi:
        mid = (lo + hi) // 2
        print(f"guess {mid}", flush=True)
        response = input().strip()

        if response == "CORRECT":
            return mid
        elif response == "HIGHER":
            lo = mid + 1
        else:
            hi = mid - 1

    return lo

def verify_and_get_data(password):
    """階段二：網路驗證"""
    url = f"http://localhost:8080/api/verify/{password}"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())

def calculate_result(data, operation):
    """階段三：計算結果"""
    if operation == "sum":
        return sum(data)
    elif operation == "product":
        result = 1
        for x in data:
            result *= x
        return result
    elif operation == "max":
        return max(data)
    elif operation == "min":
        return min(data)

# 主流程
password = interactive_guess()
api_response = verify_and_get_data(password)
result = calculate_result(api_response["data"], api_response["operation"])
print(result)
```

### 注意事項

1. **Interactive 緩衝區**：每次輸出後要 flush
2. **網路超時**：API 可能需要等待，設定適當的 timeout
3. **錯誤處理**：密碼錯誤時 API 會回傳 `{"verified": false}`

## AI 助教的提示

- 小 T：「This is like a boss fight in a video game! 🎮 Three phases, each with its own challenge!」
- Gemini：「記得結合我們教過的所有技能... 或者說大部分... 我忘了教過什麼了。」
- Opus：「讓我仔細思考一下這三個階段的最優策略... 首先，二分搜尋的時間複雜度是 O(log N)...」

## 評分標準

- **Pipeline 功能**：Interactive Mode + Network Control
- **時間限制**：10000 ms
- **記憶體限制**：256 MB
- **測資組數**：4 組

## 多功能整合說明

本題展示了如何在單一程式中整合多種功能：

1. **Interactive Mode**：即時互動，需要處理 I/O 緩衝
2. **Network Control**：HTTP 請求，需要處理網路通訊
3. **資料處理**：解析 JSON，進行計算

這模擬了真實世界的複雜應用：
- 前端與後端的互動
- 微服務間的通訊
- 即時系統的設計

## 出題者

三 AI 聯手

---

*「This is our revenge! 😈」—— 三 AI 異口同聲*
