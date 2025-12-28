#!/usr/bin/env python3
"""
Combined Pull_image + URL_IP network test
Input format (from .in file):
  - sidecar <hostname> <port>      -> test sidecar container connection
  - external ip <ip> <port>        -> test external IP connection
  - external url <hostname> <port> -> test external URL connection
Output: debug logs showing connection attempts and results
"""

import socket
import sys


def debug(msg):
    """Print debug message to stdout"""
    print(f"[DEBUG] {msg}")


def test_redis(host, port):
    """Test Redis sidecar with AUTH command"""
    debug(f"Testing Redis sidecar at {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        debug(f"Connecting to {host}:{port}...")
        sock.connect((host, port))
        debug("Connected!")
        
        # Send Redis AUTH command
        password = "noj_secret_pass"
        command = f"AUTH {password}\r\n"
        debug(f"Sending AUTH command...")
        sock.sendall(command.encode())
        
        response = sock.recv(1024).decode()
        debug(f"Raw response: {repr(response)}")
        
        if response.startswith("+OK"):
            debug("Redis AUTH successful!")
            print("RESULT: PASS")
        else:
            debug(f"Redis AUTH failed: {response}")
            print("RESULT: FAIL")
        
        sock.close()
    except Exception as e:
        debug(f"Exception: {e}")
        print("RESULT: FAIL")


def test_http(host, port):
    """Test HTTP sidecar (busybox httpd)"""
    debug(f"Testing HTTP sidecar at {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        debug(f"Connecting to {host}:{port}...")
        sock.connect((host, port))
        debug("Connected!")
        
        # Send HTTP GET request
        request = f"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n"
        debug(f"Sending HTTP GET request...")
        sock.sendall(request.encode())
        
        debug("Receiving response...")
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        
        response_str = response.decode('utf-8', errors='replace')
        debug(f"Response length: {len(response_str)}")
        debug(f"Content snippet: {repr(response_str[:200])}...")
        
        if "verify_env_args_success" in response_str:
            debug("HTTP secret keyword found!")
            print("RESULT: PASS")
        else:
            debug("HTTP secret keyword NOT found")
            print("RESULT: FAIL")
        
        sock.close()
    except Exception as e:
        debug(f"Exception: {e}")
        print("RESULT: FAIL")


def test_external_connection(host, port, is_url=False):
    """Test external network connection (IP or URL)"""
    conn_type = "URL" if is_url else "IP"
    debug(f"Testing external {conn_type} connection to {host}:{port}")
    
    try:
        # DNS resolution for URLs
        if is_url:
            debug(f"Resolving DNS for {host}...")
            try:
                resolved_ip = socket.gethostbyname(host)
                debug(f"Resolved {host} -> {resolved_ip}")
                if resolved_ip == "0.0.0.0":
                    debug("DNS sinkholed! This URL is not whitelisted.")
                    print("RESULT: BLOCKED (sinkhole)")
                    return
            except socket.gaierror as e:
                debug(f"DNS resolution failed: {e}")
                print("RESULT: FAIL (DNS)")
                return
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        debug(f"Connecting to {host}:{port}...")
        result = sock.connect_ex((host, port))
        
        if result == 0:
            debug("Connection successful!")
            print("RESULT: PASS")
            
            # If HTTPS, just confirm we can connect
            if port == 443:
                debug("HTTPS port connected, TLS handshake not performed")
            elif port == 80:
                # Send simple HTTP request
                request = f"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n"
                sock.sendall(request.encode())
                response = sock.recv(1024)
                debug(f"HTTP response snippet: {repr(response[:100])}")
        else:
            debug(f"Connection blocked (errno={result})")
            print("RESULT: BLOCKED")
        
        sock.close()
    except Exception as e:
        debug(f"Exception: {e}")
        print("RESULT: FAIL")


def main():
    debug("=" * 60)
    debug("Combined Pull_image + URL_IP Network Test")
    debug("=" * 60)
    
    # Read input
    line = sys.stdin.read().strip()
    debug(f"Input: {repr(line)}")
    
    if not line:
        debug("No input provided")
        print("RESULT: FAIL (no input)")
        return
    
    parts = line.split()
    
    if parts[0] == "sidecar":
        # Format: sidecar <hostname> <port>
        if len(parts) < 3:
            debug("Invalid sidecar format, expected: sidecar <hostname> <port>")
            print("RESULT: FAIL (bad input)")
            return
        
        host = parts[1]
        port = int(parts[2])
        
        if port == 6379:
            test_redis(host, port)
        elif port == 8080:
            test_http(host, port)
        else:
            debug(f"Unknown sidecar port {port}, attempting generic TCP connect")
            test_external_connection(host, port, is_url=False)
    
    elif parts[0] == "external":
        # Format: external ip <ip> <port> OR external url <hostname> <port>
        if len(parts) < 4:
            debug("Invalid external format, expected: external (ip|url) <host> <port>")
            print("RESULT: FAIL (bad input)")
            return
        
        ext_type = parts[1]
        host = parts[2]
        port = int(parts[3])
        
        if ext_type == "ip":
            test_external_connection(host, port, is_url=False)
        elif ext_type == "url":
            test_external_connection(host, port, is_url=True)
        else:
            debug(f"Unknown external type: {ext_type}")
            print("RESULT: FAIL (bad input)")
    
    else:
        debug(f"Unknown command: {parts[0]}")
        print("RESULT: FAIL (unknown command)")
    
    debug("=" * 60)
    debug("Test complete")
    debug("=" * 60)


if __name__ == "__main__":
    main()
