#!/usr/bin/env python3
"""
Network Test Client for URL/IP Whitelist/Blacklist Testing
Outputs detailed debug logs and summary
"""
import socket
import sys


def debug_log(msg):
    """Print debug message"""
    print(f"[DEBUG] {msg}", flush=True)


def resolve_dns(hostname):
    """Resolve hostname to IP, return (ip, is_sinkhole, error)"""
    try:
        ip = socket.gethostbyname(hostname)
        is_sinkhole = (ip == "0.0.0.0")
        debug_log(f"DNS: {hostname} -> {ip}" + (" (SINKHOLE)" if is_sinkhole else ""))
        return ip, is_sinkhole, None
    except socket.gaierror as e:
        debug_log(f"DNS: {hostname} -> FAILED ({e})")
        return None, False, str(e)


def check_connection(host, port, timeout=3):
    """Try TCP connection, return (success, error)"""
    try:
        # If hostname, resolve first
        if not host.replace('.', '').isdigit():
            ip, is_sinkhole, error = resolve_dns(host)
            if is_sinkhole:
                return False, "sinkholed"
            if error:
                return False, error
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        debug_log(f"Connecting to {host}:{port}")
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            debug_log("Connected successfully")
            return True, None
        else:
            debug_log(f"Connection failed (errno={result})")
            return False, f"errno={result}"
    except Exception as e:
        debug_log(f"Connection error: {e}")
        return False, str(e)


def test_target(test_type, target, port, expect_connect):
    """Run a single test and return pass/fail"""
    debug_log(f"Testing: {test_type} {target}:{port}, expect={'connect' if expect_connect else 'block'}")
    
    connected, error = check_connection(target, port)
    
    passed = (connected == expect_connect)
    status = "CONNECTED" if connected else f"BLOCKED ({error})"
    result = "[PASS]" if passed else "[FAIL]"
    
    expected = "connect" if expect_connect else "block"
    if passed:
        print(f"{result} {target}:{port} -> {status}")
    else:
        print(f"{result} {target}:{port} -> {status} (expected {expected})")
    
    return passed


def parse_and_run_tests():
    """Parse input and run tests"""
    print("=" * 60)
    print("Network Test Client (Python)")
    print("=" * 60)
    
    input_data = sys.stdin.read().strip()
    if not input_data:
        debug_log("No input provided!")
        return
    
    lines = input_data.split('\n')
    results = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        parts = line.split()
        if len(parts) < 4:
            debug_log(f"Skipping invalid line: {line}")
            continue
        
        test_type = parts[0].upper()
        target = parts[1]
        port = int(parts[2])
        expect = parts[3].lower()
        
        expect_connect = (expect == "connect")
        
        print(f"\n{'-' * 40}")
        result = test_target(test_type, target, port, expect_connect)
        results.append(result)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n{'=' * 60}")
    print(f"Summary: {passed}/{total} tests passed")
    print("=" * 60)


if __name__ == "__main__":
    parse_and_run_tests()
