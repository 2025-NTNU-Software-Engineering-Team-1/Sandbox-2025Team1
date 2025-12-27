#!/bin/bash

# 安裝依賴（如有）
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

# 啟動服務（背景執行）
python3 server.py &

# 記錄 PID 供 Sandbox 關閉
echo $! > service.pid

# 等待服務啟動
sleep 2

# 檢查服務是否正常運行
if ! curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "Service failed to start" >&2
    exit 1
fi

echo "Service started successfully"
