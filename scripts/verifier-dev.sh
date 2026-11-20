#!/usr/bin/env bash
set -euo pipefail
export AWS_PAGER=""

output() {
  aws cloudformation describe-stacks --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue | [0]" --output text
}
probe=$(output satom-leman-ci-sonde-bko ProbeId)
alb=$(output satom-leman-ci-dev-bko AlbDns)
[[ "$probe" =~ ^i-[a-f0-9]+$ && "$alb" =~ ^internal-[a-z0-9.-]+\.elb\.amazonaws\.com$ ]]
for _ in {1..36}; do
  connected=$(aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$probe" --query 'InstanceInformationList[0].PingStatus' --output text)
  [[ "$connected" == Online ]] && break
  sleep 5
done
[[ "$connected" == Online ]]
[[ "${LEMAN_LOAD:-true}" =~ ^(true|false)$ ]]
parameters=$(python3 - "$alb" "${LEMAN_LOAD:-true}" <<'PY'
import base64, json, pathlib, shlex, sys
encoded = base64.b64encode(pathlib.Path("tests/charge.js").read_bytes()).decode()
probe = pathlib.Path("scripts/sonde-interne.sh").read_text().partition("\n")[2]
config = {"PORTAL_URL": "http://" + sys.argv[1], "LEMAN_K6_B64": encoded, "LEMAN_LOAD": sys.argv[2]}
env = "export " + " ".join(k + "=" + shlex.quote(v) for k, v in config.items())
print(json.dumps({"commands": ["#!/usr/bin/env bash\n" + env + "\n" + probe], "executionTimeout": ["100"]}))
PY
)
command_id=$(aws ssm send-command --document-name AWS-RunShellScript --instance-ids "$probe" \
  --comment 'Tests HTTP et charge bornée du portail dev' --parameters "$parameters" --query Command.CommandId --output text)
for _ in {1..32}; do
  state=$(aws ssm get-command-invocation --command-id "$command_id" --instance-id "$probe" --query Status --output text 2>/dev/null || true)
  case "$state" in Success|Failed|Cancelled|TimedOut) break ;; esac
  sleep 4
done
aws ssm get-command-invocation --command-id "$command_id" --instance-id "$probe" \
  --query '{Etat:Status,Sortie:StandardOutputContent,Erreurs:StandardErrorContent}' --output json
[[ "$state" == Success ]]
