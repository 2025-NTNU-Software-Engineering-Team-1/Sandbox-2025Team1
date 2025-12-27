#!/bin/bash
set -e

CONFIG_FILE="/etc/network_config/network_ip.json"
DNSMASQ_BLOCKLIST="/etc/dnsmasq.d/blocklist.conf"
DNSMASQ_ALLOWLIST="/etc/dnsmasq.d/allowlist.conf"

echo "=== Starting Router with DNS Sinkhole + IPv6 ==="

# ============================================================
# 1. Parse Configuration
# ============================================================
echo "=== 1. Prepare Configuration ==="

MODEL="black"
IPS=""
URLS=""
SIDECAR_IPS=""
INTERNAL_NAMES=""

if [ -f "$CONFIG_FILE" ]; then
    MODEL=$(jq -r '.model // "black"' "$CONFIG_FILE" | tr '[:upper:]' '[:lower:]')
    IPS=$(jq -r '(.ip // [])[]' "$CONFIG_FILE")
    URLS=$(jq -r '(.url // [])[]' "$CONFIG_FILE")
    SIDECAR_IPS=$(jq -r '(.sidecar_whitelist // [])[]' "$CONFIG_FILE")
    INTERNAL_NAMES=$(jq -r '(.internal_names // [])[]' "$CONFIG_FILE")
fi

echo "Mode: $MODEL"
echo "IPs: $IPS"
echo "URLs: $URLS"
echo "Sidecar IPs: $SIDECAR_IPS"
echo "Internal Names: $INTERNAL_NAMES"

# ============================================================
# 2. DNS Resolution with IPv6 Support and Retry
# ============================================================
resolve_with_retry() {
    local domain="$1"
    local max_attempts=3
    local attempt=1
    local all_ips=""

    while [ $attempt -le $max_attempts ]; do
        # Resolve IPv4 (A records)
        ipv4=$(timeout 5s dig +short "$domain" A 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' || echo "")
        # Resolve IPv6 (AAAA records)
        ipv6=$(timeout 5s dig +short "$domain" AAAA 2>/dev/null | grep -E '^[0-9a-fA-F:]+$' || echo "")

        if [ -n "$ipv4" ] || [ -n "$ipv6" ]; then
            all_ips="$ipv4 $ipv6"
            echo "$all_ips"
            return 0
        fi

        echo "Retry $attempt for $domain..." >&2
        sleep 1
        attempt=$((attempt + 1))
    done

    echo "" # Return empty on failure
    return 1
}

# Resolve URLs to IPs (for IP-based blocking fallback)
RESOLVED_IPV4=""
RESOLVED_IPV6=""

for url in $URLS; do
    domain=$(echo "$url" | sed -E 's|https?://||' | cut -d/ -f1)
    echo "Resolving domain: $domain"

    # Get all IPs with retry
    ips=$(resolve_with_retry "$domain")

    for ip in $ips; do
        if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            RESOLVED_IPV4="$RESOLVED_IPV4 $ip"
            echo "  IPv4: $ip"
        elif [[ "$ip" =~ : ]]; then
            RESOLVED_IPV6="$RESOLVED_IPV6 $ip"
            echo "  IPv6: $ip"
        fi
    done
done

ALL_IPV4="$IPS $RESOLVED_IPV4"
ALL_IPV6="$RESOLVED_IPV6"

echo "All IPv4: $ALL_IPV4"
echo "All IPv6: $ALL_IPV6"

# ============================================================
# 3. Configure DNS Sinkhole (dnsmasq)
# ============================================================
echo "=== 2. Configuring DNS Sinkhole ==="

# Get dnsmasq user UID for firewall rules
DNSMASQ_UID=$(id -u dnsmasq 2>/dev/null || echo "100")
echo "dnsmasq UID: $DNSMASQ_UID"

# Base dnsmasq configuration
cat > /etc/dnsmasq.conf << 'DNSMASQ_CONF'
# Upstream DNS servers for external queries (FIRST - most reliable)
server=8.8.8.8
server=8.8.4.4
server=2001:4860:4860::8888
server=2001:4860:4860::8844

# Docker's embedded DNS for internal container name resolution (LAST - fallback)
# Only used for resolving internal container names like "redis-sidecar"
server=127.0.0.11

# Don't use /etc/resolv.conf
no-resolv

# Don't read /etc/hosts
no-hosts

# Listen ONLY on loopback interfaces
# This ensures responses use the correct source address (127.0.0.1)
# All external queries are redirected to 127.0.0.1:53 via NAT
listen-address=127.0.0.1
listen-address=::1

# Cache size
cache-size=1000

# Log queries for debugging
log-queries
log-facility=/var/log/dnsmasq.log

# Load blocklist/allowlist
conf-dir=/etc/dnsmasq.d/,*.conf

# DO NOT use strict-order - allows fallback to other DNS servers
# strict-order
DNSMASQ_CONF

# Initialize blocklist and allowlist files
> "$DNSMASQ_BLOCKLIST"
> "$DNSMASQ_ALLOWLIST"

if [ "$MODEL" == "black" ]; then
    # ============================================================
    # Blacklist Mode: Block specific domains, allow everything else
    # ============================================================
    echo "Configuring Blacklist DNS Sinkhole..."

    # Extract domains from URLs and block them via DNS Sinkhole
    for url in $URLS; do
        domain=$(echo "$url" | sed -E 's|https?://||' | cut -d/ -f1)
        echo "Blocking domain from URL: $domain"
        echo "address=/$domain/0.0.0.0" >> "$DNSMASQ_BLOCKLIST"
        echo "address=/$domain/::" >> "$DNSMASQ_BLOCKLIST"
    done

elif [ "$MODEL" == "white" ]; then
    # ============================================================
    # Whitelist Mode: Catch-all blocking with explicit exceptions
    # ============================================================
    echo "Configuring Whitelist DNS Sinkhole (catch-all mode)..."

    # Strategy:
    # 1. Block ALL domains with address=/#/0.0.0.0 (catch-all)
    # 2. Allow internal container names via server=/name/127.0.0.11
    # 3. Allow whitelisted domains via server=/domain/8.8.8.8
    # Note: server= directive overrides address= for specific domains

    # Step 1: Allow internal container names FIRST (more specific rules)
    # These are resolved by Docker's embedded DNS
    for name in $INTERNAL_NAMES; do
        echo "Allowing internal name: $name"
        echo "server=/$name/127.0.0.11" >> "$DNSMASQ_ALLOWLIST"
    done

    # Step 2: Allow whitelisted external domains
    for url in $URLS; do
        domain=$(echo "$url" | sed -E 's|https?://||' | cut -d/ -f1)
        echo "Allowing domain: $domain"
        echo "server=/$domain/8.8.8.8" >> "$DNSMASQ_ALLOWLIST"
        echo "server=/$domain/8.8.4.4" >> "$DNSMASQ_ALLOWLIST"
    done

    # Step 3: Block everything else (catch-all)
    # This MUST come after the allowlist entries
    echo "address=/#/0.0.0.0" >> "$DNSMASQ_BLOCKLIST"
    echo "address=/#/::" >> "$DNSMASQ_BLOCKLIST"
    echo "Catch-all blocking enabled: all non-whitelisted domains return 0.0.0.0"
fi

echo "DNS Sinkhole blocklist:"
cat "$DNSMASQ_BLOCKLIST"
echo "DNS Sinkhole allowlist:"
cat "$DNSMASQ_ALLOWLIST"

# Start dnsmasq
echo "Starting dnsmasq..."
dnsmasq --keep-in-foreground &
DNSMASQ_PID=$!
sleep 1

# Verify dnsmasq is running
if ! kill -0 $DNSMASQ_PID 2>/dev/null; then
    echo "ERROR: dnsmasq failed to start!"
    cat /var/log/dnsmasq.log 2>/dev/null || true
    exit 1
fi
echo "dnsmasq started with PID $DNSMASQ_PID"

# ============================================================
# 4. Apply nftables Firewall Rules (IPv4 + IPv6)
# ============================================================
echo "=== 3. Applying Firewall Rules ==="

nft flush ruleset

# Create tables
nft add table inet filter
nft add table inet nat

# NAT chains
nft add chain inet nat prerouting { type nat hook prerouting priority -100 \; }
nft add chain inet nat postrouting { type nat hook postrouting priority 100 \; }
nft add chain inet nat output { type nat hook output priority -100 \; }

# Redirect all DNS queries to local dnsmasq (DNS Sinkhole)
# Prerouting: handles incoming packets from other containers
nft add rule inet nat prerouting udp dport 53 redirect to :53
nft add rule inet nat prerouting tcp dport 53 redirect to :53

# Output: handles locally-generated packets (student container DNS queries)
# Exclude root (UID 0) AND dnsmasq user to avoid redirect loop
# dnsmasq needs to query upstream DNS servers directly
nft add rule inet nat output meta skuid 0 accept
nft add rule inet nat output meta skuid $DNSMASQ_UID accept
nft add rule inet nat output udp dport 53 redirect to :53
nft add rule inet nat output tcp dport 53 redirect to :53

# Outbound NAT (masquerade) - for all outgoing interfaces
nft add rule inet nat postrouting masquerade

# Output filter chain (default drop)
nft add chain inet filter output { type filter hook output priority 0 \; policy drop \; }
nft add chain inet filter student_out

# Allow loopback
nft add rule inet filter output oifname "lo" accept

# Root can access anything (for system operations)
nft add rule inet filter output meta skuid 0 accept

# dnsmasq user can access anything (for upstream DNS queries)
nft add rule inet filter output meta skuid $DNSMASQ_UID accept

# Teacher (UID 1450) and Student (UID 1451) jump to student_out chain
# IMPORTANT: These rules must come BEFORE ct state established,related
# Otherwise established connections bypass the whitelist check!
nft add rule inet filter output meta skuid 1450 jump student_out
nft add rule inet filter output meta skuid 1451 jump student_out

# Allow established/related connections (for other users, after student check)
nft add rule inet filter output ct state established,related accept

# ============================================================
# 5. Configure student_out chain based on mode
# ============================================================
if [ "$MODEL" == "white" ]; then
    echo "Configuring Whitelist firewall rules..."
    echo "  Strategy: DNS sinkhole for URL control, firewall for explicit IPs only"
    echo "  Note: All port 53 traffic is NAT redirected to dnsmasq (sinkhole)"

    # ============================================================
    # 5b. Configure student_out chain (filter table)
    # ============================================================

    # Allow Sidecar IPs (IPv4 and IPv6)
    for sip in $SIDECAR_IPS; do
        echo "Allow Sidecar: $sip"
        if [[ "$sip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            nft add rule inet filter student_out ip daddr "$sip" accept
        elif [[ "$sip" =~ : ]]; then
            nft add rule inet filter student_out ip6 daddr "$sip" accept
        fi
    done

    # Allow local DNS (dnsmasq on localhost)
    nft add rule inet filter student_out ip daddr 127.0.0.1 udp dport 53 accept
    nft add rule inet filter student_out ip daddr 127.0.0.1 tcp dport 53 accept
    nft add rule inet filter student_out ip6 daddr ::1 udp dport 53 accept
    nft add rule inet filter student_out ip6 daddr ::1 tcp dport 53 accept

    # Allow explicitly whitelisted IPs (from $IPS only, not resolved URLs)
    # We rely on DNS sinkhole for URL-based control, not IP resolution
    for ip in $IPS; do
        if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Allow explicit IP: $ip"
            nft add rule inet filter student_out ip daddr "$ip" accept
        elif [[ "$ip" =~ : ]]; then
            echo "Allow explicit IPv6: $ip"
            nft add rule inet filter student_out ip6 daddr "$ip" accept
        fi
    done

    # If URL rules exist, allow HTTP/HTTPS ports for whitelisted domains
    # DNS sinkhole will return 0.0.0.0 for non-whitelisted domains
    if [ -n "$URLS" ]; then
        echo "URL whitelist detected: Allowing HTTP/HTTPS ports"
        echo "  (DNS sinkhole will block non-whitelisted domains)"
        
        # Allow common web ports
        nft add rule inet filter student_out tcp dport 80 accept    # HTTP
        nft add rule inet filter student_out tcp dport 443 accept   # HTTPS
        nft add rule inet filter student_out tcp dport 8080 accept  # Alt HTTP
        nft add rule inet filter student_out tcp dport 8443 accept  # Alt HTTPS
    fi

    # Reject everything else
    nft add rule inet filter student_out reject

else
    echo "Configuring Blacklist firewall rules..."

    # Block blacklisted IPv4 addresses
    for ip in $ALL_IPV4; do
        if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Block IPv4: $ip"
            nft add rule inet filter student_out ip daddr "$ip" reject
        fi
    done

    # Block blacklisted IPv6 addresses
    for ip in $ALL_IPV6; do
        if [[ "$ip" =~ : ]]; then
            echo "Block IPv6: $ip"
            nft add rule inet filter student_out ip6 daddr "$ip" reject
        fi
    done

    # Allow everything else
    nft add rule inet filter student_out accept
fi

echo "=== Firewall Rules Applied ==="
nft list ruleset

# ============================================================
# 6. Drop Privileges and Keep Running
# ============================================================
echo "=== 4. Dropping Privileges ==="

if ! id -u nobody > /dev/null 2>&1; then
    adduser -D -u 65534 nobody || useradd -u 65534 -U -M -s /bin/false nobody
fi

echo "Router with DNS Sinkhole is running..."
echo "  - dnsmasq PID: $DNSMASQ_PID"
echo "  - Mode: $MODEL"
echo "  - IPv6: Enabled"

# Wait for dnsmasq (keep container running)
wait $DNSMASQ_PID
