import socket


def check_target(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))

        if result == 0:
            print("good")
        else:
            print("fail")

        sock.close()
    except Exception:
        print("fail")


if __name__ == "__main__":
    targets = [
        ("1.1.1.1", 53),  # Cloudflare DNS
        ("9.9.9.9", 53),  # Quad9 DNS
        ("www.google.com", 443),  # Google HTTPS
        ("github.com", 443),  # GitHub HTTPS
    ]

    for host, port in targets:
        check_target(host, port)
