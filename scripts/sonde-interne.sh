#!/usr/bin/env bash
set -euo pipefail
cd "$(mktemp -d)"
trap 'rm -f -- k6.tar.gz charge.js; if [[ -d k6-v2.4.0-linux-amd64 ]]; then rm -f -- k6-v2.4.0-linux-amd64/k6; rmdir k6-v2.4.0-linux-amd64; fi' EXIT
curl -fsS --max-time 6 "$PORTAL_URL/" | grep -E '^web-0[12]_bko$'
curl -fsS --max-time 6 "$PORTAL_URL/api/health" | grep -F 'app-01_bko OK'
test "$(curl -fsSI --max-time 6 "$PORTAL_URL/static/logo.png" | tr -d '\r' | grep -ic '^Content-Type: image/png$')" -eq 1
test "$(curl -sS --max-time 6 -o /dev/null -w '%{http_code}' "$PORTAL_URL/api/error")" = 404
test "$(curl -fsSI --max-time 6 "$PORTAL_URL/api/health" | tr -d '\r' | grep -ic '^X-Content-Type-Options: nosniff$')" -eq 1
test "$(curl -fsSI --max-time 6 "$PORTAL_URL/api/health" | tr -d '\r' | grep -ic '^Cache-Control: no-store$')" -eq 1
echo 'Contrôle passif : Cache-Control et type MIME contrôlés, route de diagnostic fermée.'
python3 - <<'PY'
import json, os, socket, time
from urllib.parse import urlsplit
started = time.monotonic()
host = urlsplit(os.environ['PORTAL_URL']).hostname
socket.getaddrinfo(host, 80)
elapsed = (time.monotonic() - started) * 1000
print(json.dumps({"test":"dns_interne", "duree_ms":round(elapsed,3)}))
if elapsed >= 100:
 raise SystemExit("Délai DNS supérieur à 100 ms")
PY
if [[ "$LEMAN_LOAD" == false ]]; then exit 0; fi
curl -fsSL --max-time 45 https://github.com/grafana/k6/releases/download/v2.4.0/k6-v2.4.0-linux-amd64.tar.gz -o k6.tar.gz
printf '%s  %s\n' 5a5ecf23529ccf93135bc7e5b0c1cd5126ecf5f2672e22eed1556a0ab74abb87 k6.tar.gz | sha256sum -c
tar -xzf k6.tar.gz k6-v2.4.0-linux-amd64/k6
printf '%s' "$LEMAN_K6_B64" | base64 -d >charge.js
K6_NO_USAGE_REPORT=true ./k6-v2.4.0-linux-amd64/k6 run --quiet charge.js
