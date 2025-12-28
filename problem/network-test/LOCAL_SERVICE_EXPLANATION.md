# Local Service 說明

## 什麼是 Local Service？

Local Service 是一個在評測期間運行的本地服務，供學生程式連接和互動。它允許教師創建自訂的服務程式（如 HTTP Server、Database、Message Queue 等），在評測容器中啟動，讓學生程式可以與之通信。

## 工作流程

1. **教師上傳**：教師將 Local Service 打包成 `local_service.zip` 上傳到題目
2. **評測開始**：當學生提交程式進行評測時，Sandbox 會：
   - 下載 `local_service.zip`
   - 解壓縮
   - 根據 Dockerfile 構建服務容器（如果需要）
   - 啟動服務（執行 `start.sh`）
3. **學生程式執行**：學生程式可以連接到 Local Service（通常是 `localhost:8080`）
4. **評測結束**：Sandbox 會自動關閉 Local Service

## Local Service 結構

根據目前的設計，`local_service.zip` 應包含：

```
local_service.zip
├── Dockerfile          # 服務的 Docker 映像定義（必要）
├── start.sh            # 啟動腳本（必要，需有執行權限）
├── server.py            # 服務程式（範例）
├── requirements.txt     # Python 依賴（可選）
└── 其他必要檔案...
```

## Dockerfile 的作用

Dockerfile 用於構建 Local Service 的執行環境，確保：
- 服務有正確的運行環境（Python、Node.js、資料庫等）
- 所有依賴都已安裝
- 服務可以在隔離的容器中運行

## 與學生程式的關係

- **學生程式**：運行在評測容器中，可以連接到 Local Service
- **Local Service**：運行在獨立的容器中（或同一容器內），提供 API/服務
- **網路配置**：透過 `networkAccessRestriction.connectWithLocal` 控制連線權限

## 使用場景

1. **HTTP API 練習**：提供 RESTful API 供學生程式調用
2. **資料庫操作**：提供資料庫服務供學生程式查詢
3. **Socket 通訊**：提供 TCP/UDP 服務供學生程式連接
4. **訊息佇列**：提供 MQ 服務供學生程式使用
