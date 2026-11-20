#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" != 1 ]]; then
  echo 'Usage : bash scripts/stack.sh dev|prod' >&2
  exit 2
fi
environment=$1
case "$environment" in dev|prod) ;; *) exit 2 ;; esac
export AWS_PAGER=""
tags=(Projet=SatomCloudNetwork Equipe=bko "Environnement=$environment" Module=13)
role=()
if [[ -n "${CFN_ROLE_ARN:-}" ]]; then role=(--role-arn "$CFN_ROLE_ARN"); fi
deploy() {
  local stack=$1 template=$2
  shift 2
  aws cloudformation deploy --stack-name "$stack" --template-file "$template" \
    --tags "${tags[@]}" "${role[@]}" --no-fail-on-empty-changeset --parameter-overrides "$@"
}
stack="satom-leman-ci-$environment-bko"
mapfile -t params < <(python3 -c 'import json,sys; print("\n".join(f"{k}={v}" for k,v in json.load(open(sys.argv[1],encoding="utf-8")).items()))' "parameters/$environment.json")
(( ${#params[@]} >= 9 ))
if [[ "$environment" == dev && -n "${DEV_VPC_ID:-}" ]]; then params+=("ExistingVpcId=$DEV_VPC_ID"); fi
if [[ "$environment" == dev && "${LEMAN_DEV_ALARM:-false}" == true ]]; then
  params=("${params[@]/LabDiagnostics=false/LabDiagnostics=true}")
fi
deploy "$stack" cloudformation/reseau-leman.yaml "${params[@]}"
if [[ "$environment" == dev && -n "${PROBE_PROFILE_NAME:-}" ]]; then
  output() {
    aws cloudformation describe-stacks --stack-name "$stack" \
      --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue | [0]" --output text
  }
  deploy satom-leman-ci-sonde-bko templates/sonde.yaml \
    "VpcId=$(output VpcId)" "SubnetId=$(output PublicSubnetId)" "TestAlbGroup=$(output AlbSg)" \
    "ProfileName=$PROBE_PROFILE_NAME" "InstanceMarket=$(jq -r '.InstanceMarket // "on-demand"' parameters/dev.json)"
fi
