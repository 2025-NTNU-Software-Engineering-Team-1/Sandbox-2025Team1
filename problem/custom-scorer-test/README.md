# Custom Scorer 測試題目：部分計分

## 題目說明

這是一個專門用來測試 **Custom Scorer** 功能的範例題目。

### 題目描述

給定 N 個整數，請依序輸出它們（每個數字一行）。

本題使用 **Custom Scorer** 進行計分，支援：
- ✅ **部分計分**：每個 Subtask 根據正確的 case 數量給予部分分數
- ✅ **時間獎勵**：平均執行時間 < 500ms 可獲得 5% 加分
- ✅ **遲交懲罰**：每天扣除 10% 分數（最多扣 30%）

### 輸入格式

- 第一行：一個整數 N (1 ≤ N ≤ 100)
- 第二行：N 個整數（空格分隔）

### 輸出格式

- N 行，每行一個整數

### 範例

#### 輸入範例 1
```
3
42 17 99
```

#### 輸出範例 1
```
42
17
99
```

### 測資說明

本題共分為 3 個 Subtask：

| Subtask | 滿分 | N 範圍 | Time Limit | Memory Limit | Case 數量 |
|---------|------|--------|------------|--------------|----------|
| 1       | 30 分 | N ≤ 3  | 1000ms     | 256KB        | 2        |
| 2       | 40 分 | N ≤ 5  | 1000ms     | 256KB        | 2        |
| 3       | 30 分 | N ≤ 10 | 2000ms     | 512KB        | 2        |

### Custom Scorer 計分邏輯

本題使用 Python 編寫的 Custom Scorer (`score.py`)，計分規則如下：

#### 1. 基礎分數（部分計分）
每個 Subtask 根據正確的 case 數量按比例給分：
```
Subtask 分數 = (正確 case 數 / 總 case 數) × Subtask 滿分
```

例如：Subtask 1 (30分) 有 2 個 case，如果只對 1 個：
```
得分 = (1 / 2) × 30 = 15 分
```

#### 2. 時間獎勵（5% 加分）
若平均執行時間 < 500ms，額外獲得當前總分的 5%：
```
時間獎勵 = 總分 × 0.05
```

#### 3. 遲交懲罰（最多扣 30%）
每遲交一天扣除 10%，最多扣 3 天（30%）：
```
遲交扣分 = 總分 × min(0.3, 遲交天數 × 0.1)
``` 

#### 4. 最終分數
```
最終分數 = max(0, min(100, 基礎分數 + 時間獎勵 - 遲交扣分))
```

### Scorer 輸入格式

Scorer 從 stdin 接收 JSON 格式的資料：
```json
{
  "tasks": [
    [
      {"status": "AC", "execTime": 123, "memoryUsage": 1024},
      {"status": "WA", "execTime": 456, "memoryUsage": 2048}
    ],
    ...
  ],
  "stats": {
    "maxRunTime": 500,
    "avgRunTime": 250,
    "sumRunTime": 750,
    "maxMemory": 2048,
    "avgMemory": 1536,
    "sumMemory": 4608
  },
  "lateSeconds": 0
}
```

### Scorer 輸出格式

Scorer 輸出 JSON 格式的計分結果：
```json
{
  "score": 85,
  "message": "Task 1: 2/2 cases correct → 30 points | Task 2: 1/2 cases correct → 20 points | Time Bonus: avg=250ms < 500ms → +2 points",
  "breakdown": {
    "taskScores": [30, 20, 15],
    "timeBonus": 2,
    "latePenalty": 0,
    "finalScore": 67
  }
}
```

### Custom Scorer 測試重點

本題目可測試以下 Custom Scorer 功能：

- ✅ 正確讀取 JSON 輸入（tasks、stats、lateSeconds）
- ✅ 部分計分邏輯（proportional scoring）
- ✅ 時間獎勵計算
- ✅ 遲交懲罰計算
- ✅ 分數上下限控制（0-100）
- ✅ 詳細的計分細項回報（breakdown）
- ✅ 錯誤處理與 fallback

### 使用方式

1. **建立題目**：在 Backend 建立題目並設定 `pipeline.scoringScript = true`
2. **上傳 Scorer**：上傳 `score.py` 檔案
3. **上傳測資**：上傳包含 6 個 test case 的測資 zip
4. **測試提交**：
   - 使用 `src/solution.cpp`：全對（預期 100 分）
   - 使用 `src/partial_solution.cpp`：部分對（預期 30 分）

### 預期結果

#### 完整解答（solution.cpp）
- 所有 case AC + 平均時間 < 500ms
- 預期分數：**100 分**（30+40+30，上限）

#### 部分解答（partial_solution.cpp）
- Subtask 1 (N≤3): 2/2 AC → 30 分
- Subtask 2 (N=4,5): 0/2 AC → 0 分（輸出數量不足）
- Subtask 3 (N=7,10): 0/2 AC → 0 分（輸出數量不足）
- 預期分數：**30 分**（僅 Task 1 得分）

#### 遲交懲罰示例
- 全對但遲交 2 天
- 基礎分數：100 → 扣除 20% → **80 分**

### 檔案清單

```
custom-scorer-test/
├── meta.json              # 題目配置（啟用 scoringScript）
├── score.py               # Custom Scorer 腳本
├── README.md              # 本說明文件
├── src/
│   ├── solution.cpp       # 完整解答（100 分）
│   └── partial_solution.cpp  # 部分解答（30 分，測試部分計分）
└── testcase/
    ├── 0000.in            # Subtask 1, Case 1 (N=2)
    ├── 0000.out
    ├── 0001.in            # Subtask 1, Case 2 (N=3)
    ├── 0001.out
    ├── 0100.in            # Subtask 2, Case 1 (N=4)
    ├── 0100.out
    ├── 0101.in            # Subtask 2, Case 2 (N=5)
    ├── 0101.out
    ├── 0200.in            # Subtask 3, Case 1 (N=7)
    ├── 0200.out
    ├── 0201.in            # Subtask 3, Case 2 (N=10)
    └── 0201.out
```

---

**製作日期：** 2025-12-02  
**用途：** Custom Scorer 功能測試與驗證  
**參考來源：** 基於 custom-checker-float-test 修改
