import socket
import sys


def test_custom_envs():
    host = "localhost"
    port = 80

    # 1. 讀取輸入
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

        # 3. 發送 HTTP Request
        print("debug: Sending GET request...")
        request = f"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n"
        sock.sendall(request.encode())

        # 4. 接收回應
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

        # 5. 驗證內容 (針對 v1 的兩個服務)
        is_good = False

        if port == 8000:  # env-python
            if "Hello from Server Container!" in response_str:
                print("debug: Matched Python env signature")
                is_good = True
            else:
                print("fail (debug: Python env signature not found)")

        elif port == 8080:  # env-cpp
            if "Hello from C++ File!" in response_str:
                print("debug: Matched C++ env signature")
                is_good = True
            else:
                print("fail (debug: C++ env signature not found)")
        else:
            print(f"fail (debug: Unknown port {port})")

        if is_good:
            print("good")

        sock.close()
    except Exception as e:
        print(f"fail (debug: Exception {e})")


if __name__ == "__main__":
    test_custom_envs()
