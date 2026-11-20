import base64
import unittest
from contextlib import redirect_stdout
from io import StringIO

from app.adaptateur_alb import handler
from app.portail import LOGO


class AdaptateurTest(unittest.TestCase):
    def request(self, path, method="GET"):
        with redirect_stdout(StringIO()):
            return handler({"path": path, "httpMethod": method}, None)

    def test_alb_status(self):
        for path, status in [("/", 200), ("/api/health", 200), ("/api/error", 404)]:
            response = self.request(path)
            self.assertEqual(response["statusCode"], status)
            self.assertTrue(response["statusDescription"].startswith(f"{status} "))
            self.assertEqual(response["headers"]["Cache-Control"], "no-store")

    def test_alb_binary_content(self):
        response = self.request("/static/logo.png")
        self.assertTrue(response["isBase64Encoded"])
        self.assertEqual(base64.b64decode(response["body"]), LOGO)
        self.assertEqual(response["headers"]["Content-Type"], "image/png")
        head = self.request("/static/logo.png", "HEAD")
        self.assertFalse(head["isBase64Encoded"])
        self.assertEqual(head["body"], "")

    def test_alb_only_accepts_reads(self):
        self.assertEqual(self.request("/", "POST")["statusCode"], 405)

    def test_alb_browser_representation(self):
        with redirect_stdout(StringIO()):
            response = handler({"path": "/", "headers": {"Accept": "text/html"}}, None)
        self.assertEqual(response["headers"]["Content-Type"], "text/html; charset=utf-8")
        self.assertEqual(response["headers"]["Vary"], "Accept")
        self.assertIn("web-01_bko", response["body"])


if __name__ == "__main__":
    unittest.main()
