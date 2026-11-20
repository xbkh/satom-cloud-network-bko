#!/usr/bin/env bash
set -euo pipefail
output="${1:-rapports-ci/reprise-dev.json}"
mkdir -p "$(dirname "$output")"
start=$(date +%s)
record=$(mktemp)
trap 'rm -f -- "$record"' EXIT

bash scripts/dev-lambda.sh delete
bash scripts/dev-lambda.sh deploy
for _ in {1..12}; do
  if bash scripts/dev-lambda.sh probe smoke >"$record" &&
     jq -e '.http_home==200 and .http_api==200 and .diagnostic==404' "$record" >/dev/null; then
    break
  fi
  sleep 5
done
jq -e '.http_home==200 and .http_api==200 and .diagnostic==404' "$record" >/dev/null
end=$(date +%s)
jq --arg started "$(date -u -d "@$start" +%FT%TZ)" --arg finished "$(date -u -d "@$end" +%FT%TZ)" \
  --argjson rto "$((end-start))" \
  '{variante:"ALB interne + Lambda; réseau de référence conservé",started:$started,finished:$finished,rto_s:$rto,verification:.,rpo:"sans donnée métier persistante"}' "$record" | tee "$output"
