import socket
import sys


def test_service():
    host = "localhost"
    port = 80

    # 1. 從 stdin 讀取目標 (相容所有 .in 格式)
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

        print(f"debug: Connecting to {host}:{port}...")
        sock.connect((host, port))
        print("debug: Connected!")

        # 3. 根據 Port 分流處理
        if port == 6379:
            # --- Redis 測試流程 (來自 src) ---
            print("debug: Detected Redis port (6379), sending AUTH...")
            password = "noj_secret_pass"
            command = f"AUTH {password}\r\n"
            sock.sendall(command.encode())

            response = sock.recv(1024).decode()
            print(f"debug: Redis raw response: {repr(response)}")

            if response.startswith("+OK"):
                print("good (Redis Auth Success)")
            else:
                print("fail (Redis Auth Failed)")

        elif port == 8000 or port == 8080:
            # --- HTTP 測試流程 (整合了 src 和 src_1) ---
            # 8000 -> env-python
            # 8080 -> secret-server (src) 或 env-cpp (src_1)

            print(f"debug: Detected HTTP port ({port}), sending GET...")
            request = f"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n"
            sock.sendall(request.encode())

            print("debug: Receiving response...")
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk

            response_str = response.decode("utf-8", errors="replace")
            print(f"debug: Response length: {len(response_str)}")
            print(f"debug: Content snippet: {repr(response_str[:100])}...")

            # 驗證邏輯整合
            is_good = False

            # Case 1: src_1 (env-python)
            if port == 8000:
                if "Hello from Server Container!" in response_str:
                    print("debug: Matched Python env signature")
                    is_good = True
                else:
                    print("fail (Python env signature not found)")

            # Case 2: src (secret-server) OR src_1 (env-cpp)
            elif port == 8080:
                if "verify_env_args_success" in response_str:
                    print("debug: Matched Secret Server signature (src)")
                    is_good = True
                elif "Hello from C++ File!" in response_str:
                    print("debug: Matched C++ env signature (src_1)")
                    is_good = True
                else:
                    print("fail (No known signature found for port 8080)")

            if is_good:
                print("good")
            else:
                print("fail (Content verification failed)")

        else:
            print(f"fail (debug: Unknown port {port}, no protocol handler)")

        sock.close()
    except Exception as e:
        print(f"fail (debug: Exception {e})")


if __name__ == "__main__":
    test_service()
