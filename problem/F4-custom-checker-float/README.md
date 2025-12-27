# Custom Checker 測試題目:浮點數輸出

## 題目說明

這是一個專門用來測試 Custom Checker 功能的範例題目。

### 題目描述

給定 N 個浮點數,請將它們依序輸出(每個數字一行)。

由於浮點數運算可能存在精度誤差,本題使用 **Custom Checker** 進行判定,允許誤差範圍為 **ε = 1e-6**。

### 輸入格式

- 第一行:一個整數 N (1 ≤ N ≤ 100)
- 第二行:N 個浮點數(空格分隔)

### 輸出格式

- N 行,每行一個浮點數

### 範例

#### 輸入範例 1
```
2
3.14159265 2.71828183
```

#### 輸出範例 1
```
3.14159265
2.71828183
```

#### 輸入範例 2
```
3
1.41421356 1.73205081 2.23606798
```

#### 輸出範例 2
```
1.41421356
1.73205081
2.23606798
```

### 測資說明

本題共分為 3 個 Subtask:

| Subtask | 分數 | N 範圍 | Time Limit | Memory Limit | Case 數量 |
|---------|------|--------|------------|--------------|----------|
| 1 | 30 分 | N ≤ 3 | 1000ms | 256KB | 2 |
| 2 | 40 分 | N ≤ 5 | 1000ms | 256KB | 2 |
| 3 | 30 分 | N ≤ 10 | 2000ms | 512KB | 2 |

### Custom Checker 邏輯

本題使用 Python 編寫的 Custom Checker (`custom_checker.py`),主要檢查項目:

1. **輸出行數檢查:**確認輸出行數等於 N
2. **數值格式檢查:**確認每行都是有效的浮點數
3. **數值比較:**允許誤差 ε = 1e-6
   - 若 |student_output - expected| ≤ 1e-6,視為正確
   - 否則視為錯誤並回報具體差異

### Custom Checker 測試重點

本題目可測試以下 Custom Checker 功能:

- ✅ 正確讀取三個參數檔案 (input.in, student.out, answer.out)
- ✅ 正確解析檔案內容
- ✅ 錯誤處理 (空輸出、格式錯誤、數量不符)
- ✅ 浮點數誤差容忍
- ✅ 詳細的錯誤訊息回報
- ✅ 正確輸出 STATUS 和 MESSAGE

### 使用方式

1. **建立題目:**在 Backend 建立題目並設定 `pipeline.customChecker = true`
2. **上傳 Checker:**上傳 `custom_checker.py` 檔案
3. **上傳測資:**上傳包含 6 個 test case 的測資 zip (0000.in/out ~ 0201.in/out)
4. **測試提交:**使用 `src/solution.cpp` 作為參考解答進行測試

### 預期結果

- 使用參考解答提交應獲得 **100 分**(所有 test case AC)
- Checker 訊息範例:`All 2 numbers match within tolerance (ε = 1.00e-06)`

### 檔案清單

```
custom-checker-float-test/
├── meta.json              # 題目配置
├── custom_checker.py      # Custom Checker 腳本
├── README.md             # 本說明文件
├── src/
│   └── solution.cpp      # 參考解答
└── testcase/
    ├── 0000.in           # Subtask 1, Case 1 輸入
    ├── 0000.out          # Subtask 1, Case 1 預期輸出
    ├── 0001.in           # Subtask 1, Case 2 輸入
    ├── 0001.out          # Subtask 1, Case 2 預期輸出
    ├── 0100.in           # Subtask 2, Case 1 輸入
    ├── 0100.out          # Subtask 2, Case 1 預期輸出
    ├── 0101.in           # Subtask 2, Case 2 輸入
    ├── 0101.out          # Subtask 2, Case 2 預期輸出
    ├── 0200.in           # Subtask 3, Case 1 輸入
    ├── 0200.out          # Subtask 3, Case 1 預期輸出
    ├── 0201.in           # Subtask 3, Case 2 輸入
    └── 0201.out          # Subtask 3, Case 2 預期輸出
```

---

**製作日期:** 2025-12-01  
**用途:** Custom Checker 功能測試與驗證
