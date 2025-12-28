#!/usr/bin/env python3
"""Echo Server - Simple HTTP service that echoes messages"""
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

MESSAGE = os.environ.get("ECHO_MESSAGE", "Hello from Echo Service!")

class EchoHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[LOG] {args[0]}")
    
    def do_GET(self):
        if self.path == "/health":
            response = "OK"
        elif self.path.startswith("/echo?text="):
            text = self.path.split("text=")[1] if "text=" in self.path else ""
            response = f"[ECHO] {text}"
        else:
            response = MESSAGE
        
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(response.encode())

if __name__ == "__main__":
    port = 9000
    print(f"Echo Server starting on port {port}")
    print(f"Message: {MESSAGE}")
    server = HTTPServer(("0.0.0.0", port), EchoHandler)
    server.serve_forever()
