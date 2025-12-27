#!/bin/bash
set -e

# =============================================================================
# System Router for AI Checker
# Hardcoded whitelist: Only allows Google AI API endpoints
# =============================================================================

echo "=== Starting System Router (AI Checker) ==="

# HARDCODED: Only Google AI API endpoints allowed
WHITELIST_URLS="generativelanguage.googleapis.com aiplatform.googleapis.com"

echo "=== 1. Resolving Whitelist Domains ==="
RESOLVED_IPS=""
for url in $WHITELIST_URLS; do
    echo "Resolving domain: $url"
    ips=$(timeout 3s dig +short "$url" A || echo "")
    
    if [ -n "$ips" ]; then
        RESOLVED_IPS="$RESOLVED_IPS $ips"
        echo "Resolved $url to: $ips"
    else
        echo "Failed to resolve $url"
    fi
done

echo "=== 2. Applying Firewall Rules (Whitelist Mode) ==="

nft flush ruleset

nft add table inet filter
nft add table nat

nft add chain nat postrouting { type nat hook postrouting priority 100 \; }
nft add rule nat postrouting oifname "eth0" masquerade
nft add chain inet filter output { type filter hook output priority 0 \; policy drop \; }
nft add chain inet filter ai_out

nft add rule inet filter output oifname "lo" accept
nft add rule inet filter output ct state established,related accept
nft add rule inet filter output meta skuid 0 udp dport 53 accept
nft add rule inet filter output meta skuid 0 tcp dport 53 accept

# Apply rules to both teacher (UID 1450) and student (UID 1451)
nft add rule inet filter output meta skuid 1450 jump ai_out
nft add rule inet filter output meta skuid 1451 jump ai_out

# Allow DNS queries
nft add rule inet filter ai_out udp dport 53 accept
nft add rule inet filter ai_out tcp dport 53 accept

# Allow resolved Google AI API IPs
for ip in $RESOLVED_IPS; do
    if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        nft add rule inet filter ai_out ip daddr "$ip" accept
        echo "Allowed IP: $ip"
    fi
done

# Reject everything else
nft add rule inet filter ai_out reject
echo "All other traffic will be rejected"

echo "=== 3. Dropping Privileges ==="

nft list ruleset > /dev/null 2>&1 || echo "Rules applied (output hidden)"

if ! id -u nobody > /dev/null 2>&1; then
    adduser -D -u 65534 nobody || useradd -u 65534 -U -M -s /bin/false nobody
fi

echo "System Router is running (as user 'nobody')..."
if command -v su-exec >/dev/null; then
    exec su-exec nobody sleep infinity
else
    exec su -s /bin/sh nobody -c "sleep infinity"
fi
