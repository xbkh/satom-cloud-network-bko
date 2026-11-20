"""Service HTTP de démonstration de Léman Finance."""

import base64
import json
import os
import socket
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

LOGO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAZElEQVR4nO3PQQ3AIADA"
    "QEAEgrCD//9E8Lgs6Slo5z53/NnSAa8a0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0"
    "BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0BrQGtAa0D4CBAFDmwGDrAAAAABJRU5ErkJggg=="
)
TEXT = "text/plain; charset=utf-8"
NO_CACHE = "no-store"


@dataclass(frozen=True)
class PortalConfig:
    local_ip: str
    primary_web_ip: str
    app_ip: str
    diagnostics: bool = False


def api_route(path, config):
    if path == "/api/health":
        return 200, f"app-01_bko OK ({config.local_ip})"
    if config.diagnostics and path == "/api/error":
        return 500, "Erreur applicative volontaire du TP"
    if config.diagnostics and path == "/api/flow-test":
        try:
            with socket.create_connection((config.primary_web_ip, 22), timeout=2):
                return 200, "Connexion inattendue sur 22"
        except OSError:
            return 200, "Connexion au port 22 non établie"
    return 404, "Route API inconnue"


def web_route(path, config):
    if path == "/health":
        return 200, "healthy"
    if config.diagnostics and path == "/dns-test":
        try:
            result = socket.gethostbyname("app.prod.leman.internal")
            return 200, f"app.prod.leman.internal = {result}"
        except OSError:
            return 503, "Zone DNS privée indisponible"
    if path == "/":
        return 200, "web-01_bko" if config.local_ip == config.primary_web_ip else "web-02_bko"
    return 404, "Page inconnue"


def make_server(address, config):
    is_app = config.local_ip == config.app_ip

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            path = urlsplit(self.path).path
            if not is_app and path == "/static/logo.png":
                status, content, media_type, cache = 200, LOGO, "image/png", "public, max-age=86400"
            else:
                status, message = api_route(path, config) if is_app else web_route(path, config)
                content, media_type, cache = (message + "\n").encode(), TEXT, NO_CACHE
            self.send_response(status)
            self.send_header("Content-Type", media_type)
            self.send_header("Cache-Control", cache)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if self.command == "GET":
                self.wfile.write(content)

        def log_request(self, code="-", size="-"):
            print(json.dumps({
                "event": "http_request",
                "method": self.command,
                "status": code,
                "path": urlsplit(self.path).path,
            }), flush=True)

    return ThreadingHTTPServer(address, Handler)


def main():
    config = PortalConfig(
        local_ip=socket.gethostbyname(socket.gethostname()),
        primary_web_ip=os.environ["LEMAN_WEB_IP"],
        app_ip=os.environ["LEMAN_APP_IP"],
        diagnostics=os.environ.get("LEMAN_LAB_DIAGNOSTICS") == "true",
    )
    port = 8080 if config.local_ip == config.app_ip else 80
    with make_server(("", port), config) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
