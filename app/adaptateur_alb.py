"""Adaptation des réponses du portail au format ALB pour Lambda."""

import base64
import json
from http import HTTPStatus
from urllib.parse import urlsplit

from app.portail import LOGO, NO_CACHE, TEXT, PortalConfig, api_route, web_route

DEMO = PortalConfig("Lambda dev", "Lambda dev", "Lambda dev")


def handler(event, _context):
    path = urlsplit(event.get("path", "/")).path
    method = event.get("httpMethod", "GET")
    if method not in ("GET", "HEAD"):
        status, message = 405, "Méthode non autorisée"
    elif path == "/static/logo.png":
        status, message = 200, ""
    elif path.startswith("/api/"):
        status, message = api_route(path, DEMO)
    else:
        status, message = web_route(path, DEMO)
    binary = status == 200 and path == "/static/logo.png" and method == "GET"
    image = status == 200 and path == "/static/logo.png"
    body = base64.b64encode(LOGO).decode("ascii") if binary else message + "\n"
    print(json.dumps({"event": "http_request", "method": method, "status": status, "path": path}))
    return {
        "statusCode": status,
        "statusDescription": f"{status} {HTTPStatus(status).phrase}",
        "headers": {
            "Content-Type": "image/png" if image else TEXT,
            "Cache-Control": "public, max-age=86400" if image else NO_CACHE,
            "X-Content-Type-Options": "nosniff",
        },
        "isBase64Encoded": binary,
        "body": "" if method == "HEAD" else body,
    }
