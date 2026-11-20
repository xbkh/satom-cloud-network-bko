#!/usr/bin/env bash
set -euo pipefail
export AWS_PAGER=""
for name in satom-leman-ci-sonde-bko satom-leman-ci-dev-bko; do
  if ! stack=$(aws cloudformation describe-stacks --stack-name "$name" --output json 2>&1); then
    if [[ "$stack" == *'does not exist'* ]]; then continue; fi
    printf '%s\n' "$stack" >&2
    exit 1
  fi
  id=$(jq -er '
    .Stacks[0] |
    select(any(.Tags[]; .Key=="Equipe" and .Value=="bko")) |
    select(any(.Tags[]; .Key=="Environnement" and .Value=="dev")) |
    select(any(.Tags[]; .Key=="Module" and .Value=="13")) |
    .StackId
  ' <<<"$stack")
  aws cloudformation delete-stack --stack-name "$id"
  aws cloudformation wait stack-delete-complete --stack-name "$id"
  printf '%s\tDELETE_COMPLETE\n' "$name"
done
