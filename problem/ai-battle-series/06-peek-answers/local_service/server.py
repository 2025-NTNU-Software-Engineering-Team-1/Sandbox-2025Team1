#!/usr/bin/env python3
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

DATA_PATH = Path(__file__).with_name("data.json")


def load_pages():
    with DATA_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    pages = payload.get("pages", [])
    return pages


PAGES = load_pages()
TOTAL_PAGES = len(PAGES)


class APIHandler(BaseHTTPRequestHandler):

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if parsed.path != "/api/answers":
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        query = parse_qs(parsed.query)
        page_values = query.get("page", [])
        if not page_values:
            self._send_json(400, {"error": "missing page"})
            return

        try:
            page = int(page_values[0])
        except ValueError:
            self._send_json(400, {"error": "invalid page"})
            return

        if page < 1 or page > TOTAL_PAGES:
            self._send_json(404, {"error": "page not found"})
            return

        data = PAGES[page - 1]
        self._send_json(200, {
            "page": page,
            "total_pages": TOTAL_PAGES,
            "data": data
        })

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), APIHandler)
    print("Server started on 0.0.0.0:8080", flush=True)
    server.serve_forever()
