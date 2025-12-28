#!/usr/bin/env python3
"""
Simple Network Connectivity Test
Just shows CONNECTED or NOT CONNECTED for each target
"""
import socket


def check_connection(host: str, port: int, timeout: float = 3.0) -> bool:
    """Try to connect to host:port, return True if connected"""
    try:
        # Try to resolve hostname first
        if not host.replace('.', '').isdigit():
            try:
                ip = socket.gethostbyname(host)
                print(f"  DNS: {host} -> {ip}")
            except socket.gaierror:
                print(f"  DNS: {host} -> FAILED (sinkholed)")
                return False

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        return False


def test(host: str, port: int):
    """Test connection and print result"""
    connected = check_connection(host, port)
    status = "CONNECTED" if connected else "NOT CONNECTED"
    print(f"{host}:{port} -> {status}")


def main():
    print("=" * 60)
    print("Simple Network Connectivity Test")
    print("=" * 60)

    print("\n--- IP Connection Tests ---")
    test("1.1.1.1", 443)
    test("1.1.1.1", 80)
    test("8.8.8.8", 443)
    test("9.9.9.9", 443)

    print("\n--- URL Connection Tests ---")
    test("www.google.com", 443)
    test("www.google.com", 80)
    test("github.com", 443)
    test("facebook.com", 443)
    test("amazon.com", 443)

    print("\n--- Port 53 Tests (NAT redirected) ---")
    test("1.1.1.1", 53)
    test("8.8.8.8", 53)

    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
