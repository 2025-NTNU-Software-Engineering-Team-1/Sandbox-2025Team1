FROM alpine:edge

# Install dnsmasq with nftset support and other required packages
RUN apk add --no-cache nftables jq bash iproute2 bind-tools su-exec dnsmasq-dnssec-nftset

RUN mkdir -p /etc/network_config /etc/dnsmasq.d /var/log

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]