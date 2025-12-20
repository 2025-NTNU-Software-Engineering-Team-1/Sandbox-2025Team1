# Network Test 測試資料總結

## ✅ 已完成項目

### 1. Local Service 說明
- ✅ 創建了 `LOCAL_SERVICE_EXPLANATION.md` 說明文件
- ✅ 解釋了 Local Service 的概念、工作流程和使用場景

### 2. Local Service 結構調整
- ✅ 在 `local_service/` 目錄中添加了 `Dockerfile`
- ✅ `Dockerfile` 基於 `python:3.11-slim`，包含必要的工具和依賴
- ✅ 重新打包了 `local_service.zip`，包含所有必要檔案：
  - `Dockerfile` ⭐ (新增)
  - `start.sh`
  - `server.py`
  - `requirements.txt`

### 3. 測試資料打包
- ✅ 已將 `testdata/` 目錄打包成 `testdata.zip`
- ✅ 包含 3 組測試案例（0000, 0001, 0002）

### 4. 前端測試指南
- ✅ 創建了 `FRONTEND_TEST_GUIDE.md`，說明如何透過前端介面測試

## 📦 準備好的檔案

### 可直接上傳的檔案

1. **testdata.zip** (887 bytes)
   - 位置：`Sandbox/problem/network-test/testdata.zip`
   - 用途：題目測試資料
   - 內容：3 組測試案例的輸入和預期輸出

2. **local_service.zip** (2,222 bytes)
   - 位置：`Sandbox/problem/network-test/local_service.zip`
   - 用途：Local Service 服務檔案
   - 內容：
     - `Dockerfile` - Docker 映像定義
     - `start.sh` - 啟動腳本
     - `server.py` - HTTP 伺服器
     - `requirements.txt` - Python 依賴

## 📋 Local Service 是什麼？

**Local Service** 是一個在評測期間運行的本地服務，供學生程式連接和互動。

### 主要特點：
1. **教師上傳**：教師將服務打包成 zip 上傳
2. **自動啟動**：Sandbox 在評測開始時自動啟動服務
3. **學生連線**：學生程式可以連接到服務（通常是 `localhost:8080`）
4. **自動關閉**：評測結束後自動關閉服務

### 為什麼需要 Dockerfile？
- 定義服務的執行環境（Python、Node.js、資料庫等）
- 確保所有依賴都已安裝
- 讓服務可以在隔離的容器中運行
- Sandbox 會使用 Dockerfile 構建服務容器

## 🚀 前端測試步驟

### 快速開始

1. **上傳測試資料**
   - 在題目編輯頁面，上傳 `testdata.zip`

2. **上傳 Local Service**
   - 在 Local Service 區塊，上傳 `local_service.zip`

3. **配置網路設定**
   - 啟用 `networkAccessRestriction`
   - 設定 `connectWithLocal` 規則：
     - IP: `127.0.0.1` (allow)
     - Port: `8080` (allow)

4. **設定測試案例**
   - 案例數量：3
   - 記憶體限制：65536 KB
   - 時間限制：2000 ms

5. **測試提交**
   - 使用 `student/cpp/main.cpp` 或 `student/py/main.py` 測試

詳細步驟請參考 `FRONTEND_TEST_GUIDE.md`

## 📁 檔案結構

```
network-test/
├── testdata.zip                    # ✅ 已打包，可直接上傳
├── local_service.zip               # ✅ 已打包（包含 Dockerfile），可直接上傳
├── config.json                     # 題目配置參考
├── description.md                  # 題目描述
├── README.md                       # 詳細說明
├── SETUP.md                        # 設置指南
├── FRONTEND_TEST_GUIDE.md          # 前端測試指南 ⭐
├── LOCAL_SERVICE_EXPLANATION.md    # Local Service 說明 ⭐
├── SUMMARY.md                      # 本文件
├── env-cpp/                        # C++ 執行環境
│   └── Dockerfile
├── env-py/                         # Python 執行環境
│   └── Dockerfile
├── student/                        # 學生代碼範例
│   ├── cpp/main.cpp
│   └── py/main.py
├── testdata/                       # 原始測試資料（已打包）
│   ├── in/
│   └── out/
└── local_service/                  # Local Service 原始檔案（已打包）
    ├── Dockerfile                  # ⭐ 新增
    ├── start.sh
    ├── server.py
    └── requirements.txt
```

## ✅ 檢查清單

- [x] Local Service 包含 Dockerfile
- [x] testdata.zip 已打包
- [x] local_service.zip 已打包（包含 Dockerfile）
- [x] 所有說明文件已更新
- [x] 前端測試指南已創建

## 📝 注意事項

1. **Dockerfile 是必要的**：`local_service.zip` 必須包含 `Dockerfile`
2. **執行權限**：`start.sh` 需要有執行權限（打包時會保留）
3. **網路配置**：確保 `connectWithLocal` 規則正確設定
4. **測試驗證**：建議先用學生代碼範例測試

## 🔗 相關文檔

- [Local Service 說明](./LOCAL_SERVICE_EXPLANATION.md) - 詳細解釋 Local Service
- [前端測試指南](./FRONTEND_TEST_GUIDE.md) - 如何透過前端測試
- [設置指南](./SETUP.md) - 完整設置步驟
- [README](./README.md) - 完整說明文件
