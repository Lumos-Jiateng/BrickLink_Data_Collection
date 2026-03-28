#!/usr/bin/env python3
"""
Serves annotator.html and handles JSON save requests from the browser.
Usage: python3 server.py [port]
Then open http://localhost:8787 in your browser.
"""

import http.server
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
DIR = Path(__file__).parent.resolve()
HTML_FILE = DIR / "annotator.html"


class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  [{self.address_string()}] {fmt % args}")

    def do_GET(self):
        if self.path in ("/", "/annotator.html"):
            content = HTML_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/save":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            self._json_response(400, {"error": f"Invalid JSON: {e}"})
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"annotation_{timestamp}.json"
        out_path = DIR / filename

        with open(out_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"  Saved → {out_path}")
        self._json_response(200, {"saved": filename, "path": str(out_path)})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json_response(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    os.chdir(DIR)
    server = http.server.HTTPServer(("localhost", PORT), Handler)
    print(f"Annotator server running at http://localhost:{PORT}")
    print(f"Serving files from: {DIR}")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
