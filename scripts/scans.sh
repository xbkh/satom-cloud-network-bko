#!/usr/bin/env bash
set -euo pipefail
report_dir="${1:-rapports-ci}"
mkdir -p "$report_dir"
temp=$(mktemp -d)
name=gitleaks_8.30.1_linux_x64.tar.gz
curl -fsSL --max-time 75 "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/$name" -o "$temp/$name"
printf '%s  %s\n' 551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb "$temp/$name" | sha256sum -c
tar -xzf "$temp/$name" -C "$temp" gitleaks
"$temp/gitleaks" git --redact=100 --report-format json --report-path "$report_dir/gitleaks.json" .
SEMGREP_SEND_METRICS=off semgrep scan --metrics=off --error --config policies/semgrep.yaml --json-output "$report_dir/semgrep.json" app
