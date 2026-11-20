"""Vérifie ou regénère le script embarqué dans le template CloudFormation."""

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app" / "portail.py"
TEMPLATE = ROOT / "cloudformation" / "reseau-leman.yaml"
USER_DATA = re.compile(
    r"(?<=            cat > /opt/leman.py <<'PY'\n).*?(?=^            PY$)",
    re.MULTILINE | re.DOTALL,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    template = TEMPLATE.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")
    if "${" in source:
        parser.exit(1, "Les interpolations CloudFormation appartiennent au fichier YAML.\n")
    code = "".join((" " * 12 + line if line.strip() else "\n") for line in source.splitlines(True))
    bundled, count = USER_DATA.subn(lambda _: code, template)
    if count != 1:
        parser.exit(1, "Bloc applicatif introuvable ou ambigu.\n")
    if args.check:
        if bundled != template:
            parser.exit(1, "Actualiser le template avec python3 scripts/bundle_portal.py.\n")
    elif bundled != template:
        TEMPLATE.write_text(bundled, encoding="utf-8")


if __name__ == "__main__":
    main()
