#!/bin/bash
set -e

CONFIG_FILE="/etc/network_config/network_ip.json"
SIDECAR_IPS=""

echo "=== Starting Router Firewall ==="

echo "=== 1. Prepare Configuration ==="
MODEL="Black"
IPS=""
URLS=""

if [ -f "$CONFIG_FILE" ]; then
    MODEL=$(jq -r '.model // "black"' "$CONFIG_FILE" | tr '[:upper:]' '[:lower:]')
    IPS=$(jq -r '(.ip // [])[]' "$CONFIG_FILE")
    URLS=$(jq -r '(.url // [])[]' "$CONFIG_FILE")
    SIDECAR_IPS=$(jq -r '(.sidecar_whitelist // [])[]' "$CONFIG_FILE")

fi

echo "Mode: $MODEL"

RESOLVED_IPS=""
for url in $URLS; do
    domain=$(echo "$url" | sed -E 's|https?://||' | cut -d/ -f1)
    echo "Resolving domain: $domain"
    ips=$(timeout 3s dig +short "$domain" A || echo "")

    if [ -n "$ips" ]; then
        RESOLVED_IPS="$RESOLVED_IPS $ips"
        echo "Resolved $domain to: $ips"
    else
        echo "Failed to resolve $domain"
    fi
done

ALL_IPS="$IPS $RESOLVED_IPS"

echo "=== 2. Applying Firewall Rules ==="

nft flush ruleset

nft add table inet filter
nft add table nat

nft add chain nat postrouting { type nat hook postrouting priority 100 \; }
nft add rule nat postrouting oifname "eth0" masquerade
nft add chain inet filter output { type filter hook output priority 0 \; policy drop \; }   
nft add chain inet filter student_out

nft add rule inet filter output oifname "lo" accept
nft add rule inet filter output ct state established,related accept
nft add rule inet filter output meta skuid 0 udp dport 53 accept
nft add rule inet filter output meta skuid 0 tcp dport 53 accept

nft add rule inet filter output meta skuid 1450 jump student_out

if [ "$MODEL" == "white" ]; then
    echo "Configuring Whitelist..."
    
    for sip in $SIDECAR_IPS; do
        echo "Allow Sidecar: $sip"
        if [[ "$sip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            nft add rule inet filter student_out ip daddr "$sip" accept
        fi
    done
    
    nft add rule inet filter student_out udp dport 53 accept
    nft add rule inet filter student_out tcp dport 53 accept

    for ip in $ALL_IPS; do
        if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            nft add rule inet filter student_out ip daddr "$ip" accept
        fi
    done

    nft add rule inet filter student_out reject
else
    echo "Configuring Blacklist..."
    for ip in $ALL_IPS; do
        if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            nft add rule inet filter student_out ip daddr "$ip" reject
        fi
    done
    nft add rule inet filter student_out accept
fi

echo "=== 3. Dropping Privileges ==="

nft list ruleset > /dev/null 2>&1 || echo "Rules applied (output hidden)"

if ! id -u nobody > /dev/null 2>&1; then
    adduser -D -u 65534 nobody || useradd -u 65534 -U -M -s /bin/false nobody
fi

echo "Router is running (as user 'nobody')..."
if command -v su-exec >/dev/null; then
    exec su-exec nobody sleep infinity
else
    # Fallback to standard su if su-exec not installed
    exec su -s /bin/sh nobody -c "sleep infinity"
fi