# Network Test 測試資料說明

本目錄包含網路功能測試題目的完整測試資料。

## 目錄結構

```
network-test/
├── env-cpp/              # C++ 執行環境 Dockerfile
│   └── Dockerfile
├── env-py/               # Python 執行環境 Dockerfile
│   └── Dockerfile
├── student/              # 學生代碼範例
│   ├── cpp/
│   │   └── main.cpp      # C++ 範例（使用 libcurl）
│   └── py/
│       └── main.py       # Python 範例（使用 urllib）
├── testdata/             # 測試資料
│   ├── in/               # 輸入檔案
│   │   ├── 0000.in
│   │   ├── 0001.in
│   │   └── 0002.in
│   └── out/              # 預期輸出檔案
│       ├── 0000.out
│       ├── 0001.out
│       └── 0002.out
├── local_service/        # Local Service 檔案（需打包成 zip）
│   ├── Dockerfile        # 服務的 Docker 映像定義（必要）
│   ├── start.sh          # 啟動腳本（必須有執行權限）
│   ├── server.py         # HTTP 伺服器
│   └── requirements.txt  # Python 依賴
├── config.json           # 題目配置文件
├── description.md        # 題目描述
└── README.md            # 本文件
```

## 題目說明

這是一個 HTTP 客戶端練習題，要求學生撰寫程式連接到本地 HTTP 伺服器（運行在 `localhost:8080`），發送 HTTP GET 請求並輸出回應內容。

## 網路配置

題目配置了 `networkAccessRestriction`，允許連接到：
- IP: `127.0.0.1` (localhost)
- Port: `8080`

## Local Service

`local_service/` 目錄包含一個簡單的 HTTP 伺服器，提供 `/api/data/{param}` 端點。

### 打包 Local Service

在部署前，需要將 `local_service/` 目錄打包成 zip 檔案：

```bash
cd local_service
chmod +x start.sh
cd ..
zip -r local_service.zip local_service/
```

**注意**：`local_service.zip` 必須包含 `Dockerfile`，Sandbox 會使用它來構建服務容器。

### Local Service 功能

- 監聽 `localhost:8080`
- 提供 `/api/data/{param}` 端點
- 提供 `/health` 健康檢查端點
- 返回 JSON 格式的資料

## 測試資料說明

### 測試案例 1 (0000.in/0000.out)
- 輸入：3 個用戶 ID
- 測試基本 HTTP GET 請求功能

### 測試案例 2 (0001.in/0001.out)
- 輸入：1 個用戶 ID
- 測試單一請求處理

### 測試案例 3 (0002.in/0002.out)
- 輸入：5 個用戶 ID
- 測試多個連續請求處理

## 學生代碼要求

### C++ 版本
- 使用 `libcurl` 進行 HTTP 請求
- 編譯時需要連結 `-lcurl`

### Python 版本
- 使用 `urllib` 或 `requests` 進行 HTTP 請求
- Python 3.11+

## 部署步驟

1. **構建 Docker 映像**
   ```bash
   docker build -t noj-network-cpp -f env-cpp/Dockerfile .
   docker build -t noj-network-py -f env-py/Dockerfile .
   ```

2. **打包測試資料**
   ```bash
   cd testdata
   zip -r ../testdata.zip .
   cd ..
   ```

3. **打包 Local Service**
   ```bash
   cd local_service
   chmod +x start.sh
   zip -r ../local_service.zip .
   cd ..
   ```

4. **上傳到 MinIO**
   - 上傳 `testdata.zip` 到 `problems/network-test/testdata.zip`
   - 上傳 `local_service.zip` 到 `problems/network-test/local_service.zip`

5. **在後端創建題目**
   - 使用 `config.json` 中的配置創建題目
   - 確保 `networkAccessRestriction` 設定正確

## 注意事項

1. **start.sh 執行權限**：確保 `start.sh` 有執行權限（`chmod +x start.sh`）
2. **服務啟動時間**：Local Service 需要時間啟動，建議在 `start.sh` 中加入等待邏輯
3. **Port 衝突**：確保 Port 8080 未被佔用
4. **錯誤處理**：學生代碼應包含適當的錯誤處理

## 測試建議

1. 先在本地測試 Local Service：
   ```bash
   cd local_service
   chmod +x start.sh
   ./start.sh
   # 在另一個終端測試
   curl http://localhost:8080/api/data/user1
   ```

2. 測試學生代碼：
   ```bash
   # C++
   g++ -o main main.cpp -lcurl
   ./main < testdata/in/0000.in

   # Python
   python3 main.py < testdata/in/0000.in
   ```

## 相關文檔

- [Network Control Guide](../../../Docs and Ref/Guides/03_NETWORK_CONTROL.md)
- [Config Reference](../../../Docs and Ref/Guides/CONFIG_REFERENCE.md)
