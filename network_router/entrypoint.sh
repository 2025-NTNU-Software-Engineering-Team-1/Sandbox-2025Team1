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
# 2. Prepare domain list from URLs
# ============================================================
DOMAINS=""
for url in $URLS; do
    domain=$(echo "$url" | sed -E 's|https?://||' | cut -d/ -f1)
    DOMAINS="$DOMAINS $domain"
done
echo "Domains from URLs: $DOMAINS"

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

# Allow rebinding to localhost (needed for Docker DNS 127.0.0.11)
rebind-localhost-ok

# Don't cache negative (NXDOMAIN) responses
# This helps with timing issues where Docker DNS may not be ready immediately
no-negcache

# DO NOT use strict-order - allows fallback to other DNS servers
# strict-order
DNSMASQ_CONF

# Initialize blocklist and allowlist files
> "$DNSMASQ_BLOCKLIST"
> "$DNSMASQ_ALLOWLIST"

if [ "$MODEL" == "black" ]; then
    # ============================================================
    # Blacklist Mode: Block specific domains, allow everything else
    # URLs are blocked via DNS sinkhole (returns 0.0.0.0)
    # IPs are blocked via firewall rules
    # ============================================================
    echo "Configuring Blacklist DNS Sinkhole..."

    # Step 1: Map internal container names to their IPs (same as white mode)
    # Since router is on a different primary network (bridge), Docker DNS (127.0.0.11)
    # cannot resolve container names in noj-net. We use direct host-record mapping.
    NAMES_ARRAY=($INTERNAL_NAMES)
    IPS_ARRAY=($SIDECAR_IPS)
    
    echo "Internal names count: ${#NAMES_ARRAY[@]}"
    echo "Sidecar IPs count: ${#IPS_ARRAY[@]}"
    
    for i in "${!NAMES_ARRAY[@]}"; do
        name="${NAMES_ARRAY[$i]}"
        ip="${IPS_ARRAY[$i]}"
        if [ -n "$name" ] && [ -n "$ip" ]; then
            echo "Mapping internal name '$name' -> $ip"
            echo "host-record=$name,$ip" >> "$DNSMASQ_ALLOWLIST"
        fi
    done

    # Step 2: Block specific domains via DNS Sinkhole
    for domain in $DOMAINS; do
        echo "Blocking domain: $domain"
        # Sinkhole the domain (return 0.0.0.0) - connection will fail
        echo "address=/$domain/0.0.0.0" >> "$DNSMASQ_BLOCKLIST"
        echo "address=/$domain/::" >> "$DNSMASQ_BLOCKLIST"
    done


elif [ "$MODEL" == "white" ]; then
    # ============================================================
    # Whitelist Mode: Catch-all blocking with explicit exceptions
    # Use nftset to dynamically add resolved IPs to firewall whitelist
    # ============================================================
    echo "Configuring Whitelist DNS Sinkhole (catch-all mode)..."

    # Step 1: Map internal container names to their IPs
    # Since router is on a different primary network (bridge), Docker DNS (127.0.0.11)
    # cannot resolve container names in noj-net. We use direct host-record mapping.
    # Convert space-separated lists to arrays
    NAMES_ARRAY=($INTERNAL_NAMES)
    IPS_ARRAY=($SIDECAR_IPS)
    
    echo "Internal names count: ${#NAMES_ARRAY[@]}"
    echo "Sidecar IPs count: ${#IPS_ARRAY[@]}"
    
    for i in "${!NAMES_ARRAY[@]}"; do
        name="${NAMES_ARRAY[$i]}"
        ip="${IPS_ARRAY[$i]}"
        if [ -n "$name" ] && [ -n "$ip" ]; then
            echo "Mapping internal name '$name' -> $ip"
            # Use host-record to directly map name to IP (no upstream DNS query needed)
            echo "host-record=$name,$ip" >> "$DNSMASQ_ALLOWLIST"
        fi
    done


    # Step 2: Allow whitelisted external domains and add resolved IPs to nftables set
    # The nftset option adds resolved IPs to the specified nftables set
    for domain in $DOMAINS; do
        echo "Allowing domain (with dynamic IP): $domain"
        echo "server=/$domain/8.8.8.8" >> "$DNSMASQ_ALLOWLIST"
        echo "server=/$domain/8.8.4.4" >> "$DNSMASQ_ALLOWLIST"
        # Add resolved IPs to nftables sets (4 = IPv4, 6 = IPv6)
        echo "nftset=/$domain/4#inet#filter#url_whitelist_ipv4" >> "$DNSMASQ_ALLOWLIST"
        echo "nftset=/$domain/6#inet#filter#url_whitelist_ipv6" >> "$DNSMASQ_ALLOWLIST"
    done

    # Step 3: Block everything else (catch-all)
    # NOTE: The server= directives above take precedence for their specific domains
    # address=/#/ is a catch-all for domains that don't have specific server= rules
    echo "address=/#/0.0.0.0" >> "$DNSMASQ_BLOCKLIST"
    echo "address=/#/::" >> "$DNSMASQ_BLOCKLIST"
    echo "Catch-all blocking enabled: all non-whitelisted domains return 0.0.0.0"
    echo "Dynamic IP whitelisting enabled via nftset"
fi

echo "DNS Sinkhole blocklist:"
cat "$DNSMASQ_BLOCKLIST"
echo "DNS Sinkhole allowlist:"
cat "$DNSMASQ_ALLOWLIST"

# ============================================================
# 4. Apply nftables Firewall Rules (IPv4 + IPv6)
# IMPORTANT: Create nftables sets BEFORE starting dnsmasq
# dnsmasq needs the sets to exist to add IPs to them
# ============================================================
echo "=== 3. Applying Firewall Rules ==="

nft flush ruleset

# Create tables
nft add table inet filter
nft add table inet nat

# Create sets for dynamic URL IP whitelisting
# These sets will be populated by dnsmasq when it resolves whitelisted domains
nft add set inet filter url_whitelist_ipv4 { type ipv4_addr \; flags timeout \; timeout 5m \; }
nft add set inet filter url_whitelist_ipv6 { type ipv6_addr \; flags timeout \; timeout 5m \; }

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
    echo "  Strategy: DNS sinkhole for URL control + dynamic IP whitelisting"
    echo "  Note: All port 53 traffic is NAT redirected to dnsmasq"

    # Allow Sidecar IPs
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

    # Allow explicit IP whitelist (from config)
    for ip in $IPS; do
        if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Allow explicit IPv4: $ip"
            nft add rule inet filter student_out ip daddr "$ip" accept
        elif [[ "$ip" =~ : ]]; then
            echo "Allow explicit IPv6: $ip"
            nft add rule inet filter student_out ip6 daddr "$ip" accept
        fi
    done

    # Allow IPs from dynamic URL whitelist (populated by dnsmasq nftset)
    # These IPs are added when dnsmasq resolves whitelisted domains
    nft add rule inet filter student_out ip daddr @url_whitelist_ipv4 accept
    nft add rule inet filter student_out ip6 daddr @url_whitelist_ipv6 accept
    echo "Dynamic URL whitelist rules added (using nftables sets)"

    # Reject everything else
    nft add rule inet filter student_out reject

else
    echo "Configuring Blacklist firewall rules..."
    echo "  Strategy: DNS sinkhole blocks URLs (returns 0.0.0.0)"
    echo "  Firewall blocks explicit IPs"

    # Block explicit IP blacklist (from config)
    for ip in $IPS; do
        if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Block explicit IPv4: $ip"
            nft add rule inet filter student_out ip daddr "$ip" reject
        elif [[ "$ip" =~ : ]]; then
            echo "Block explicit IPv6: $ip"
            nft add rule inet filter student_out ip6 daddr "$ip" reject
        fi
    done

    # Allow everything else (DNS sinkhole handles URL blocking)
    nft add rule inet filter student_out accept
fi

echo "=== Firewall Rules Applied ==="
nft list ruleset

# ============================================================
# 6. Start dnsmasq (AFTER nftables sets are created)
# ============================================================
echo "=== 4. Starting dnsmasq ==="

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
# 7. Drop Privileges and Keep Running
# ============================================================
echo "=== 5. Dropping Privileges ==="

if ! id -u nobody > /dev/null 2>&1; then
    adduser -D -u 65534 nobody || useradd -u 65534 -U -M -s /bin/false nobody
fi

echo "Router with DNS Sinkhole is running..."
echo "  - dnsmasq PID: $DNSMASQ_PID"
echo "  - Mode: $MODEL"
echo "  - IPv6: Enabled"
echo "  - Dynamic IP whitelisting: $([ '$MODEL' == 'white' ] && echo 'Enabled' || echo 'N/A')"

# Wait for dnsmasq (keep container running)
wait $DNSMASQ_PID
