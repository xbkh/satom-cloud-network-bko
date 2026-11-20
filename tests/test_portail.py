import http.client
import json
import threading
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from app.portail import LOGO, PortalConfig, api_route, make_server, web_route

WEB = PortalConfig("10.0.1.10", "10.0.1.10", "10.0.2.10")
BACKUP = PortalConfig("10.0.5.10", WEB.primary_web_ip, WEB.app_ip)
APP = PortalConfig("10.0.2.10", WEB.primary_web_ip, WEB.app_ip)
DIAG_APP = PortalConfig(APP.local_ip, APP.primary_web_ip, APP.app_ip, diagnostics=True)
DIAG_WEB = PortalConfig(WEB.local_ip, WEB.primary_web_ip, WEB.app_ip, diagnostics=True)


class PortalTest(unittest.TestCase):
    def request(self, config, path, method="GET"):
        with make_server(("127.0.0.1", 0), config) as server:
            runner = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
            runner.start()
            try:
                with redirect_stdout(StringIO()) as log:
                    conn = http.client.HTTPConnection(*server.server_address, timeout=2)
                    try:
                        conn.request(method, path)
                        result = conn.getresponse()
                        response = result.status, dict(result.getheaders()), result.read()
                    finally:
                        conn.close()
                event = json.loads(log.getvalue())
                self.assertEqual(event["status"], response[0])
                self.assertEqual(event["event"], "http_request")
                return response
            finally:
                server.shutdown()
                runner.join()

    def test_web_targets(self):
        for cfg, name in [(WEB, b"web-01_bko"), (BACKUP, b"web-02_bko")]:
            status, headers, body = self.request(cfg, "/?trace=private")
            self.assertEqual(status, 200)
            self.assertEqual(body, name + b"\n")
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(headers["Cache-Control"], "no-store")

    def test_app_health(self):
        status, headers, body = self.request(APP, "/api/health")
        self.assertEqual(status, 200)
        self.assertIn(b"app-01_bko OK", body)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_static_head_and_get(self):
        for method, expected in [("GET", LOGO), ("HEAD", b"")]:
            status, headers, body = self.request(WEB, "/static/logo.png", method)
            self.assertEqual((status, body), (200, expected))
            self.assertEqual(headers["Content-Type"], "image/png")
            self.assertEqual(headers["Cache-Control"], "public, max-age=86400")

    def test_diagnostics_disabled(self):
        for path in ("/api/error", "/api/flow-test", "/static/logo.png"):
            self.assertEqual(self.request(APP, path)[0], 404)
        self.assertEqual(self.request(WEB, "/dns-test")[0], 404)
        self.assertEqual(self.request(WEB, "/health")[0], 200)

    def test_opt_in_diagnostics(self):
        self.assertEqual(api_route("/api/error", DIAG_APP)[0], 500)
        with patch("socket.create_connection", side_effect=TimeoutError):
            self.assertIn("non établie", api_route("/api/flow-test", DIAG_APP)[1])
        with patch("socket.create_connection"):
            self.assertIn("inattendue", api_route("/api/flow-test", DIAG_APP)[1])
        with patch("socket.gethostbyname", return_value=APP.app_ip):
            self.assertIn(APP.app_ip, web_route("/dns-test", DIAG_WEB)[1])
        with patch("socket.gethostbyname", side_effect=OSError):
            self.assertEqual(web_route("/dns-test", DIAG_WEB)[0], 503)


if __name__ == "__main__":
    unittest.main()
