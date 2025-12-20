# Network Test 測試資料設置指南

## 已創建的檔案清單

### 1. 執行環境 Dockerfile
- ✅ `env-cpp/Dockerfile` - C++ 執行環境（基於 gcc:11，包含 libcurl）
- ✅ `env-py/Dockerfile` - Python 執行環境（基於 python:3.11-slim，包含 requests）

### 2. 學生代碼範例
- ✅ `student/cpp/main.cpp` - C++ 範例（使用 libcurl 進行 HTTP 請求）
- ✅ `student/py/main.py` - Python 範例（使用 urllib 進行 HTTP 請求）

### 3. 測試資料
- ✅ `testdata/in/0000.in` - 測試案例 1 輸入（3 個請求）
- ✅ `testdata/out/0000.out` - 測試案例 1 預期輸出
- ✅ `testdata/in/0001.in` - 測試案例 2 輸入（1 個請求）
- ✅ `testdata/out/0001.out` - 測試案例 2 預期輸出
- ✅ `testdata/in/0002.in` - 測試案例 3 輸入（5 個請求）
- ✅ `testdata/out/0002.out` - 測試案例 3 預期輸出

### 4. Local Service
- ✅ `local_service/Dockerfile` - 服務的 Docker 映像定義（必要）
- ✅ `local_service/start.sh` - 服務啟動腳本（需有執行權限）
- ✅ `local_service/server.py` - HTTP 伺服器實作
- ✅ `local_service/requirements.txt` - Python 依賴（目前為空）

### 5. 配置文件
- ✅ `config.json` - 題目配置文件（包含 networkAccessRestriction 設定）
- ✅ `description.md` - 題目描述文件
- ✅ `README.md` - 詳細說明文件

## 下一步操作

### 1. 設置 Local Service 執行權限
```bash
chmod +x local_service/start.sh
```

### 2. 打包測試資料
```bash
cd testdata
zip -r ../testdata.zip .
cd ..
```

### 3. 打包 Local Service
```bash
cd local_service
chmod +x start.sh
zip -r ../local_service.zip .
cd ..
```

**重要**：確保 `local_service.zip` 包含 `Dockerfile`，Sandbox 需要使用它來構建服務容器。

### 4. 構建 Docker 映像（可選，用於本地測試）
```bash
docker build -t noj-network-cpp -f env-cpp/Dockerfile .
docker build -t noj-network-py -f env-py/Dockerfile .
```

### 5. 上傳到 MinIO
- 上傳 `testdata.zip` 到 `problems/network-test/testdata.zip`
- 上傳 `local_service.zip` 到 `problems/network-test/local_service.zip`

### 6. 在後端創建題目
使用 `config.json` 中的配置在後端創建題目，確保：
- `networkAccessRestriction.enabled = true`
- `connectWithLocal` 規則正確設定（允許 127.0.0.1:8080）

## 測試驗證

### 本地測試 Local Service
```bash
cd local_service
chmod +x start.sh
./start.sh
# 在另一個終端測試
curl http://localhost:8080/api/data/user1
curl http://localhost:8080/health
```

### 測試學生代碼（C++）
```bash
cd student/cpp
g++ -o main main.cpp -lcurl
echo -e "2\nuser1\nuser2" | ./main
```

### 測試學生代碼（Python）
```bash
cd student/py
echo -e "2\nuser1\nuser2" | python3 main.py
```

## 配置說明

### networkAccessRestriction 配置
```json
{
  "enabled": true,
  "connectWithLocal": {
    "mode": "whitelist",
    "rules": [
      {"type": "ip", "value": "127.0.0.1", "action": "allow"},
      {"type": "port", "value": "8080", "action": "allow"}
    ]
  }
}
```

此配置允許學生程式：
- 連接到 `127.0.0.1` (localhost)
- 使用 Port `8080`
- 不允許連接到外部網路（firewallExtranet 規則為空）

## 注意事項

1. **執行權限**：確保 `start.sh` 有執行權限
2. **服務啟動時間**：Local Service 需要時間啟動，`start.sh` 中已包含 2 秒等待
3. **Port 衝突**：確保 Port 8080 未被佔用
4. **錯誤處理**：學生代碼應包含適當的錯誤處理
5. **JSON 格式**：伺服器返回的 JSON 格式需與預期輸出完全一致（包括空格）

## 相關文檔

- [Network Control Guide](../../../Docs and Ref/Guides/03_NETWORK_CONTROL.md)
- [Config Reference](../../../Docs and Ref/Guides/CONFIG_REFERENCE.md)
- [Database Schema](../../../Docs and Ref/Architecture/DatabaseSchema.md)
