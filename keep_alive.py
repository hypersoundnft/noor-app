"""Tiny HTTP server so UptimeRobot can ping the Replit to keep it awake."""

from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass  # silence request logs


def keep_alive():
    server = HTTPServer(("0.0.0.0", 8080), _Handler)
    Thread(target=server.serve_forever, daemon=True).start()
