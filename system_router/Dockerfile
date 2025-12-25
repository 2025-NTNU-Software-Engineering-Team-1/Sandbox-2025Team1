FROM alpine:3.19

RUN apk add --no-cache nftables jq bash iproute2 bind-tools su-exec

RUN mkdir -p /etc/network_config

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
