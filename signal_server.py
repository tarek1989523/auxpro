import http.server
import json
import threading
from urllib.parse import urlparse, parse_qs

HOST = "0.0.0.0"
PORT = 9999

signal = {"id": 0, "type": "", "lot": 0.0, "price": 0.0, "sl": 0.0, "tp": 0.0, "time": 0}
lock = threading.Lock()


class SignalHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/signal":
            with lock:
                data = json.dumps(signal).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        elif parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/signal":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(body)
                with lock:
                    global signal
                    signal = {
                        "id": signal["id"] + 1,
                        "type": data.get("type", ""),
                        "lot": data.get("lot", 0.0),
                        "price": data.get("price", 0.0),
                        "sl": data.get("sl", 0.0),
                        "tp": data.get("tp", 0.0),
                        "time": data.get("time", 0),
                    }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "id": signal["id"]}).encode())
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass


def run_server():
    server = http.server.HTTPServer((HOST, PORT), SignalHandler)
    print(f"Signal server running on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
