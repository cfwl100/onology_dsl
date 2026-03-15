from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from oac_osdk import OacClient


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(size)
        payload = json.loads(body)
        mode = self.path.split("/")[-1]
        response = {
            "mode": mode,
            "success": True,
            "echoOperation": payload.get("operation"),
        }
        raw = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):
        return


def test_osdk_execute():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        base = f"http://127.0.0.1:{server.server_port}"
        client = OacClient(base)
        result = client.execute({"operation": "QUERY"})
        assert result["mode"] == "execute"
        assert result["success"] is True
        assert result["echoOperation"] == "QUERY"
    finally:
        server.shutdown()
        thread.join(timeout=2)
