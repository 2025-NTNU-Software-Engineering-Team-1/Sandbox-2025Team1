import socket
import sys


def log(msg):
    """Print debug log message"""
    print(f"[LOG] {msg}")


def test_redis(host, port):
    """Test Redis sidecar with AUTH command"""
    log(f"Mode: Redis test")
    log(f"Target: {host}:{port}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)

        log("Connecting to Redis...")
        sock.connect((host, port))
        log("Connected!")

        password = "noj_secret_pass"
        command = f"AUTH {password}\r\n"
        log(f"Sending AUTH command...")
        sock.sendall(command.encode())

        response = sock.recv(1024).decode()
        log(f"Raw response: {repr(response)}")

        if response.startswith("+OK"):
            log("Redis AUTH succeeded!")
            print("good")
        else:
            log("Redis AUTH failed!")
            print("fail")

        sock.close()
    except Exception as e:
        log(f"Exception: {e}")
        print("fail")


def test_http_sidecar(host, port):
    """Test HTTP secret-server sidecar (verify_env_args_success)"""
    log(f"Mode: HTTP sidecar test")
    log(f"Target: {host}:{port}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)

        log("Connecting...")
        sock.connect((host, port))
        log("Connected!")

        request = f"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n"
        log("Sending HTTP GET request...")
        sock.sendall(request.encode())

        log("Receiving response...")
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk

        response_str = response.decode('utf-8', errors='replace')
        log(f"Response length: {len(response_str)}")
        log(f"Content snippet: {repr(response_str[:100])}...")

        if "verify_env_args_success" in response_str:
            log("Found secret keyword!")
            print("good")
        else:
            log("Secret keyword not found!")
            print("fail")

        sock.close()
    except Exception as e:
        log(f"Exception: {e}")
        print("fail")


def test_custom_python(host, port):
    """Test custom Python environment (Hello from Server Container!)"""
    log(f"Mode: Custom Python env test")
    log(f"Target: {host}:{port}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)

        log("Connecting...")
        sock.connect((host, port))
        log("Connected!")

        request = f"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n"
        log("Sending HTTP GET request...")
        sock.sendall(request.encode())

        log("Receiving response...")
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk

        response_str = response.decode('utf-8', errors='replace')
        log(f"Response length: {len(response_str)}")
        log(f"Content snippet: {repr(response_str[:100])}...")

        if "Hello from Server Container!" in response_str:
            log("Matched Python env signature!")
            print("good")
        else:
            log("Python env signature not found!")
            print("fail")

        sock.close()
    except Exception as e:
        log(f"Exception: {e}")
        print("fail")


def test_custom_cpp(host, port):
    """Test custom C++ environment (Hello from C++ File!)"""
    log(f"Mode: Custom C++ env test")
    log(f"Target: {host}:{port}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)

        log("Connecting...")
        sock.connect((host, port))
        log("Connected!")

        request = f"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n"
        log("Sending HTTP GET request...")
        sock.sendall(request.encode())

        log("Receiving response...")
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk

        response_str = response.decode('utf-8', errors='replace')
        log(f"Response length: {len(response_str)}")
        log(f"Content snippet: {repr(response_str[:100])}...")

        if "Hello from C++ File!" in response_str:
            log("Matched C++ env signature!")
            print("good")
        else:
            log("C++ env signature not found!")
            print("fail")

        sock.close()
    except Exception as e:
        log(f"Exception: {e}")
        print("fail")


def test_external(host, port):
    """Test external network connectivity (IP or hostname)"""
    log(f"Mode: External network test")
    log(f"Target: {host}:{port}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)

        log("Resolving hostname...")
        log(f"Attempting connection to {host}:{port}...")

        result = sock.connect_ex((host, port))

        if result == 0:
            log("Connection succeeded!")
            print("good")
        else:
            log(f"Connection failed with error code: {result}")
            print("fail")

        sock.close()
    except Exception as e:
        log(f"Exception: {e}")
        print("fail")


def main():
    # Read input: <type> <host> <port>
    try:
        line = sys.stdin.read().strip()
        if not line:
            log("No input provided!")
            print("fail")
            return

        parts = line.split()
        if len(parts) < 3:
            log(f"Invalid input format: {line}")
            print("fail")
            return

        test_type = parts[0]
        host = parts[1]
        port = int(parts[2])

        log(f"Input parsed: type={test_type}, host={host}, port={port}")

    except Exception as e:
        log(f"Failed to parse input: {e}")
        print("fail")
        return

    # Dispatch to appropriate test function
    if test_type == "redis":
        test_redis(host, port)
    elif test_type == "http":
        test_http_sidecar(host, port)
    elif test_type == "custom_python":
        test_custom_python(host, port)
    elif test_type == "custom_cpp":
        test_custom_cpp(host, port)
    elif test_type == "external":
        test_external(host, port)
    else:
        log(f"Unknown test type: {test_type}")
        print("fail")


if __name__ == "__main__":
    main()
