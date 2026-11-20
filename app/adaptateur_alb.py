"""Adaptation des réponses du portail au format ALB pour Lambda."""

import base64
import json
from http import HTTPStatus
from urllib.parse import urlsplit

from app.portail import (
    LOGO,
    NO_CACHE,
    TEXT,
    PortalConfig,
    api_route,
    home_content,
    web_route,
)

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
    body, media_type = message + "\n", TEXT
    if image:
        media_type = "image/png"
        if binary:
            body = base64.b64encode(LOGO).decode("ascii")
    headers = {
        "Content-Type": media_type,
        "Cache-Control": "public, max-age=86400" if image else NO_CACHE,
        "X-Content-Type-Options": "nosniff",
    }
    if status == 200 and path == "/":
        request_headers = {key.lower(): value for key, value in (event.get("headers") or {}).items()}
        body, headers["Content-Type"] = home_content(message, request_headers.get("accept", ""))
        headers["Vary"] = "Accept"
    print(json.dumps({"event": "http_request", "method": method, "status": status, "path": path}))
    return {
        "statusCode": status,
        "statusDescription": f"{status} {HTTPStatus(status).phrase}",
        "headers": headers,
        "isBase64Encoded": binary,
        "body": "" if method == "HEAD" else body,
    }
