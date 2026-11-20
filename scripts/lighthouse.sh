#!/usr/bin/env bash
set -euo pipefail
report_dir="${1:-rapports-ci}"
mkdir -p "$report_dir"
work=$(mktemp -d)
server_pid=
cleanup() {
  if [[ -n "$server_pid" ]]; then kill "$server_pid" 2>/dev/null || true; fi
  rm -rf -- "$work"
}
trap cleanup EXIT

python3 -u - >"$work/server.log" 2>&1 <<'PY' &
from app.portail import PortalConfig, make_server

config = PortalConfig("127.0.0.1", "127.0.0.1", "127.0.0.2")
with make_server(("127.0.0.1", 0), config) as server:
    print(server.server_address[1])
    server.serve_forever()
PY
server_pid=$!
for _ in {1..50}; do
  if [[ -s "$work/server.log" ]]; then break; fi
  sleep 0.1
done
port=$(head -n 1 "$work/server.log")
[[ "$port" =~ ^[0-9]+$ ]]

export CHROME_PATH="${CHROME_PATH:-$(command -v google-chrome)}"
npx --yes lighthouse@12.8.2 "http://127.0.0.1:$port/" \
  --only-categories=performance,accessibility --output=json \
  --output-path="$work/lighthouse.json" \
  --chrome-flags='--headless=new --disable-dev-shm-usage' --quiet
jq -e '{
  outil: ("Lighthouse " + .lighthouseVersion),
  cible: "Accueil HTML du portail sur 127.0.0.1",
  performance: (.categories.performance.score * 100 | round),
  accessibilite: (.categories.accessibility.score * 100 | round)
}' "$work/lighthouse.json" | tee "$report_dir/lighthouse.json"
jq -e '.performance >= 85 and .accessibilite >= 90' "$report_dir/lighthouse.json" >/dev/null
