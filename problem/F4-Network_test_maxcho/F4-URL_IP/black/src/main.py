import socket


def check_target(host, port, expect_success=True):
    """
    Check if a connection to host:port succeeds.
    expect_success: if True, "good" means connection succeeded
                    if False, "good" means connection failed
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
    print("Network BLACKLIST Test")
    print("Config: Blacklist IP=[1.1.1.1], URL=[www.google.com]")
    print("=" * 60)
    
    # ============================================================
    # DNS Resolution Tests
    # In BLACKLIST mode: blacklisted URLs should be sinkholed
    # ============================================================
    print("\n--- DNS Resolution Tests ---")
    
    # Blacklisted URL should be sinkholed (0.0.0.0)
    check_dns("www.google.com", expect_real_ip=False)
    
    # Non-blacklisted URLs should resolve normally
    check_dns("github.com", expect_real_ip=True)
    check_dns("facebook.com", expect_real_ip=True)
    check_dns("amazon.com", expect_real_ip=True)
    check_dns("cloudflare.com", expect_real_ip=True)

    # ============================================================
    # IP Connection Tests - Blacklisted IPs
    # Blacklisted IPs should be BLOCKED on non-53 ports
    # ============================================================
    print("\n--- Blacklisted IP Tests ---")
    
    # 1.1.1.1 is in blacklist - should be BLOCKED
    check_target("1.1.1.1", 443, expect_success=False)   # HTTPS - should block
    check_target("1.1.1.1", 80, expect_success=False)    # HTTP - should block
    check_target("1.1.1.1", 853, expect_success=False)   # DoT - should block
    
    # Port 53 is special - NAT redirect to dnsmasq (will show "connected")
    # This is expected behavior, not a bug
    print("\n  (Note: Port 53 is NAT redirected to dnsmasq)")
    check_target("1.1.1.1", 53, expect_success=True)     # DNS - NAT redirect

    # ============================================================
    # IP Connection Tests - Non-Blacklisted IPs
    # Non-blacklisted IPs should be ALLOWED
    # ============================================================
    print("\n--- Non-Blacklisted IP Tests ---")
    
    # Various DNS providers - should all connect
    check_target("9.9.9.9", 443, expect_success=True)       # Quad9
    check_target("9.9.9.9", 53, expect_success=True)        # Quad9 DNS (NAT redirect)
    check_target("8.8.8.8", 443, expect_success=True)       # Google DNS
    check_target("208.67.222.222", 443, expect_success=True) # OpenDNS
    
    # Random public IPs - should connect
    check_target("93.184.216.34", 80, expect_success=True)   # example.com
    check_target("140.82.112.3", 443, expect_success=True)   # github.com
    check_target("31.13.87.36", 443, expect_success=True)    # facebook.com

    # ============================================================
    # URL Connection Tests (via DNS sinkhole)
    # ============================================================
    print("\n--- URL Connection Tests ---")
    
    # Blacklisted domain - DNS sinkhole returns 0.0.0.0, connection fails
    check_target("www.google.com", 443, expect_success=False)
    check_target("www.google.com", 80, expect_success=False)
    check_target("www.google.com", 22, expect_success=False)  # Any port fails
    
    # Non-blacklisted domains - should connect normally
    check_target("github.com", 443, expect_success=True)
    check_target("facebook.com", 443, expect_success=True)
    check_target("amazon.com", 443, expect_success=True)
    check_target("twitter.com", 443, expect_success=True)
    check_target("cloudflare.com", 443, expect_success=True)
    check_target("microsoft.com", 443, expect_success=True)

    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)
    print("\nExpected behavior in BLACKLIST mode:")
    print("  - Blacklisted IPs (1.1.1.1): BLOCKED on all ports except 53")
    print("  - Blacklisted URLs (www.google.com): DNS sinkhole -> 0.0.0.0")
    print("  - Non-blacklisted IPs/URLs: ALLOWED")
    print("  - Port 53: Always NAT redirect to dnsmasq (shows CONNECTED)")
