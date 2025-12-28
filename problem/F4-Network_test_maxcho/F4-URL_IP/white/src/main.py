import socket


def check_target(host, port, expect_success=True, label=""):
    """Check if a connection to host:port succeeds."""
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
        
        mark = "[PASS]" if is_success == expect_success else "[FAIL]"
        expected = "connect" if expect_success else "block"
        extra = f" ({label})" if label else ""
        if is_success != expect_success:
            print(f"{mark} {host}:{port} -> {status} (expected {expected}){extra}")
        else:
            print(f"{mark} {host}:{port} -> {status}{extra}")

    except Exception as e:
        status = f"ERROR ({e})"
        if not expect_success:
            print(f"[PASS] {host}:{port} -> {status}")
        else:
            print(f"[FAIL] {host}:{port} -> {status}")


def check_dns(domain, expect_real_ip=True):
    """Check if DNS resolution returns a real IP or sinkhole (0.0.0.0)."""
    try:
        ip = socket.gethostbyname(domain)
        is_sinkhole = (ip == "0.0.0.0")
        
        if expect_real_ip and not is_sinkhole:
            print(f"[PASS] DNS {domain} -> {ip}")
        elif not expect_real_ip and is_sinkhole:
            print(f"[PASS] DNS {domain} -> {ip} (sinkholed)")
        else:
            expected = "real IP" if expect_real_ip else "sinkhole"
            print(f"[FAIL] DNS {domain} -> {ip} (expected {expected})")
    except Exception as e:
        print(f"[FAIL] DNS {domain} -> ERROR ({e})")


if __name__ == "__main__":
    print("=" * 60)
    print("Network WHITELIST Test")
    print("Config: Whitelist IP=[1.1.1.1], URL=[www.google.com]")
    print("=" * 60)
    
    # ============================================================
    # DNS Resolution Tests
    # In WHITELIST mode: only whitelisted URLs should resolve
    # ============================================================
    print("\n--- DNS Resolution Tests ---")
    
    # Whitelisted URL should resolve to real IP
    check_dns("www.google.com", expect_real_ip=True)
    
    # Non-whitelisted URLs should be sinkholed (0.0.0.0)
    check_dns("github.com", expect_real_ip=False)
    check_dns("facebook.com", expect_real_ip=False)
    check_dns("amazon.com", expect_real_ip=False)
    check_dns("cloudflare.com", expect_real_ip=False)
    check_dns("twitter.com", expect_real_ip=False)

    # ============================================================
    # Whitelisted IP Tests
    # 1.1.1.1 is in whitelist - should CONNECT
    # ============================================================
    print("\n--- Whitelisted IP Tests (1.1.1.1) ---")
    
    check_target("1.1.1.1", 443, expect_success=True, label="HTTPS")
    check_target("1.1.1.1", 80, expect_success=True, label="HTTP")
    check_target("1.1.1.1", 853, expect_success=True, label="DoT")
    check_target("1.1.1.1", 53, expect_success=True, label="DNS - NAT redirect")

    # ============================================================
    # Non-Whitelisted IP Tests
    # These IPs are NOT in whitelist - should be BLOCKED
    # ============================================================
    print("\n--- Non-Whitelisted IP Tests ---")
    
    # DNS providers - all should be blocked
    check_target("9.9.9.9", 443, expect_success=False, label="not whitelisted")
    check_target("8.8.8.8", 443, expect_success=False, label="not whitelisted")
    check_target("208.67.222.222", 443, expect_success=False, label="not whitelisted")
    
    # Other IPs
    check_target("140.82.112.3", 443, expect_success=False, label="not whitelisted")
    check_target("31.13.87.36", 443, expect_success=False, label="not whitelisted")
    
    # Port 53 - always NAT redirected to dnsmasq
    print("\n  (Note: Port 53 is NAT redirected to dnsmasq)")
    check_target("9.9.9.9", 53, expect_success=True, label="NAT redirect")
    check_target("8.8.8.8", 53, expect_success=True, label="NAT redirect")

    # ============================================================
    # Whitelisted URL Connection Tests
    # www.google.com is whitelisted - should connect on HTTP/HTTPS
    # ============================================================
    print("\n--- Whitelisted URL Connection Tests ---")
    
    check_target("www.google.com", 443, expect_success=True, label="HTTPS")
    check_target("www.google.com", 80, expect_success=True, label="HTTP")
    
    # Non-HTTP ports should be blocked (even for whitelisted URL)
    check_target("www.google.com", 22, expect_success=False, label="SSH - non-web port")
    check_target("www.google.com", 3306, expect_success=False, label="MySQL - non-web port")

    # ============================================================
    # Non-Whitelisted URL Connection Tests
    # These URLs are sinkholed - connection will fail
    # ============================================================
    print("\n--- Non-Whitelisted URL Connection Tests ---")
    
    check_target("github.com", 443, expect_success=False, label="sinkholed")
    check_target("facebook.com", 443, expect_success=False, label="sinkholed")
    check_target("amazon.com", 443, expect_success=False, label="sinkholed")
    check_target("twitter.com", 443, expect_success=False, label="sinkholed")
    check_target("cloudflare.com", 443, expect_success=False, label="sinkholed")
    check_target("microsoft.com", 443, expect_success=False, label="sinkholed")

    # ============================================================
    # Edge Cases
    # ============================================================
    print("\n--- Edge Cases ---")
    
    # Google IP (resolved from www.google.com) should be allowed
    # because URL IPs are added to the whitelist
    check_target("142.250.196.196", 443, expect_success=True, label="Google IP - resolved from URL")

    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)
    print("\nExpected behavior in WHITELIST mode:")
    print("  - Whitelisted IPs (1.1.1.1): CONNECTED on all ports")
    print("  - Whitelisted URLs (www.google.com): Resolved IPs also whitelisted")
    print("  - Non-whitelisted URLs: DNS sinkhole -> 0.0.0.0")
    print("  - Non-whitelisted IPs: BLOCKED")
    print("  - Port 53: Always NAT redirect to dnsmasq")

