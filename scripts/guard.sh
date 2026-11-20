#!/usr/bin/env bash
set -euo pipefail
d=$(mktemp -d)
archive=cfn-guard-v3-x86_64-linux-latest.tar.gz
curl -fsSL --max-time 75 "https://github.com/aws-cloudformation/cloudformation-guard/releases/download/3.3.0/$archive" -o "$d/$archive"
printf '%s  %s\n' ecf25d586c98057836fac28a8e498569f6daded8f386fd13327c82a4daa45d6e "$d/$archive" | sha256sum -c
tar -xzf "$d/$archive" -C "$d" cfn-guard-v3-x86_64-linux-latest/cfn-guard
guard="$d/cfn-guard-v3-x86_64-linux-latest/cfn-guard"
for file in cloudformation/reseau-leman.yaml cloudformation/12-supervision.yaml templates/sonde.yaml templates/dev-sans-ec2.yaml; do
  "$guard" validate --rules policies/portail.guard --data "$file"
done
echo 'cfn-guard : contrôles IMDSv2, chiffrement EBS et rétention exécutés sur les templates ciblés.'
