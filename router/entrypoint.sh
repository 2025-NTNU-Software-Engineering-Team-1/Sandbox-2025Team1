#!/bin/bash
set -e

CONFIG_FILE="/etc/network_config/network_ip.json"

echo "=== Starting Router Firewall ==="

# 1. init nftables
nft flush ruleset
nft add table inet filter
nft add chain inet filter output { type filter hook output priority 0 \; policy accept \; }
nft add chain inet filter student_out


nft add table nat
nft add chain nat postrouting { type nat hook postrouting priority 100 \; }
nft add rule nat postrouting oifname "eth0" masquerade

# 2. base rules
nft add rule inet filter output oifname "lo" accept  # allow localhost
nft add rule inet filter output ct state established,related accept # allow established/related packets
nft add rule inet filter output udp dport 53 accept  # allow DNS
nft add rule inet filter output tcp dport 53 accept

# 3. UID based rules
# Teacher (UID 1450): allow 
nft add rule inet filter output meta skuid 1450 accept
nft add rule inet filter output meta skuid 1451 jump student_out
nft add rule inet filter output meta skuid 0 accept

# 4. Read JSON config
if [ -f "$CONFIG_FILE" ]; then
    MODEL=$(jq -r '.model // "black"' "$CONFIG_FILE" | tr '[:upper:]' '[:lower:]')
    IPS=$(jq -r '.ip[] // empty' "$CONFIG_FILE")
    URLS=$(jq -r '.url[] // empty' "$CONFIG_FILE")

    echo "Mode: $MODEL"

    # URL to IP resolution
    RESOLVED_IPS=""
    for url in $URLS; do
        domain=$(echo "$url" | sed -E 's|https?://||' | cut -d/ -f1)
        echo "Resolving domain: $domain"

        ips=$(dig +short "$domain" A)

        if [ -n "$ips" ]; then
            RESOLVED_IPS="$RESOLVED_IPS $ips"
            echo "Resolved $domain to: $ips"
        else
            echo "Failed to resolve $domain"
        fi
    done
    
    ALL_IPS="$IPS $RESOLVED_IPS"

    if [ "$MODEL" == "white" ]; then
        # === Whitelist mode ===
        for ip in $ALL_IPS; do
            echo "Allow: $ip"
            if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                nft add rule inet filter student_out ip daddr "$ip" accept
            fi
        done
        nft add rule inet filter student_out reject
    else
        # === Blacklist mode ===
        for ip in $ALL_IPS; do
            echo "Deny: $ip"
            if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                nft add rule inet filter student_out ip daddr "$ip" reject
            fi
        done
        nft add rule inet filter student_out accept
    fi
else
    echo "No config found, allowing all."
fi

nft list ruleset
echo "=== Router Rules Applied. Sleeping... ==="
exec sleep infinity