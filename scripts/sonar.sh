#!/usr/bin/env bash
set -euo pipefail

report_dir="${1:-rapports-ci}"
mkdir -p "$report_dir"
report_dir=$(realpath "$report_dir")
sonar_url="${SONAR_HOST_URL:-http://127.0.0.1:19090}"
sonar_dir="${SONAR_TOOLS_DIR:-}"
server_version=26.11.0.134175
scanner_version=8.4.0.16527

if [[ -z "$sonar_dir" ]]; then sonar_dir=$(mktemp -d); fi
server="$sonar_dir/sonarqube-$server_version"
scanner="$sonar_dir/sonar-scanner-$scanner_version/bin/sonar-scanner"
base=https://binaries.sonarsource.com/Distribution

if [[ ! -x "$scanner" ]]; then
  curl -fsSL --max-time 180 "$base/sonar-scanner-cli/sonar-scanner-cli-$scanner_version.zip" -o "$sonar_dir/scanner.zip"
  unzip -q "$sonar_dir/scanner.zip" -d "$sonar_dir"
fi
if [[ -z "${SONAR_TOKEN:-}" ]]; then
  [[ "$sonar_url" == http://127.0.0.1:19090 ]]
  if [[ ! -x "$server/bin/linux-x86-64/sonar.sh" ]]; then
    curl -fsSL --max-time 720 "$base/sonarqube/sonarqube-$server_version.zip" -o "$sonar_dir/server.zip"
    unzip -q "$sonar_dir/server.zip" -d "$sonar_dir"
  fi
  if ! grep -q '^sonar.web.port=19090$' "$server/conf/sonar.properties"; then
    printf '\nsonar.web.host=127.0.0.1\nsonar.web.port=19090\nsonar.search.host=127.0.0.1\nsonar.search.port=19091\n' >> "$server/conf/sonar.properties"
  fi
  if ! curl -fsS "$sonar_url/api/system/status" >/dev/null 2>&1; then
    "$server/bin/linux-x86-64/sonar.sh" start
  fi
  trap '"$server/bin/linux-x86-64/sonar.sh" stop >/dev/null' EXIT
  for _ in {1..90}; do
    ready=$(curl --max-time 3 -fsS "$sonar_url/api/system/status" 2>/dev/null || true)
    [[ "$ready" == *'"status":"UP"'* ]] && break
    sleep 3
  done
  if [[ "$ready" != *'"status":"UP"'* ]]; then
    tail -15 "$server/logs/sonar.log" "$server/logs/web.log" >&2
    exit 1
  fi
  bootstrap_config=$(mktemp)
  chmod 600 "$bootstrap_config"
  printf '%s\n' 'user = "admin:admin"' >"$bootstrap_config"
  SONAR_TOKEN=$(curl -fsS --config "$bootstrap_config" --data-urlencode "name=satom-analysis-$(date +%s)" \
    "$sonar_url/api/user_tokens/generate" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
  rm -f -- "$bootstrap_config"
  if [[ "${GITHUB_ACTIONS:-}" == true ]]; then printf '::add-mask::%s\n' "$SONAR_TOKEN"; fi
  export SONAR_TOKEN
fi
export SONAR_HOST_URL="$sonar_url"
"$scanner" -Dsonar.qualitygate.wait=true -Dsonar.qualitygate.timeout=150
metrics=alert_status,coverage,duplicated_lines_density,security_rating,reliability_rating,sqale_rating,sqale_debt_ratio,security_hotspots,security_hotspots_reviewed,blocker_violations,critical_violations
curl -fsS --header "Authorization: Bearer $SONAR_TOKEN" --get --data-urlencode component=satom-leman-portail-bko \
  --data-urlencode "metricKeys=$metrics" "$sonar_url/api/measures/component" -o "$report_dir/sonar.json"
python3 - "$report_dir/sonar.json" <<'PY'
import json,sys
with open(sys.argv[1], encoding="utf-8") as report:
 data=json.load(report)
values={m["metric"]:m["value"] for m in data["component"]["measures"]}
print(json.dumps(values,ensure_ascii=False,indent=2))
checks={
 "gate": values.get("alert_status")=="OK",
 "coverage":float(values["coverage"])>=80,
 "duplication":float(values["duplicated_lines_density"])<3,
 "ratings":all(float(values[m])==1 for m in ("security_rating","reliability_rating","sqale_rating")),
 "debt":float(values["sqale_debt_ratio"])<=5,
 "issues":all(int(values.get(m,0))==0 for m in ("blocker_violations","critical_violations")),
 "hotspots":int(values["security_hotspots"])==0 or float(values.get("security_hotspots_reviewed",0))==100,
}
if not all(checks.values()):
 raise SystemExit("Seuils Sonar non atteints : " + ", ".join(k for k,ok in checks.items() if not ok))
PY
