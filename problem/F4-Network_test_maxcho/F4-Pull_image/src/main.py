import socket
import sys


def test_service():
    # 預設值
    host = "localhost"
    port = 80

    # 1. 從 stdin 讀取目標
    try:
        line = sys.stdin.read().strip()
        if line:
            parts = line.split()
            if len(parts) >= 2:
                host = parts[0]
                port = int(parts[1])
    except Exception:
        pass

    print(f"debug: Target is {host}:{port}")

    try:
        # 2. 建立連線
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)

        print("debug: Connecting...")
        sock.connect((host, port))
        print("debug: Connected!")

        # 3. 根據 Port 決定協定
        if port == 6379:
            # --- Redis 測試流程 ---
            print("debug: Detected Redis port (6379), sending AUTH...")
            password = "noj_secret_pass"
            command = f"AUTH {password}\r\n"
            sock.sendall(command.encode())

            response = sock.recv(1024).decode()
            print(f"debug: Raw response: {repr(response)}")

            if response.startswith("+OK"):
                print("good")
            else:
                print("fail (debug: Redis AUTH failed)")

        elif port == 8080:
            # --- Busybox HTTP 測試流程 ---
            print("debug: Detected HTTP port (8080), sending GET...")
            request = f"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n"
            sock.sendall(request.encode())

            print("debug: Receiving response...")
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk: break
                response += chunk

            response_str = response.decode('utf-8', errors='replace')
            print(f"debug: Response length: {len(response_str)}")
            # 印出前 100 字元供除錯
            print(f"debug: Content snippet: {repr(response_str[:100])}...")

            if "verify_env_args_success" in response_str:
                print("good")
            else:
                print("fail (debug: HTTP secret keyword not found)")

        else:
            print(f"fail (debug: Unknown port {port}, no protocol handler)")

        sock.close()
    except Exception as e:
        print(f"fail (debug: Exception {e})")


if __name__ == "__main__":
    test_service()
