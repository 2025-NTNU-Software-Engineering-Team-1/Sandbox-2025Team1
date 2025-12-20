#!/usr/bin/env python3
"""
簡單的HTTP伺服器，提供API端點供學生程式測試
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# 模擬資料庫
DATA_STORE = {
    "user1": {
        "id": "user1",
        "name": "Alice",
        "score": 95
    },
    "user2": {
        "id": "user2",
        "name": "Bob",
        "score": 87
    },
    "user3": {
        "id": "user3",
        "name": "Charlie",
        "score": 92
    },
    "test123": {
        "id": "test123",
        "name": "Test User",
        "score": 100
    },
    "student1": {
        "id": "student1",
        "name": "David",
        "score": 88
    },
    "student2": {
        "id": "student2",
        "name": "Eve",
        "score": 91
    },
    "student3": {
        "id": "student3",
        "name": "Frank",
        "score": 85
    },
    "student4": {
        "id": "student4",
        "name": "Grace",
        "score": 94
    },
    "student5": {
        "id": "student5",
        "name": "Henry",
        "score": 89
    },
}


class APIHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        """處理GET請求"""
        if self.path == "/health":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
            return

        # 解析路徑 /api/data/{param}
        if self.path.startswith("/api/data/"):
            param = self.path.replace("/api/data/", "").strip()

            if param in DATA_STORE:
                data = DATA_STORE[param]
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            else:
                # 如果找不到，返回預設資料
                default_data = {"id": param, "name": "Unknown", "score": 0}
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(default_data).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')

    def log_message(self, format, *args):
        """覆寫日誌方法，減少輸出"""
        pass


if __name__ == '__main__':
    server = HTTPServer(('localhost', 8080), APIHandler)
    print('Server started on port 8080', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped')
        server.shutdown()
