#!/usr/bin/env python3
"""
Network Test Client - Tests Docker containers, IP/URL connectivity
Reads test specification from stdin and outputs detailed debug logs
"""
import socket
import sys
import json


def debug_log(msg):
    """Print debug message with prefix"""
    print(f"[DEBUG] {msg}", flush=True)


def check_connection(host, port, timeout=5):
    """Attempt to connect to host:port and return (success, error_msg)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        debug_log(f"Attempting connection to {host}:{port}")

        # Try DNS resolution first if it's a hostname
        if not host.replace('.', '').isdigit():
            try:
                ip = socket.gethostbyname(host)
                debug_log(f"DNS resolved {host} -> {ip}")
                if ip == "0.0.0.0":
                    debug_log("DNS sinkholed to 0.0.0.0")
                    return False, "DNS sinkholed"
            except socket.gaierror as e:
                debug_log(f"DNS resolution failed: {e}")
                return False, f"DNS failed: {e}"

        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            debug_log(f"Connection successful!")
            return True, None
        else:
            debug_log(f"Connection failed with errno={result}")
            return False, f"errno={result}"

    except Exception as e:
        debug_log(f"Connection exception: {e}")
        return False, str(e)


def send_http_request(host,
                      port,
                      path="/",
                      method="GET",
                      body=None,
                      timeout=5):
    """Send HTTP request and return response body"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        debug_log(f"Connecting to {host}:{port}")
        sock.connect((host, port))
        debug_log("Connected!")

        # Build request
        if body:
            request = f"{method} {path} HTTP/1.0\r\nHost: {host}\r\nContent-Length: {len(body)}\r\n\r\n{body}"
        else:
            request = f"{method} {path} HTTP/1.0\r\nHost: {host}\r\n\r\n"

        debug_log(f"Sending {method} request to {path}")
        sock.sendall(request.encode())

        # Receive response
        debug_log("Receiving response...")
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk

        sock.close()

        response_str = response.decode("utf-8", errors="replace")
        debug_log(f"Response length: {len(response_str)} bytes")

        # Extract body (after double CRLF)
        parts = response_str.split("\r\n\r\n", 1)
        if len(parts) > 1:
            body = parts[1]
            debug_log(f"Body: {body[:200]}...")
            return True, body
        else:
            debug_log(f"No body found in response")
            return True, response_str

    except Exception as e:
        debug_log(f"HTTP request failed: {e}")
        return False, str(e)


def test_docker_env(env_name, port, expected_signature):
    """Test connection to a Docker environment container"""
    debug_log(f"Testing Docker env: {env_name}:{port}")
    debug_log(f"Expected signature: {expected_signature}")

    success, body = send_http_request(env_name, port)

    if success and expected_signature in body:
        debug_log(f"Signature matched!")
        return True
    else:
        debug_log(f"Signature NOT found in response")
        return False


def test_ip_connectivity(ip, port, expect_success=True):
    """Test raw IP connectivity"""
    debug_log(
        f"Testing IP: {ip}:{port}, expect={'connect' if expect_success else 'block'}"
    )

    success, error = check_connection(ip, port)

    if success == expect_success:
        debug_log(
            f"Result as expected: {'connected' if success else 'blocked'}")
        return True
    else:
        debug_log(
            f"Unexpected result: {'connected' if success else 'blocked'}")
        return False


def test_url_connectivity(url, port, expect_success=True):
    """Test URL connectivity (includes DNS resolution)"""
    debug_log(
        f"Testing URL: {url}:{port}, expect={'connect' if expect_success else 'block'}"
    )

    success, error = check_connection(url, port)

    if success == expect_success:
        debug_log(
            f"Result as expected: {'connected' if success else 'blocked'}")
        return True
    else:
        debug_log(
            f"Unexpected result: {'connected' if success else 'blocked'}")
        return False


def parse_test_spec(line):
    """Parse test specification line
    Format: TYPE TARGET PORT [EXPECT] [SIGNATURE]
    Examples:
        DOCKER env-python 8000 "Hello from Server Container!"
        IP 1.1.1.1 443 connect
        URL www.google.com 443 connect
        IP 8.8.8.8 443 block
    """
    parts = line.strip().split()
    if len(parts) < 3:
        return None

    test_type = parts[0].upper()
    target = parts[1]
    port = int(parts[2])

    # Default expectations
    expect = "connect"
    signature = None

    if len(parts) >= 4:
        if test_type == "DOCKER":
            # For DOCKER, remaining parts are the signature
            signature = " ".join(parts[3:])
        else:
            expect = parts[3].lower()

    return {
        "type": test_type,
        "target": target,
        "port": port,
        "expect": expect,
        "signature": signature
    }


def run_test(spec):
    """Run a single test based on specification"""
    test_type = spec["type"]
    target = spec["target"]
    port = spec["port"]
    expect = spec["expect"]
    signature = spec["signature"]

    print(f"\n{'='*60}")
    print(f"Test: {test_type} {target}:{port}")
    print(f"{'='*60}")

    if test_type == "DOCKER":
        result = test_docker_env(target, port, signature if signature else "")
    elif test_type == "IP":
        result = test_ip_connectivity(target, port, expect == "connect")
    elif test_type == "URL":
        result = test_url_connectivity(target, port, expect == "connect")
    else:
        debug_log(f"Unknown test type: {test_type}")
        result = False

    status = "PASS" if result else "FAIL"
    print(f"Result: [{status}]")
    return result


def main():
    print("=" * 60)
    print("Network Test Client (Python)")
    print("=" * 60)

    # Read all input
    input_data = sys.stdin.read().strip()
    if not input_data:
        debug_log("No input provided!")
        return

    lines = input_data.split('\n')
    debug_log(f"Processing {len(lines)} test(s)")

    results = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        spec = parse_test_spec(line)
        if spec:
            result = run_test(spec)
            results.append(result)
        else:
            debug_log(f"Invalid test spec: {line}")

    print(f"\n{'='*60}")
    print(f"Summary: {sum(results)}/{len(results)} tests passed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
