#!/usr/bin/env bash
set -euo pipefail

report_dir="${1:-rapports-ci}"
mkdir -p "$report_dir"
templates=(
  cloudformation/reseau-leman.yaml cloudformation/10-route53.yaml
  cloudformation/10-zone-deleguee.yaml cloudformation/11-cloudfront.yaml
  cloudformation/demo-certificat.yaml cloudformation/12-supervision.yaml
  templates/*.yaml
)
python3 scripts/bundle_portal.py --check
python3 scripts/bundle_lambda.py --check
ruff check app scripts tests policies
cfn-lint -r eu-north-1 --non-zero-exit-code error -t "${templates[@]}"
python3 policies/controle-iac.py "${templates[@]}"
bash scripts/guard.sh
coverage run --source=app -m unittest discover -s tests -p 'test_*.py'
coverage xml -o coverage.xml
coverage report --fail-under=80
cp coverage.xml "$report_dir/coverage.xml"
pip-audit --disable-pip --no-deps --format json -r app/requirements.txt -o "$report_dir/dependances.json"
cyclonedx-py requirements app/requirements.txt --output-reproducible --of JSON --sv 1.6 -o "$report_dir/portail.cdx.json"
