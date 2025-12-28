#!/usr/bin/env python3
"""Calculator Server - Simple HTTP API for calculations"""
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

SERVICE_NAME = os.environ.get("SERVICE_NAME", "Calculator Service")

class CalcHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[LOG] {args[0]}")
    
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        
        response = ""
        
        if parsed.path == "/add":
            try:
                a = int(query.get("a", [0])[0])
                b = int(query.get("b", [0])[0])
                response = json.dumps({"result": a + b, "operation": "add"})
            except:
                response = json.dumps({"error": "Invalid parameters"})
        
        elif parsed.path == "/multiply":
            try:
                a = int(query.get("a", [0])[0])
                b = int(query.get("b", [0])[0])
                response = json.dumps({"result": a * b, "operation": "multiply"})
            except:
                response = json.dumps({"error": "Invalid parameters"})
        
        elif parsed.path == "/health":
            response = "OK"
        
        else:
            response = json.dumps({
                "service": SERVICE_NAME,
                "endpoints": ["/add?a=&b=", "/multiply?a=&b=", "/health"]
            })
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response.encode())

if __name__ == "__main__":
    port = 9001
    print(f"{SERVICE_NAME} starting on port {port}")
    server = HTTPServer(("0.0.0.0", port), CalcHandler)
    server.serve_forever()
