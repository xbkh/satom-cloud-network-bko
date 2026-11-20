"""Regénère le code de la solution temporaire utilisée quand les vCPU EC2 sont épuisés."""

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "dev-sans-ec2.yaml"
BLOCK = re.compile(r"(          # BEGIN APPLICATION\n).*?(?=^          # END APPLICATION$)", re.MULTILINE | re.DOTALL)
PORTAL_IMPORT = re.compile(r"^from app\.portail import (?:\([\s\S]*?^\)|[^\n]+)\n", re.MULTILINE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    portail = (ROOT / "app" / "portail.py").read_text(encoding="utf-8")
    portail = portail.rsplit('if __name__ == "__main__":', 1)[0].rstrip()
    adapter = (ROOT / "app" / "adaptateur_alb.py").read_text(encoding="utf-8")
    adapter = PORTAL_IMPORT.sub("", adapter)
    adapter = "\n".join(line for line in adapter.splitlines() if not (
        line in ("import base64", "import json", "from urllib.parse import urlsplit")
        or line.startswith('"""')
    )).strip()
    code = "".join((" " * 10 + line if line else "") + "\n" for line in (
        portail + "\n\n" + adapter
    ).splitlines())
    before = TEMPLATE.read_text(encoding="utf-8")
    updated, count = BLOCK.subn(lambda match: match[1] + code, before)
    if count != 1 or (args.check and before != updated):
        raise SystemExit("Le code Lambda doit être régénéré.")
    if not args.check and before != updated:
        TEMPLATE.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
