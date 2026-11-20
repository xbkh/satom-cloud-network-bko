#!/usr/bin/env bash
set -euo pipefail
export AWS_PAGER="" AWS_REGION=eu-north-1
report_dir="${1:-rapports-ci}"
mkdir -p "$report_dir"
dev=satom-leman-ci-dev-bko
sonde=satom-leman-ci-sonde-bko
monitor=satom-leman-ci-alarme-bko
alarm=alarm-5xx-portail-ci-dev-bko

output() {
  aws cloudformation describe-stacks --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue | [0]" --output text
}
if stack=$(aws cloudformation describe-stacks --stack-name "$monitor" --output json 2>&1); then
  echo 'Une stack d’alarme dev existe déjà.' >&2
  exit 1
elif [[ "$stack" != *'does not exist'* ]]; then
  printf '%s\n' "$stack" >&2
  exit 1
fi
config=$(aws cloudformation describe-stacks --stack-name "$dev" --output json)
jq -e '.Stacks[0] |
  any(.Tags[]; .Key=="Equipe" and .Value=="bko") and
  any(.Tags[]; .Key=="Environnement" and .Value=="dev") and
  any(.Parameters[]; .ParameterKey=="LabDiagnostics" and .ParameterValue=="true")
' <<<"$config" >/dev/null
probe=$(output "$sonde" ProbeId)
alb=$(output "$dev" AlbDns)
alb=${alb,,}
[[ "$probe" =~ ^i-[a-f0-9]+$ && "$alb" =~ ^internal-[a-z0-9.-]+\.elb\.amazonaws\.com$ ]]

command_id=
cleanup() {
  if [[ -n "$command_id" ]]; then
    aws ssm cancel-command --command-id "$command_id" >/dev/null 2>&1 || true
  fi
  aws cloudformation delete-stack --stack-name "$monitor"
  aws cloudformation wait stack-delete-complete --stack-name "$monitor"
}
trap cleanup EXIT
aws cloudformation deploy --stack-name "$monitor" --template-file cloudformation/12-supervision.yaml \
  --no-fail-on-empty-changeset --capabilities CAPABILITY_IAM \
  --tags Projet=SatomCloudNetwork Equipe=bko Environnement=dev Module=12 \
  --parameter-overrides "VpcId=$(output "$dev" VpcId)" "AlbFullName=$(output "$dev" AlbFullName)" \
  "WebTargetsFullName=$(output "$dev" WebTargetsFullName)" NameSuffix=ci-dev-bko \
  AlarmPeriodSeconds=60 DeployVpcObservability=false >&2
queue=$(output "$monitor" NotificationQueueUrl)
test -n "$queue"

payload=$(python3 - "$alb" <<'PY'
import json, sys

code = f"""#!/usr/bin/env bash
set -euo pipefail
for iteration in {{1..38}}; do
  status=$(curl --silent --show-error --max-time 4 --output /dev/null \
    --write-out '%{{http_code}}' 'http://{sys.argv[1]}/api/error')
  test "$status" = 500
  sleep 4
done
"""
print(json.dumps({"commands": [code], "executionTimeout": ["180"]}))
PY
)
started=$(date +%s)
command_id=$(aws ssm send-command --document-name AWS-RunShellScript --instance-ids "$probe" \
  --comment 'Vérification de la notification 5xx sur dev' --parameters "$payload" \
  --query Command.CommandId --output text)
message=
while (( $(date +%s) - started < 285 )); do
  events=$(aws sqs receive-message --queue-url "$queue" --wait-time-seconds 8 --max-number-of-messages 5 --output json)
  message=$(jq -c --arg alarm "$alarm" 'first(
    .Messages[]? | .Body | fromjson |
    select(.AlarmName==$alarm and .NewStateValue=="ALARM")
  ) // empty' <<<"$events")
  if [[ -n "$message" ]]; then break; fi
  state=$(aws ssm get-command-invocation --command-id "$command_id" --instance-id "$probe" --query Status --output text 2>/dev/null || true)
  if [[ "$state" == Failed || "$state" == TimedOut ]]; then
    echo "La sonde d’alarme a échoué avec l’état $state." >&2
    exit 1
  fi
done
[[ -n "$message" ]]
duration=$(( $(date +%s) - started ))
jq --argjson seconds "$duration" '{
  environnement:"dev", metrique:.Trigger.MetricName, notification:.NewStateValue,
  etat_precedent:.OldStateValue, horodatage_alarme:.StateChangeTime,
  secondes_depuis_injection:$seconds, seuil_moins_de_cinq_minutes:($seconds<300)
}' <<<"$message" | tee "$report_dir/alarme-dev.json"
(( duration < 300 ))
