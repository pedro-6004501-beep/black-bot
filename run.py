"""
Kuberns launcher: starts a minimal HTTP health-check server on port 8000
in a background thread, then runs the Telegram bot in the main thread.
"""
import threading
import http.server
import runpy


class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):  # silence access logs
        pass


def start_health_server():
    server = http.server.HTTPServer(("0.0.0.0", 8000), HealthHandler)
    server.serve_forever()


if __name__ == "__main__":
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()
    runpy.run_path("bot.py", run_name="__main__")
