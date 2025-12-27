import socket


def check_target(host, port, expect_success=True):
    """
    Check if a connection to host:port succeeds.
    expect_success: if True, "good" means connection succeeded (expected behavior)
                    if False, "good" means connection failed (expected behavior)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))

        if result == 0:
            status = "CONNECTED"
            is_success = True
        else:
            status = f"BLOCKED (errno={result})"
            is_success = False

        sock.close()
        
        if is_success == expect_success:
            print(f"[PASS] {host}:{port} -> {status}")
        else:
            print(f"[FAIL] {host}:{port} -> {status} (expected {'connect' if expect_success else 'block'})")

    except Exception as e:
        status = f"ERROR ({e})"
        if not expect_success:
            print(f"[PASS] {host}:{port} -> {status}")
        else:
            print(f"[FAIL] {host}:{port} -> {status}")


def check_dns(domain, expect_real_ip=True):
    """
    Check if DNS resolution returns a real IP or sinkhole (0.0.0.0).
    expect_real_ip: if True, we expect real IP (whitelisted domain)
                   if False, we expect 0.0.0.0 (sinkholed domain)
    """
    try:
        ip = socket.gethostbyname(domain)
        is_sinkhole = (ip == "0.0.0.0")
        
        if expect_real_ip and not is_sinkhole:
            print(f"[PASS] DNS {domain} -> {ip}")
        elif not expect_real_ip and is_sinkhole:
            print(f"[PASS] DNS {domain} -> {ip} (sinkholed)")
        else:
            print(f"[FAIL] DNS {domain} -> {ip} (expected {'real IP' if expect_real_ip else 'sinkhole'})")
    except Exception as e:
        print(f"[FAIL] DNS {domain} -> ERROR ({e})")


if __name__ == "__main__":
    print("=" * 60)
    print("Network Whitelist Test")
    print("Config: IP=[1.1.1.1], URL=[www.google.com]")
    print("=" * 60)
    
    print("\n--- DNS Resolution Tests ---")
    # Whitelisted URLs should resolve to real IPs
    check_dns("www.google.com", expect_real_ip=True)
    
    # Non-whitelisted URLs should be sinkholed
    check_dns("github.com", expect_real_ip=False)
    check_dns("facebook.com", expect_real_ip=False)
    check_dns("amazon.com", expect_real_ip=False)
    
    print("\n--- IP Connection Tests ---")
    # Whitelisted IPs should connect
    check_target("1.1.1.1", 53, expect_success=True)   # Explicit IP whitelist
    check_target("1.1.1.1", 443, expect_success=True)  # Explicit IP, any port
    
    # Non-whitelisted IPs should be blocked
    check_target("9.9.9.9", 53, expect_success=False)    # Not in whitelist
    check_target("8.8.8.8", 53, expect_success=False)    # Google DNS - not whitelisted
    check_target("208.67.222.222", 53, expect_success=False)  # OpenDNS

    print("\n--- URL Connection Tests (via DNS sinkhole) ---")
    # Whitelisted domain - should connect on HTTP/HTTPS ports
    check_target("www.google.com", 443, expect_success=True)
    check_target("www.google.com", 80, expect_success=True)
    
    # Non-whitelisted domains - DNS returns 0.0.0.0, connection will fail
    check_target("github.com", 443, expect_success=False)
    check_target("facebook.com", 443, expect_success=False)
    check_target("amazon.com", 443, expect_success=False)
    check_target("twitter.com", 443, expect_success=False)
    
    print("\n--- Edge Cases ---")
    # Non-standard ports should be blocked even for whitelisted domains
    # (unless explicit IP whitelist)
    check_target("www.google.com", 22, expect_success=False)   # SSH
    check_target("www.google.com", 3306, expect_success=False) # MySQL
    
    # Direct IP on HTTP/HTTPS ports (not in whitelist)
    check_target("93.184.216.34", 80, expect_success=False)   # example.com IP
    check_target("140.82.112.3", 443, expect_success=False)   # github.com IP

    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)
