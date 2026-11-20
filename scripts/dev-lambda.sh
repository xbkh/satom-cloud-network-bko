#!/usr/bin/env bash
set -euo pipefail
export AWS_PAGER=""
network=satom-leman-ci-dev-bko
lambda=satom-leman-ci-dev-lambda-bko
tags=(Projet=SatomCloudNetwork Equipe=bko Environnement=dev Module=13)
output() {
  aws cloudformation describe-stacks --stack-name "$1" --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue | [0]" --output text
}
test "${DEV_VPC_ID:-}" = "$(output satom-leman-dev-bko VpcDevId)"
[[ "$DEV_VPC_ID" == vpc-* ]]
case "${1:-}" in
  deploy)
    mapfile -t params < <(python3 -c 'import json; p=json.load(open("parameters/dev.json",encoding="utf-8")); p["DeployPortal"]="false"; print("\n".join(f"{k}={v}" for k,v in p.items()))')
    aws cloudformation deploy --stack-name "$network" --template-file cloudformation/reseau-leman.yaml \
      --parameter-overrides "${params[@]}" "ExistingVpcId=$DEV_VPC_ID" --tags "${tags[@]}" --no-fail-on-empty-changeset
    aws cloudformation deploy --stack-name "$lambda" --template-file templates/dev-sans-ec2.yaml \
      --parameter-overrides "VpcId=$DEV_VPC_ID" "SubnetA=$(output "$network" PublicSubnetId)" \
      "SubnetB=$(output "$network" PublicSubnetBId)" --tags "${tags[@]}" --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset
    ;;
  probe)
    invocation=$(mktemp)
    trap 'rm -f -- "$invocation"' EXIT
    payload='{}'
    if [[ "${2:-}" == smoke ]]; then payload='{"smoke_only":true}'; fi
    fn=$(output "$lambda" ProbeName)
    [[ "$fn" == satom-leman-ci-dev-test-bko ]]
    state=$(aws lambda invoke --function-name "$fn" --cli-binary-format raw-in-base64-out \
      --payload "$payload" --cli-read-timeout 70 "$invocation" --query 'FunctionError' --output text)
    cat "$invocation"
    printf '\n'
    test "$state" = None
    jq -e '(has("thresholds") | not) or .thresholds == true' "$invocation" >/dev/null
    ;;
  delete)
    for name in "$lambda" "$network"; do
      if ! stack=$(aws cloudformation describe-stacks --stack-name "$name" --output json 2>&1); then
        if [[ "$stack" == *'does not exist'* ]]; then continue; fi
        printf '%s\n' "$stack" >&2
        exit 1
      fi
      id=$(jq -er '.Stacks[0] |
        select(any(.Tags[]; .Key=="Equipe" and .Value=="bko")) |
        select(any(.Tags[]; .Key=="Environnement" and .Value=="dev")) |
        select(any(.Tags[]; .Key=="Module" and .Value=="13")) | .StackId' <<<"$stack")
      aws cloudformation delete-stack --stack-name "$id"
      aws cloudformation wait stack-delete-complete --stack-name "$id"
      printf '%s\tDELETE_COMPLETE\n' "$name"
    done
    ;;
  *) echo 'Usage : bash scripts/dev-lambda.sh deploy|probe|delete' >&2; exit 2 ;;
esac
