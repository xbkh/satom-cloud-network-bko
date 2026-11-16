#!/usr/bin/env bash
set -euo pipefail
role=${1:?web ou app}
case "$role" in
  web) port=443 ;;
  app) port=8080 ;;
  *) exit 2 ;;
esac
install -d -m 0755 /opt/leman-lab
if [[ "$role" == web && ! -s /opt/leman-lab/tls.key ]]; then
  umask 077
  openssl req -x509 -newkey rsa:2048 -nodes -days 7 -subj '/CN=web-01-bko' \
    -keyout /opt/leman-lab/tls.key -out /opt/leman-lab/tls.crt 2>/dev/null
  umask 022
fi
rm -f /opt/leman-lab/http.py
cat >/opt/leman-lab/serveur.py <<'PY'
import ssl
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

role, port = sys.argv[1], int(sys.argv[2])

class LabHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        message = f"{role}-01_bko - Groupe Leman Finance\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(message)))
        self.end_headers()
        self.wfile.write(message)

server = ThreadingHTTPServer(("0.0.0.0", port), LabHandler)
if role == "web":
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain("/opt/leman-lab/tls.crt", "/opt/leman-lab/tls.key")
    server.socket = tls.wrap_socket(server.socket, server_side=True)
server.serve_forever()
PY
cat >/etc/systemd/system/leman-lab.service <<UNIT
[Unit]
Description=Service de test Groupe Leman Finance
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/leman-lab/serveur.py $role $port
Restart=on-failure
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable leman-lab.service
systemctl restart leman-lab.service
systemctl is-active leman-lab.service
