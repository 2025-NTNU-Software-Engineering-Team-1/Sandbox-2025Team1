# 前端測試指南

本指南說明如何透過前端介面測試 network-test 題目。

## 準備檔案

### 1. 測試資料 (testdata.zip)
✅ **已準備完成**
- 位置：`Sandbox/problem/network-test/testdata.zip`
- 內容：包含 3 組測試案例（0000, 0001, 0002）的輸入和預期輸出

### 2. Local Service (local_service.zip)
✅ **已準備完成**
- 位置：`Sandbox/problem/network-test/local_service.zip`
- 內容：
  - `Dockerfile` - 服務的 Docker 映像定義
  - `start.sh` - 啟動腳本
  - `server.py` - HTTP 伺服器
  - `requirements.txt` - Python 依賴

## 前端上傳步驟

### 1. 創建題目
1. 登入前端系統
2. 進入「題目管理」或「創建題目」頁面
3. 填寫基本資訊：
   - **題目名稱**：HTTP 客戶端練習題
   - **題目描述**：參考 `description.md` 的內容
   - **標籤**：network, http, api

### 2. 上傳測試資料
1. 在「測試資料」區塊，點擊「上傳」
2. 選擇 `testdata.zip`
3. 確認上傳成功

### 3. 上傳 Local Service
1. 在「Local Service」或「網路服務」區塊，點擊「上傳」
2. 選擇 `local_service.zip`
3. 確認上傳成功

### 4. 配置網路設定
在「網路存取限制」或「Network Access Restriction」區塊：

1. **啟用網路存取限制**：勾選 `enabled`
2. **Local Service 連線設定**：
   - 模式：`whitelist`
   - 規則：
     - IP: `127.0.0.1` (allow)
     - Port: `8080` (allow)
3. **外部網路設定**：
   - 模式：`whitelist`
   - 規則：留空（不允許外部網路）

### 5. 設定測試案例
在「測試案例」區塊：
- **案例數量**：3
- **總分**：100
- **記憶體限制**：65536 KB (64 MB)
- **時間限制**：2000 ms (2 秒)

### 6. 設定語言
在「允許的語言」區塊：
- ✅ C++ (cpp17)
- ✅ Python (python3)

### 7. 儲存題目
點擊「儲存」或「發布」按鈕

## 測試提交

### 1. 使用學生代碼範例測試
1. 進入題目頁面
2. 選擇語言（C++ 或 Python）
3. 複製 `student/cpp/main.cpp` 或 `student/py/main.py` 的內容
4. 提交程式碼
5. 查看評測結果

### 2. 預期結果
- **測試案例 1 (0000)**：應獲得 AC（Accepted）
- **測試案例 2 (0001)**：應獲得 AC（Accepted）
- **測試案例 3 (0002)**：應獲得 AC（Accepted）

## 疑難排解

### Local Service 啟動失敗
- 檢查 `local_service.zip` 是否包含 `Dockerfile`
- 確認 `start.sh` 有執行權限
- 查看 Sandbox 日誌中的錯誤訊息

### 學生程式無法連線
- 確認網路存取限制已正確設定
- 檢查 `connectWithLocal` 規則是否包含 `127.0.0.1:8080`
- 確認 Local Service 已成功啟動（檢查 Sandbox 日誌）

### 測試資料不匹配
- 確認 `testdata.zip` 結構正確（包含 `in/` 和 `out/` 目錄）
- 檢查輸出格式是否完全一致（包括空格和換行）

## 檔案位置總結

```
network-test/
├── testdata.zip          # ✅ 已準備，可直接上傳
├── local_service.zip      # ✅ 已準備，可直接上傳
├── config.json            # 參考配置（前端會自動生成）
├── description.md         # 題目描述內容
└── student/               # 學生代碼範例（用於測試提交）
    ├── cpp/main.cpp
    └── py/main.py
```

## 相關文檔

- [Local Service 說明](./LOCAL_SERVICE_EXPLANATION.md)
- [設置指南](./SETUP.md)
- [README](./README.md)
