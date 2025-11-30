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
# Student (UID 1451): jump to student_out for checking
nft add rule inet filter output meta skuid 1451 jump student_out
# Root (UID 0): allow (Router itself needs to operate)
nft add rule inet filter output meta skuid 0 accept

# 4. Read JSON config
if [ -f "$CONFIG_FILE" ]; then
    MODEL=$(jq -r '.model // "black"' "$CONFIG_FILE" | tr '[:upper:]' '[:lower:]')
    IPS=$(jq -r '.ip[] // empty' "$CONFIG_FILE")
    
    echo "Mode: $MODEL"

    if [ "$MODEL" == "white" ]; then
        # === Whitelist mode ===
        for ip in $IPS; do
            echo "Allow: $ip"
            nft add rule inet filter student_out ip daddr "$ip" accept
        done
        # Finally reject all (Reject returns an error, faster than Drop)
        nft add rule inet filter student_out reject
    else
        # === Blacklist mode ===
        for ip in $IPS; do
            echo "Deny: $ip"
            nft add rule inet filter student_out ip daddr "$ip" reject
        done
        # Finally accept all
        nft add rule inet filter student_out accept
    fi
else
    echo "No config found, allowing all."
fi

# for debugging: list the applied rules
nft list ruleset

echo "=== Router Rules Applied. Sleeping... ==="
# Keep the container running to maintain the network namespace
exec sleep infinity